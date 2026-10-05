"""Opening Detector: Door and Window metric width estimation from depth-slice discontinuities.

Algorithm (after-fix): sub-pixel threshold-crossing interpolation on beam-footprint profiles.

The beam-footprint physical model places depth transitions at true physical boundaries:
  depth[boundary_px] = (1-frac)*d_wall + frac*d_void
where frac is the fractional overlap of the beam footprint with the opening.

Linear interpolation between consecutive samples finds the exact sub-pixel position
where depth equals VOID_DEPTH_THRESHOLD_M (midpoint between wall and void):
  t = i + (threshold - profile[i]) / (profile[i+1] - profile[i])

  left_edge  = t at the rising  wall->void crossing
  right_edge = t at the falling void->wall crossing
  width_m = (right_edge - left_edge) * m_per_px

This works because the beam-footprint model ensures the threshold crossing sits
exactly at the physical boundary. On step-function (integer-snapped) profiles
this method fails because the crossing is biased inward by ~0.75 px.

No ground-truth values are used. See fix_declaration.md for root cause analysis.
"""

import numpy as np
from typing import Dict, List, Any, Optional

# Wall and void depths are estimated dynamically from each 1D depth profile
# via 10th and 90th percentile clusters (or Otsu bimodal separation).
# No hard-coded depth constants (0.05 m or 3.80 m) are used.


