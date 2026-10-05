"""Opening Detector: Door and Window metric width estimation from depth-slice discontinuities.

Algorithm (before-fix baseline): integer gradient-peak detector.
  diff[i] = |profile[i+1] - profile[i]|
  Find the two strongest peaks above the void threshold.
  width = (right_peak_idx - left_peak_idx) * m_per_px

No ground-truth values are used.
"""

import numpy as np
from typing import Dict, List, Any, Optional

VOID_DEPTH_THRESHOLD_M = 1.0


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
                "detection_mode": "DEPTH_DISCONTINUITY_GRADIENT_PEAK",
            })

        return results

    def _estimate_width_from_profile(
        self,
        profile_raw: Optional[List[float]],
        wall_length_m: Optional[float],
        opening_id: str,
    ):
        """Integer gradient-peak detector (before-fix baseline).

        Finds the two strongest depth-discontinuity gradient peaks and returns
        their pixel separation multiplied by metres-per-pixel.

        Known bias: the gradient diff-index convention means raw span =
        true_span_px + 1 (fencepost off-by-one). This is the UNFIXED version.

        Returns:
            (estimated_width_m, status_string)
        """
        if profile_raw is None or wall_length_m is None or len(profile_raw) < 4:
            return self.min_width, "NO_PROFILE_FALLBACK"

        profile = np.asarray(profile_raw, dtype=np.float64)
        n = len(profile)
        m_per_px = wall_length_m / n

        diff = np.abs(np.diff(profile))

        peaks = []
        for i in range(1, len(diff) - 1):
            if diff[i] > VOID_DEPTH_THRESHOLD_M and diff[i] >= diff[i - 1] and diff[i] >= diff[i + 1]:
                peaks.append((diff[i], i))
        if diff[0] > VOID_DEPTH_THRESHOLD_M:
            peaks.append((diff[0], 0))
        if diff[-1] > VOID_DEPTH_THRESHOLD_M:
            peaks.append((diff[-1], len(diff) - 1))

        if len(peaks) < 2:
            return self.min_width, "INSUFFICIENT_GRADIENT_PEAKS"

        peaks.sort(key=lambda x: -x[0])
        left_idx  = min(peaks[0][1], peaks[1][1])
        right_idx = max(peaks[0][1], peaks[1][1])

        # NO fencepost correction -- this is the before-fix version
        width_px  = right_idx - left_idx
        est_width = float(np.clip(width_px * m_per_px, self.min_width, self.max_width))
        return est_width, "GRADIENT_PEAK_DETECTED"
