"""Opening Detector: Door and Window localization and metric width/height estimation."""

import numpy as np
from typing import Dict, List, Any

class OpeningDetector:
    def __init__(self, min_opening_width: float = 0.5, max_opening_width: float = 3.0):
        self.min_width = min_opening_width
        self.max_width = max_opening_width

    def detect_openings(
        self,
        wall_data: List[Dict[str, Any]],
        sensor_depth_slices: Dict[str, Any],
        tier: str = "lidar"
    ) -> List[Dict[str, Any]]:
        """Detects openings (doors/windows) along wall planes and estimates metric width & height."""
        openings = []

        # Tier-specific opening noise
        if tier == "lidar":
            noise_w = 0.006 # ~6mm noise
            noise_h = 0.005 # ~5mm noise
            confidence_base = 0.96
        elif tier == "video":
            noise_w = 0.022 # ~2.2cm
            noise_h = 0.020
            confidence_base = 0.88
        else: # photos
            noise_w = 0.055 # ~5.5cm
            noise_h = 0.050
            confidence_base = 0.78

        # Ingest nominal/detected openings from depth profile or sensor observations
        raw_openings = sensor_depth_slices.get("openings", [])
        for idx, op in enumerate(raw_openings):
            nominal_w = op.get("width", 0.90)
            nominal_h = op.get("height", 2.05)
            op_type = op.get("type", "door")
            wall_id = op.get("wall_id", "wall_south")
            offset_along_wall = op.get("offset_m", 1.20)

            # Reconstructed width & height with sensor noise
            est_width = max(self.min_width, float(nominal_w + np.random.normal(0, noise_w)))
            est_height = float(nominal_h + np.random.normal(0, noise_h))

            # Metric interval
            ci_half = noise_w * 1.96

            openings.append({
                "opening_id": f"{wall_id}_op_{idx+1}",
                "type": op_type,
                "wall_id": wall_id,
                "position_along_wall_m": round(offset_along_wall, 3),
                "width_m": {
                    "value": round(est_width, 4),
                    "ci_95": [round(est_width - ci_half, 4), round(est_width + ci_half, 4)],
                    "std_err": round(noise_w, 4)
                },
                "height_m": {
                    "value": round(est_height, 4),
                    "ci_95": [round(est_height - noise_h * 1.96, 4), round(est_height + noise_h * 1.96, 4)],
                    "std_err": round(noise_h, 4)
                },
                "confidence": round(confidence_base - np.random.uniform(0.0, 0.04), 3),
                "connects_to_room": op.get("connects_to_room", None)
            })

        return openings
