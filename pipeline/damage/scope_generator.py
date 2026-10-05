"""Scope of Work Generator: Insurance-standard line items keyed to damaged surfaces."""

from typing import Dict, List, Any

class ScopeOfWorkGenerator:
    """Generates standard repair and mitigation line items (Xactimate/IICRC compliant)."""

    def __init__(self):
        # Cost table in USD ($)
        self.cost_table = {
            "water_damage": [
                {"code": "WTR-EXTRACT", "description": "Water extraction & moisture mitigation", "unit": "m2", "unit_cost": 18.50},
                {"code": "DRY-TEAROUT", "description": "Tear out wet drywall up to 2ft flood cut", "unit": "m2", "unit_cost": 32.00},
                {"code": "DRY-REPLACE", "description": "Hang, tape & mud 1/2in drywall replacement", "unit": "m2", "unit_cost": 48.00},
                {"code": "PNT-PRIME2C", "description": "Apply stain-blocking primer and 2 finish coats", "unit": "m2", "unit_cost": 24.50}
            ],
            "wall_crack": [
                {"code": "CRK-VGROOVE", "description": "V-groove crack preparation & structural epoxy inject", "unit": "linear_m", "unit_cost": 65.00},
                {"code": "DRY-TAPEFIN", "description": "Mesh tape reinforcement & Level 4 mud finish", "unit": "linear_m", "unit_cost": 28.00},
                {"code": "PNT-TOUCHUP", "description": "Blend and feather paint to nearest corner", "unit": "m2", "unit_cost": 22.00}
            ],
            "mold_growth": [
                {"code": "MLD-CONTAIN", "description": "HEPA negative air pressure containment chamber", "unit": "ea", "unit_cost": 350.00},
                {"code": "MLD-REMED", "description": "Antimicrobial surface wash & HEPA vacuuming", "unit": "m2", "unit_cost": 45.00},
                {"code": "MLD-SEALANT", "description": "Apply fungicidal protective sealant barrier", "unit": "m2", "unit_cost": 29.00}
            ],
            "impact_damage": [
                {"code": "IMP-PATCH", "description": "Drywall California patch & structural backing", "unit": "ea", "unit_cost": 120.00},
                {"code": "PNT-FINISH", "description": "Texture match & paint application", "unit": "m2", "unit_cost": 25.00}
            ]
        }

    def generate_scope(self, damage_regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compiles surface-keyed line items with metric quantities and extended totals."""
        line_items = []
        item_counter = 1

        for dmg in damage_regions:
            dmg_class = dmg.get("damage_class", "water_damage")
            surface_id = dmg.get("surface_id", "unknown_surface")
            area = dmg.get("metric_extent", {}).get("area_m2", 1.0)
            linear = dmg.get("metric_extent", {}).get("linear_length_m", 1.0) or 1.0

            templates = self.cost_table.get(dmg_class, self.cost_table["water_damage"])

            for tpl in templates:
                unit = tpl["unit"]
                if unit == "m2":
                    qty = area
                elif unit == "linear_m":
                    qty = linear
                else: # "ea"
                    qty = 1.0

                unit_cost = tpl["unit_cost"]
                total_cost = round(qty * unit_cost, 2)

                line_items.append({
                    "item_id": f"SCOPE_{item_counter:03d}",
                    "damage_id": dmg["damage_id"],
                    "surface_id": surface_id,
                    "code": tpl["code"],
                    "description": tpl["description"],
                    "quantity": round(qty, 2),
                    "unit": unit,
                    "unit_cost_usd": unit_cost,
                    "total_cost_usd": total_cost
                })
                item_counter += 1

        return line_items
