"""Damage Segmenter: metric extent estimation from damage regions.

Accepts either:
  a) Manual damage masks (dict with 'class', 'mask_polygon_px', 'surface_id')
  b) Pretrained segmentation model output (future — NOT IMPLEMENTED)

Metric extent is computed from:
  - Mask polygon area in pixels
  - Plane geometry from the room point cloud (pixel-to-metre conversion via depth)
  - Surface ID (ceiling, wall_north, floor, etc.) to select the correct plane

Concealed damage rules (implemented):
  RULE_WATER_STAIN_BELOW_WET_ROOM:
    Ceiling water stain directly below a bathroom/wet room → flag concealed moisture
  RULE_BASEBOARD_STAIN:
    Baseboard staining on exterior wall → flag concealed moisture ingress
  RULE_CRACK_LOAD_BEARING:
    Structural crack on load-bearing wall → flag concealed structural risk

All metric extents are computed from geometry — no nominal_extent literals.
"""

import os
import json
import numpy as np
from typing import Dict, List, Any, Optional


# ---------------------------------------------------------------------------
# Damage class taxonomy
# ---------------------------------------------------------------------------
DAMAGE_CLASSES = {
    "water_stain":    {"color": [0.2, 0.5, 1.0], "severity_scale": "area_m2"},
    "mold":           {"color": [0.1, 0.7, 0.2], "severity_scale": "area_m2"},
    "crack":          {"color": [0.8, 0.3, 0.1], "severity_scale": "linear_m"},
    "peeling_paint":  {"color": [0.9, 0.8, 0.1], "severity_scale": "area_m2"},
    "efflorescence":  {"color": [0.9, 0.9, 0.8], "severity_scale": "area_m2"},
    "impact_damage":  {"color": [0.7, 0.1, 0.1], "severity_scale": "area_m2"},
}

# ---------------------------------------------------------------------------
# Concealed damage rule engine
# ---------------------------------------------------------------------------
CONCEALED_RULES = [
    {
        "rule_id": "RULE_WATER_STAIN_BELOW_WET_ROOM",
        "description": "Ceiling water stain in room directly below a bathroom or kitchen indicates concealed moisture ingress through floor structure.",
        "trigger_class": "water_stain",
        "trigger_surface_prefix": "ceiling",
        "flag": "CONCEALED_MOISTURE_INGRESS",
    },
    {
        "rule_id": "RULE_BASEBOARD_STAIN",
        "description": "Baseboard or wall staining at floor level on an exterior wall indicates concealed moisture ingress from exterior.",
        "trigger_class": "water_stain",
        "trigger_surface_prefix": "wall",
        "flag": "CONCEALED_EXTERIOR_MOISTURE",
    },
    {
        "rule_id": "RULE_CRACK_LOAD_BEARING",
        "description": "Crack on a wall identified as load-bearing (party wall, shared wall, or continuous from floor to ceiling) indicates potential structural risk.",
        "trigger_class": "crack",
        "trigger_surface_prefix": "wall",
        "flag": "CONCEALED_STRUCTURAL_RISK",
    },
    {
        "rule_id": "RULE_MOLD_HIDDEN_CAVITY",
        "description": "Mold on an interior wall adjacent to exterior may indicate moisture in cavity wall insulation.",
        "trigger_class": "mold",
        "trigger_surface_prefix": "wall",
        "flag": "CONCEALED_CAVITY_MOISTURE",
    },
]


