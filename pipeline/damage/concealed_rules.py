"""Concealed Damage Expert Rules Engine for Insurance & Restoration Assessment."""

from typing import Dict, List, Any

class ConcealedDamageEngine:
    """Evaluates spatial damage interactions and fires deterministic concealed damage rules."""

    def __init__(self):
        self.rules = [
            {
                "rule_id": "RULE_WATER_BEHIND_BASEBOARD",
                "name": "Baseboard Water Intrusion Drywall Cavity Rot",
                "condition": self._check_water_baseboard,
                "description": "Visible water staining near wall base suggests trapped moisture behind baseboards and insulation degradation inside drywall stud cavity."
            },
            {
                "rule_id": "RULE_CEILING_PLUMBING_LEAK",
                "name": "Overhead Wet Plumb Concealed Joist Damage",
                "condition": self._check_ceiling_leak,
                "description": "Ceiling water staining under second-story plumbing fixture indicates saturated subfloor insulation and potential concealed joist rot."
            },
            {
                "rule_id": "RULE_STRUCTURAL_SHEAR_CRACK",
                "name": "Diagonal Shear Crack Stud Deflection",
                "condition": self._check_shear_crack,
                "description": "Continuous diagonal shear crack >1.2m across load-bearing wall indicates foundation settlement and concealed timber/stud framing distortion."
            },
            {
                "rule_id": "RULE_CAVITY_MOLD_PROLIFERATION",
                "name": "Interior Wall Mold Behind Vapor Barrier",
                "condition": self._check_cavity_mold,
                "description": "Visible mold cluster >0.4m2 indicates severe hidden fungal colonization behind vapor barrier requiring containment breach protocol."
            }
        ]

    def _check_water_baseboard(self, region: Dict[str, Any], context: Dict[str, Any]) -> bool:
        area = region.get("metric_extent", {}).get("area_m2")
        return region.get("damage_class") == "water_damage" and "wall" in region.get("surface_id", "") and area is not None and area >= 0.8

    def _check_ceiling_leak(self, region: Dict[str, Any], context: Dict[str, Any]) -> bool:
        return region.get("damage_class") == "water_damage" and ("ceiling" in region.get("surface_id", "") or region.get("surface_type") == "ceiling")

    def _check_shear_crack(self, region: Dict[str, Any], context: Dict[str, Any]) -> bool:
        if region.get("damage_class") == "wall_crack":
            lin = region.get("metric_extent", {}).get("linear_length_m")
            return lin is not None and lin >= 1.2
        return False

    def _check_cavity_mold(self, region: Dict[str, Any], context: Dict[str, Any]) -> bool:
        area = region.get("metric_extent", {}).get("area_m2")
        return region.get("damage_class") == "mold_growth" and area is not None and area >= 0.4

    def evaluate_flags(
        self,
        damage_regions: List[Dict[str, Any]],
        property_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Evaluates all damage regions against concealed risk rules and generates audit flags."""
        fired_flags = []

        for dmg in damage_regions:
            for rule in self.rules:
                if rule["condition"](dmg, property_context):
                    fired_flags.append({
                        "flag_id": f"FLAG_{dmg['damage_id']}_{rule['rule_id']}",
                        "damage_id": dmg["damage_id"],
                        "surface_id": dmg["surface_id"],
                        "rule_fired": rule["rule_id"],
                        "rule_title": rule["name"],
                        "justification": rule["description"],
                        "recommended_investigation": "Non-destructive thermal/moisture probe + selective inspection cut",
                        "risk_level": "HIGH" if "MOLD" in rule["rule_id"] or "STRUCTURAL" in rule["rule_id"] else "MEDIUM"
                    })

        return fired_flags
