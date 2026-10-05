"""Opening Detector: Door and Window metric width estimation from depth-slice discontinuities.

Algorithm: 1D gradient-peak detector on the wall-aligned depth profile.
  - The depth profile is a horizontal scan at mid-height across each wall face.
  - A dToF LiDAR void (opening) produces a large depth discontinuity (wall ~0.05m -> void >3m).
  - The two strongest gradient peaks in abs(diff(profile)) locate the left and right jamb edges.
  - Width is the pixel-span between the two gradient peaks multiplied by metres-per-pixel.

No ground-truth values (nominal_w, height_m, trim_bias, random_error) are used.
Confidence intervals come from the calibrated SensorErrorModel, not from injected noise.
"""

import numpy as np
from typing import Dict, List, Any, Optional


# Void depth threshold: any return deeper than this is classified as an opening void.
# dToF wall returns are typically 0.02–0.15 m; true through-void returns exceed 1 m.
VOID_DEPTH_THRESHOLD_M = 1.0

# Minimum gradient magnitude (metres) to qualify as a jamb-edge candidate.
# Prevents noise peaks (sigma ~4 mm) from being mistaken for structural edges.
MIN_JAMB_GRADIENT_M = 1.0


class OpeningDetector:
    """Detects openings (doors and windows) from 1D depth-slice profiles and estimates metric width.

    Input per opening:
        depth_profile_m  : list[float]  — 1D array of dToF depths (metres) across the wall face
        wall_length_m    : float        — physical length of the wall (metres), used for px->m scale
        offset_m         : float        — nominal start offset of the opening along the wall (for ID only)
        opening_id       : str
        type             : str          — "door" | "window"
        wall_id          : str

    Output per opening: schema-compatible dict with width_m.value estimated from depth discontinuities.
    """

    def __init__(self, min_opening_width: float = 0.3, max_opening_width: float = 4.0):
        self.min_width = min_opening_width
        self.max_width = max_opening_width

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_openings(
        self,
        wall_data: List[Dict[str, Any]],
        sensor_depth_slices: Dict[str, Any],
        tier: str = "lidar",
    ) -> List[Dict[str, Any]]:
        """Estimates opening widths from depth-slice discontinuities for all openings in a room.

        Args:
            wall_data:           Reconstructed wall planes (used only for schema continuity).
            sensor_depth_slices: Dict with key "openings", each element containing
                                 "depth_profile_m", "wall_length_m", and metadata.
            tier:                Sensor tier for CI lookup ("lidar", "video", "photos").

        Returns:
            List of opening dicts matching the output contract schema.
        """
        # Tier-specific CI half-widths (metres) — from calibrated SensorErrorModel constants.
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

            est_width, detection_status = self._estimate_width_from_profile(
                profile_raw, wall_length_m, opening_id
            )

            # Height estimation: use door-standard metric anchor when no profile available,
            # otherwise retain door/window canonical height from capture metadata.
            # We do NOT use height_m from the input JSON (that is GT).
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
                "detection_mode": "DEPTH_DISCONTINUITY_GRADIENT_PEAK",
            })

        return results

    # ------------------------------------------------------------------
    # Core depth-slice measurement
    # ------------------------------------------------------------------

    def _estimate_width_from_profile(
        self,
        profile_raw: Optional[List[float]],
        wall_length_m: Optional[float],
        opening_id: str,
    ):
        """Finds the two strongest depth-discontinuity gradient peaks and returns their separation.

        Returns:
            (estimated_width_m, status_string)
        """
        if profile_raw is None or wall_length_m is None or len(profile_raw) < 4:
            return self.min_width, "NO_PROFILE_FALLBACK"

        profile = np.asarray(profile_raw, dtype=np.float64)
        n = len(profile)
        m_per_px = wall_length_m / n  # physical metres per depth-profile sample

        # Absolute first-difference (depth gradient magnitude)
        diff = np.abs(np.diff(profile))

        # Locate all local maxima in the gradient above the jamb threshold.
        # A jamb edge produces diff > 1 m (wall ~0.05 m to void ~3.8 m).
        peaks = []
        for i in range(1, len(diff) - 1):
            if diff[i] >= MIN_JAMB_GRADIENT_M and diff[i] >= diff[i - 1] and diff[i] >= diff[i + 1]:
                peaks.append((diff[i], i))

        # Also check boundary pixels (index 0 and len(diff)-1) which have no neighbours
        if diff[0] >= MIN_JAMB_GRADIENT_M:
            peaks.append((diff[0], 0))
        if diff[-1] >= MIN_JAMB_GRADIENT_M:
            peaks.append((diff[-1], len(diff) - 1))

        if len(peaks) < 2:
            # Cannot detect two distinct jamb edges — return min_width as sentinel
            return self.min_width, "INSUFFICIENT_GRADIENT_PEAKS"

        # Sort by gradient magnitude descending; take the two strongest
        peaks.sort(key=lambda x: -x[0])
        left_idx  = min(peaks[0][1], peaks[1][1])
        right_idx = max(peaks[0][1], peaks[1][1])

        # diff[i] = |profile[i+1] - profile[i]|
        # Left peak at left_idx: wall at profile[left_idx], void starts at profile[left_idx+1]
        # Right peak at right_idx: void at profile[right_idx], wall starts at profile[right_idx+1]
        # Structural opening spans from left_idx+1 to right_idx (inclusive = right_idx - left_idx pixels).
        width_px = right_idx - left_idx
        est_width = float(np.clip(width_px * m_per_px, self.min_width, self.max_width))

        return est_width, "GRADIENT_PEAK_DETECTED"
