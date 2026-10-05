"""Calibrated Uncertainty and Confidence Interval Modeling across Sensor Tiers."""

from typing import Dict, Any

class SensorErrorModel:
    """Computes calibrated confidence intervals (95% CI) and empirical error bounds per sensor tier."""

    TIER_SPECS = {
        "lidar": {
            "wall_length_pct_ci": 0.5, # ±0.5% (typically ~1.0-1.5cm on 3-4m walls)
            "ceiling_height_abs_ci_m": 0.015, # ±1.5 cm
            "opening_width_abs_ci_m": 0.020, # ±2.0 cm
            "floor_area_pct_ci": 1.2, # ±1.2%
            "nominal_coverage_factor": 1.96, # 95% Gaussian coverage
            "calibration_score": 0.98
        },
        "video": {
            "wall_length_pct_ci": 3.0, # ±3.0%
            "ceiling_height_abs_ci_m": 0.055, # ±5.5 cm
            "opening_width_abs_ci_m": 0.065, # ±6.5 cm
            "floor_area_pct_ci": 4.5, # ±4.5%
            "nominal_coverage_factor": 1.96,
            "calibration_score": 0.92
        },
        "photos": {
            "wall_length_pct_ci": 8.0, # ±8.0%
            "ceiling_height_abs_ci_m": 0.140, # ±14.0 cm
            "opening_width_abs_ci_m": 0.150, # ±15.0 cm
            "floor_area_pct_ci": 9.5, # ±9.5%
            "nominal_coverage_factor": 1.96,
            "calibration_score": 0.85
        }
    }

    @classmethod
    def get_tier_uncertainty(cls, tier: str) -> Dict[str, Any]:
        """Returns the empirical error budget and confidence parameters for a given tier."""
        tier_key = tier.lower()
        return cls.TIER_SPECS.get(tier_key, cls.TIER_SPECS["photos"])

    @classmethod
    def apply_measurement_ci(cls, value: float, measurement_type: str, tier: str) -> Dict[str, Any]:
        """Attaches honest 95% confidence intervals to a single metric measurement."""
        spec = cls.get_tier_uncertainty(tier)

        if measurement_type in ["wall_length", "floor_area"]:
            pct = spec[f"{measurement_type}_pct_ci"]
            delta = value * (pct / 100.0)
            std_err = delta / spec["nominal_coverage_factor"]
        elif measurement_type == "ceiling_height":
            delta = spec["ceiling_height_abs_ci_m"]
            std_err = delta / spec["nominal_coverage_factor"]
        elif measurement_type == "opening_width":
            delta = spec["opening_width_abs_ci_m"]
            std_err = delta / spec["nominal_coverage_factor"]
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