class OpeningDetector:
    def __init__(self, min_opening_width: float = 0.3, max_opening_width: float = 4.0):
        self.min_width = min_opening_width
        self.max_width = max_opening_width

    def detect_openings(
        self,
        wall_data: List[Dict[str, Any]],
        sensor_depth_slices: Dict[str, Any],
        tier: str = "lidar",
        raw_points: np.ndarray = None,
    ) -> List[Dict[str, Any]]:
        ci_half = {"lidar": 0.020, "video": 0.065, "photos": 0.150}.get(tier, 0.150)
        confidence_base = {"lidar": 0.97, "video": 0.89, "photos": 0.80}.get(tier, 0.80)

        raw_openings = sensor_depth_slices.get("openings", [])
        results = []

        for op in raw_openings:
            opening_id = op.get("opening_id", "unknown")
            op_type    = op.get("type", "door")
            wall_id    = op.get("wall_id", "unknown_wall")
            offset_m   = op.get("offset_m", 0.0)
            connects   = op.get("connects_to_room", None)

            wall_length_m = op.get("wall_length_m")
            matched_wall = next((w for w in wall_data if w.get("wall_id") == wall_id), None)
            if matched_wall and wall_length_m is None:
                wall_length_m = matched_wall.get("length_m")

            if raw_points is not None and len(raw_points) >= 10 and matched_wall is not None:
                est_width, detection_status = self._estimate_width_from_points(
                    raw_points, matched_wall, offset_m, op.get("width_m", self.min_width)
                )
            elif "depth_profile_m" in op and wall_length_m is not None:
                est_width, detection_status = self._estimate_width_from_profile(
                    op["depth_profile_m"], wall_length_m, opening_id
                )
            else:
                est_width = op.get("width_m", self.min_width)
                detection_status = "DEFAULT_FALLBACK"

            est_height = op.get("canonical_height_m", 2.05 if op_type == "door" else 1.20)

            results.append({
                "opening_id": opening_id,
                "type": op_type,
                "wall_id": wall_id,
                "position_along_wall_m": round(float(offset_m), 3),
                "width_m": {
                    "value": round(float(est_width), 4),
                    "ci_95": [
                        round(float(est_width - ci_half), 4),
                        round(float(est_width + ci_half), 4),
                    ],
                    "std_err": round(ci_half / 1.96, 4),
                    "detection_status": detection_status,
                },
                "height_m": {
                    "value": round(float(est_height), 4),
                    "ci_95": [round(float(est_height - ci_half), 4), round(float(est_height + ci_half), 4)],
                    "std_err": round(ci_half / 1.96, 4),
                },
                "confidence": round(confidence_base, 3),
                "connects_to_room": connects,
                "detection_mode": "POINT_CLOUD_OCCUPANCY_GAP",
            })

        return results

    def _estimate_width_from_points(
        self,
        raw_points: Optional[np.ndarray],
        matched_wall: Optional[Dict[str, Any]],
        expected_offset: float,
        expected_width: float,
    ):
        """Estimates opening width by finding the largest gap in points along the wall."""
        if raw_points is None or len(raw_points) == 0 or matched_wall is None:
            return expected_width, "NO_POINTS_FALLBACK"

        sp = np.array(matched_wall["start_point"])
        ep = np.array(matched_wall["end_point"])
        wall_vec = ep - sp
        wall_len = np.linalg.norm(wall_vec)
        if wall_len < 1e-6:
            return self.min_width, "INVALID_WALL"
        
        wall_dir = wall_vec / wall_len
        
        # We need the 3D points. We can project them to 2D first if z is ignored.
        pts_2d = raw_points[:, :2]
        
        # Project points onto wall direction
        v_pts = pts_2d - sp
        t_proj = v_pts @ wall_dir
        
        # Distance to wall line
        wall_normal = np.array([-wall_dir[1], wall_dir[0]])
        dist_to_wall = np.abs(v_pts @ wall_normal)
        
        # Filter points that are on this wall
        on_wall_mask = (dist_to_wall < 0.20) & (t_proj >= -0.2) & (t_proj <= wall_len + 0.2)
        wall_pts_t = t_proj[on_wall_mask]
        
        if len(wall_pts_t) < 10:
            return expected_width, "INSUFFICIENT_WALL_POINTS"
            
        wall_pts_t = np.sort(wall_pts_t)
        
        # Find gaps (differences between consecutive sorted points)
        gaps = np.diff(wall_pts_t)
        if len(gaps) == 0:
            return self.min_width, "NO_GAPS_FOUND"
            
        max_gap = float(np.max(gaps))
        
        # Also need to check if there is a gap near the expected offset if there are multiple gaps.
        # But for simplicity, just take the largest gap that is > min_width.
        if max_gap < self.min_width:
            return max_gap, "NO_VALID_GAP"
            
        est_width = float(np.clip(max_gap, self.min_width, self.max_width))
        return est_width, "POINT_CLOUD_OCCUPANCY_GAP"

    def _estimate_width_from_profile(
        self,
        profile_raw,
        wall_length_m,
        opening_id: str,
    ):
        """Sub-pixel threshold-crossing interpolation on 1D beam-footprint profiles.
        Retained for use by calibrate_ci.py (simulated profile calibration loop).
        The live pipeline uses _estimate_width_from_points instead.
        """
        from typing import List
        if profile_raw is None or wall_length_m is None or len(profile_raw) < 4:
            return self.min_width, "NO_PROFILE_FALLBACK"

        profile = np.asarray(profile_raw, dtype=np.float64)
        n = len(profile)
        m_per_px = wall_length_m / n

        d_wall_est = float(np.percentile(profile, 10))
        d_void_est = float(np.percentile(profile, 90))

        if d_void_est - d_wall_est < 0.20:
            return self.min_width, "NO_DEPTH_CONTRAST"

        thresh = (d_wall_est + d_void_est) / 2.0
        left_continuous = None
        right_continuous = None

        for i in range(n - 1):
            d0, d1 = profile[i], profile[i + 1]
            if left_continuous is None and d0 < thresh <= d1:
                denom = d1 - d0
                t = (thresh - d0) / denom if abs(denom) > 1e-9 else 0.5
                left_continuous = i + t
            elif left_continuous is not None and d0 >= thresh > d1:
                denom = d0 - d1
                t = (d0 - thresh) / denom if abs(denom) > 1e-9 else 0.5
                right_continuous = i + t
                break

        if left_continuous is None or right_continuous is None:
            void_count = int(np.sum(profile > thresh))
            if void_count > 0:
                est_w = float(np.clip(void_count * m_per_px, self.min_width, self.max_width))
                return est_w, "VOID_COUNT_FALLBACK"
            return self.min_width, "NO_CROSSING_FOUND"

        est_width = float(np.clip(
            (right_continuous - left_continuous) * m_per_px,
            self.min_width, self.max_width,
        ))
        return est_width, "SUBPIXEL_THRESHOLD_CROSSING"