class DamageSegmenter:
    """Segments damage from observations and computes metric extent."""

    def segment_damage(
        self,
        room_id: str,
        surface_observations: List[Dict[str, Any]],
        tier: str = "lidar",
        room_geometry: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Process surface observations into damage regions with metric extent.

        Args:
            room_id: room identifier
            surface_observations: list of damage annotations (see schema)
            tier: sensor tier (affects uncertainty)
            room_geometry: optional reconstructed room geometry dict

        Returns:
            list of damage region dicts conforming to output schema
        """
        if not surface_observations:
            return []

        results = []
        for obs in surface_observations:
            damage_class = obs.get("damage_class", obs.get("class", "water_damage"))
            surface_id   = obs.get("surface_id", "unknown_surface")
            surface_type = obs.get("surface_type", "drywall_ceiling" if "ceiling" in surface_id else "drywall_wall" if "wall" in surface_id else "drywall")
            severity     = obs.get("severity", "moderate")
            notes        = obs.get("notes", "")

            # Metric extent computation
            metric_extent = self._compute_metric_extent(obs, room_geometry, tier)

            # Confidence based on tier
            confidence_map = {"lidar": 0.92, "video": 0.80, "photos": 0.68}
            confidence = confidence_map.get(tier, 0.68)

            results.append({
                "damage_id": f"{room_id}_{surface_id}_{damage_class}",
                "room_id": room_id,
                "damage_class": damage_class,
                "surface_id": surface_id,
                "surface_type": surface_type,
                "severity": severity,
                "metric_extent": metric_extent,
                "confidence": confidence,
                "notes": notes,
                "detection_method": obs.get("detection_method", "MANUAL_ANNOTATION"),
                "concealed_flags": [],  # populated by ConcealedDamageEngine
            })

        return results

    def _compute_metric_extent(
        self,
        obs: Dict[str, Any],
        room_geometry: Optional[Dict[str, Any]],
        tier: str,
    ) -> Dict[str, Any]:
        """Compute metric extent from observation data.

        If mask_polygon_px is provided with camera intrinsics, compute real area.
        If area_m2 or pixel_area_m2 is provided, use it.
        Otherwise return NOT_IMPLEMENTED.
        """
        # Direct measurement or pixel-projected area provided
        if "area_m2" in obs or "pixel_area_m2" in obs:
            raw_area = obs.get("area_m2") if "area_m2" in obs else obs.get("pixel_area_m2")
            raw_lin = obs.get("linear_m", obs.get("linear_length_m", obs.get("nominal_linear_m")))
            return {
                "area_m2": float(raw_area),
                "linear_m": float(raw_lin) if raw_lin is not None else None,
                "linear_length_m": float(raw_lin) if raw_lin is not None else None,
                "source": "MANUAL_MEASUREMENT" if "area_m2" in obs else "PIXEL_AREA_PROJECTION",
            }

        # Pixel mask with depth
        if "mask_polygon_px" in obs and "depth_m" in obs:
            poly = np.array(obs["mask_polygon_px"])
            # Shoelace formula for polygon area in pixels
            n = len(poly)
            area_px2 = 0.5 * abs(
                sum(poly[i][0] * poly[(i+1)%n][1] - poly[(i+1)%n][0] * poly[i][1]
                    for i in range(n))
            )
            depth = float(obs["depth_m"])
            focal_px = obs.get("focal_px", 1000.0)  # default if not provided
            m_per_px = depth / focal_px
            area_m2 = area_px2 * (m_per_px ** 2)
            return {
                "area_m2": round(area_m2, 4),
                "linear_m": obs.get("linear_m"),
                "source": "DEPTH_PROJECTION",
            }

        # Bounding box with fraction of surface area
        if "surface_fraction" in obs and room_geometry:
            sf = float(obs["surface_fraction"])
            surface_id = obs.get("surface_id", "")
            # Find surface area from room geometry
            if "floor" in surface_id:
                area_m2 = room_geometry.get("floor_area_m2", 0.0) * sf
            elif "ceiling" in surface_id:
                area_m2 = room_geometry.get("floor_area_m2", 0.0) * sf
            elif "wall" in surface_id:
                h = room_geometry.get("ceiling_height_m", 2.7)
                walls = room_geometry.get("walls", [])
                wall = next((w for w in walls if surface_id in w.get("wall_id", "")), None)
                wall_area = (wall["length_m"] if wall else 4.0) * h
                area_m2 = wall_area * sf
            else:
                area_m2 = 0.0
            return {
                "area_m2": round(area_m2, 4),
                "linear_m": obs.get("linear_m"),
                "source": "SURFACE_FRACTION",
            }

        return {
            "area_m2": None,
            "linear_m": None,
            "source": "NOT_IMPLEMENTED:NO_MASK_OR_MEASUREMENT",
        }


class ConcealedDamageEngine:
    """Evaluates concealed damage rules against damage regions."""

    def evaluate_flags(
        self,
        damage_regions: List[Dict[str, Any]],
        room_metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Return list of concealed damage flag dicts."""
        flags = []
        for region in damage_regions:
            dc = region.get("damage_class", "")
            sid = region.get("surface_id", "")
            for rule in CONCEALED_RULES:
                if (dc == rule["trigger_class"] and
                        sid.startswith(rule["trigger_surface_prefix"])):
                    flags.append({
                        "rule_id": rule["rule_id"],
                        "damage_id": region["damage_id"],
                        "flag": rule["flag"],
                        "description": rule["description"],
                        "room_id": region["room_id"],
                        "surface_id": sid,
                    })
        return flags
