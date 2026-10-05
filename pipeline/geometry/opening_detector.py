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

# Depth value above which a sample is considered a void (opening) return.
# Set to midpoint between d_wall=0.05 m and d_void=3.80 m -> 1.925 m.
# Using this midpoint ensures the crossing is at the physical boundary
# regardless of exact wall/void depth values (robust to ±10% variation).
VOID_DEPTH_THRESHOLD_M = 1.925


class OpeningDetector:
    def __init__(self, min_opening_width: float = 0.3, max_opening_width: float = 4.0):
        self.min_width = min_opening_width
        self.max_width = max_opening_width

    def detect_openings(
        self,
        wall_data: List[Dict[str, Any]],
        sensor_depth_slices: Dict[str, Any],
        tier: str = "lidar",
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

            profile_raw   = op.get("depth_profile_m")
            wall_length_m = op.get("wall_length_m")
            if wall_length_m is None and wall_data:
                matched_wall = next((w for w in wall_data if w.get("wall_id") == wall_id), None)
                if matched_wall:
                    wall_length_m = matched_wall.get("length_m")

            est_width, detection_status = self._estimate_width_from_profile(
                profile_raw, wall_length_m, opening_id
            )

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
                "detection_mode": "SUBPIXEL_THRESHOLD_CROSSING",
            })

        return results

    def _estimate_width_from_profile(
        self,
        profile_raw: Optional[List[float]],
        wall_length_m: Optional[float],
        opening_id: str,
    ):
        """Sub-pixel threshold-crossing interpolation on beam-footprint profiles.

        Walks the 1D depth profile to find:
          - The first rising crossing: wall -> void (depth crosses VOID_DEPTH_THRESHOLD_M upward)
          - The first falling crossing: void -> wall (depth crosses VOID_DEPTH_THRESHOLD_M downward)

        Each crossing is localised with linear interpolation:
          t = i + (threshold - profile[i]) / (profile[i+1] - profile[i])

        width_m = (right_continuous - left_continuous) * m_per_px

        Valid only when profiles are generated with beam-footprint blending (not step-function).
        See generate_lidar_sim.py for the beam-footprint model.

        Returns:
            (estimated_width_m, status_string)
        """
        if profile_raw is None or wall_length_m is None or len(profile_raw) < 4:
            return self.min_width, "NO_PROFILE_FALLBACK"

        profile = np.asarray(profile_raw, dtype=np.float64)
        n = len(profile)
        m_per_px = wall_length_m / n
        thresh = VOID_DEPTH_THRESHOLD_M

        left_continuous  = None
        right_continuous = None

        for i in range(n - 1):
            d0, d1 = profile[i], profile[i + 1]

            # Rising edge: depth crosses threshold upward (wall -> void)
            if left_continuous is None and d0 < thresh <= d1:
                denom = d1 - d0
                t = (thresh - d0) / denom if abs(denom) > 1e-9 else 0.5
                left_continuous = i + t

            # Falling edge: depth crosses threshold downward (void -> wall)
            elif left_continuous is not None and d0 >= thresh > d1:
                denom = d0 - d1
                t = (d0 - thresh) / denom if abs(denom) > 1e-9 else 0.5
                right_continuous = i + t
                break  # first complete void span found

        if left_continuous is None or right_continuous is None:
            # Fallback: count void pixels
            void_count = int(np.sum(profile > thresh))
            if void_count > 0:
                est_w = float(np.clip(void_count * m_per_px, self.min_width, self.max_width))
                return est_w, "VOID_COUNT_FALLBACK"
            return self.min_width, "NO_CROSSING_FOUND"

        est_width = float(np.clip(
            (right_continuous - left_continuous) * m_per_px,
            self.min_width,
            self.max_width,
        ))
        return est_width, "SUBPIXEL_THRESHOLD_CROSSING"
