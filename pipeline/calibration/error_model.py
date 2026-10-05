"""Calibrated Uncertainty and Confidence Interval Modeling across Sensor Tiers."""

import os
import json
from typing import Dict, Any, Optional

_BOUNDS_PATH = os.path.join(os.path.dirname(__file__), "empirical_bounds.json")

def _load_empirical_bounds() -> Optional[Dict[str, Any]]:
    if os.path.exists(_BOUNDS_PATH):
        try:
            with open(_BOUNDS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

_EMPIRICAL_BOUNDS = _load_empirical_bounds()

class SensorErrorModel:
    """Computes calibrated confidence intervals (95% CI) and empirical error bounds per sensor tier."""

    # Base specs; LiDAR values are dynamically overridden by empirical_bounds.json when present.
    TIER_SPECS = {
        "lidar": {
            "wall_length_abs_ci_m": 0.0236,   # ±2.36 cm (empirical 95th percentile)
            "wall_length_pct_ci": 1.46,       # ±1.46%
            "ceiling_height_abs_ci_m": 0.0074,# ±0.74 cm (empirical 95th percentile)
            "opening_width_abs_ci_m": 0.0128, # ±1.28 cm (empirical 95th percentile)
            "floor_area_pct_ci": 2.5,
            "nominal_coverage_factor": 1.96,
            "calibration_score": 0.98,
            "is_calibrated": True,
            "is_simulated": False,
        },
        "video": {
            "wall_length_pct_ci": 3.0,
            "ceiling_height_abs_ci_m": 0.055,
            "opening_width_abs_ci_m": 0.065,
            "floor_area_pct_ci": 4.5,
            "nominal_coverage_factor": 1.96,
            "calibration_score": 0.92,
            "is_calibrated": False,
            "is_simulated": True,
            "status": "NOT IMPLEMENTED: simulated",
        },
        "photos": {
            "wall_length_pct_ci": 8.0,
            "ceiling_height_abs_ci_m": 0.140,
            "opening_width_abs_ci_m": 0.150,
            "floor_area_pct_ci": 9.5,
            "nominal_coverage_factor": 1.96,
            "calibration_score": 0.85,
            "is_calibrated": False,
            "is_simulated": True,
            "status": "NOT IMPLEMENTED: simulated",
        }
    }

    # Dynamically inject loaded empirical calibration stats for LiDAR tier
    if _EMPIRICAL_BOUNDS and _EMPIRICAL_BOUNDS.get("tier") == "lidar":
        _stats = _EMPIRICAL_BOUNDS.get("calibration_stats", {})
        _cov = _EMPIRICAL_BOUNDS.get("held_out_empirical_coverage_pct", {})
        TIER_SPECS["lidar"].update({
            "wall_length_abs_ci_m": _stats.get("wall_length_abs_ci_m", 0.0236),
            "wall_length_pct_ci": _stats.get("wall_length_pct_ci", 1.46),
            "ceiling_height_abs_ci_m": _stats.get("ceiling_height_abs_ci_m", 0.0074),
            "opening_width_abs_ci_m": _stats.get("opening_width_abs_ci_m", 0.0128),
            "held_out_coverage_pct": _cov,
            "derivation": _EMPIRICAL_BOUNDS.get("derivation", "empirical_95th_percentile_of_absolute_error"),
            "calibration_note": _EMPIRICAL_BOUNDS.get("note", ""),
        })

    @classmethod
    def get_tier_uncertainty(cls, tier: str) -> Dict[str, Any]:
        """Returns the empirical error budget and confidence parameters for a given tier."""
        tier_key = tier.lower()
        return cls.TIER_SPECS.get(tier_key, cls.TIER_SPECS["photos"])

    @classmethod
    def apply_measurement_ci(cls, value: float, measurement_type: str, tier: str) -> Dict[str, Any]:
        """Attaches honest 95% confidence intervals to a single metric measurement."""
        spec = cls.get_tier_uncertainty(tier)
        cov_factor = spec.get("nominal_coverage_factor", 1.96)

        if measurement_type == "wall_length":
            if "wall_length_abs_ci_m" in spec:
                delta = spec["wall_length_abs_ci_m"]
            else:
                pct = spec.get("wall_length_pct_ci", 3.0)
                delta = value * (pct / 100.0)
            std_err = delta / cov_factor
        elif measurement_type == "floor_area":
            pct = spec.get("floor_area_pct_ci", 3.0)
            delta = value * (pct / 100.0)
            std_err = delta / cov_factor
        elif measurement_type == "ceiling_height":
            delta = spec["ceiling_height_abs_ci_m"]
            std_err = delta / cov_factor
        elif measurement_type == "opening_width":
            delta = spec["opening_width_abs_ci_m"]
            std_err = delta / cov_factor
        else:
            delta = value * 0.05
            std_err = delta / 1.96

        return {
            "value": round(float(value), 4),
            "ci_95": [round(float(value - delta), 4), round(float(value + delta), 4)],
            "std_error": round(float(std_err), 4),
            "unit": "m" if "area" not in measurement_type else "m2",
            "tier_calibrated": tier
        }
