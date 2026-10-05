"""JSON Schema and validation for Spatial Reconstruction and Damage Assessment Output Contract."""

from typing import Dict, List, Any, Optional
import json

SCHEMA_VERSION = "2026.08.1"

def create_output_contract(
    property_id: str,
    tier: str,
    device_model: str,
    rooms: List[Dict[str, Any]],
    stitched_plan: Dict[str, Any],
    damage_assessment: Dict[str, Any],
    concealed_flags: List[Dict[str, Any]],
    scope_of_work: List[Dict[str, Any]],
    calibration_metrics: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generates a complete, schema-compliant output dictionary."""
    return {
        "schema_version": SCHEMA_VERSION,
        "property_id": property_id,
        "capture_metadata": {
            "input_tier": tier,
            "device_model": device_model,
            "capture_timestamp": (metadata or {}).get("timestamp", "2026-08-20T14:30:00Z"),
            # NOTE: processing_time_seconds is a wall-clock measurement and is NOT part of the
            # deterministic output. It is isolated here so byte-identity checks can exclude it
            # by stripping capture_metadata.timing without touching any measurement values.
            "timing": {
                "processing_time_seconds": (metadata or {}).get("processing_time_s", 0.0)
            },
            "drift_correction_enabled": (metadata or {}).get("drift_correction", True),
            "opening_detector": (metadata or {}).get("opening_detector", "DEPTH_DISCONTINUITY_GRADIENT_PEAK"),
        },
        "rooms": rooms,
        "stitched_plan": stitched_plan,
        "damage_assessment": damage_assessment,
        "concealed_damage_flags": concealed_flags,
        "scope_of_work": scope_of_work,
        "calibration_and_confidence": calibration_metrics
    }

def validate_contract(data: Dict[str, Any]) -> bool:
    """Validates that all required top-level and nested fields are present."""
    required_top = [
        "schema_version", "property_id", "capture_metadata", 
        "rooms", "stitched_plan", "damage_assessment", 
        "concealed_damage_flags", "scope_of_work", "calibration_and_confidence"
    ]
    for key in required_top:
        if key not in data:
            raise ValueError(f"Schema violation: missing required key '{key}'")
    
    # Validate rooms
    for r in data["rooms"]:
        for rk in ["room_id", "name", "ceiling_height", "floor_area", "walls", "openings"]:
            if rk not in r:
                raise ValueError(f"Room schema violation: missing '{rk}' in room {r.get('room_id')}")
        # Validate confidence intervals on measurements
        if "value" not in r["ceiling_height"] or "ci_95" not in r["ceiling_height"]:
            raise ValueError(f"Measurement confidence interval missing in ceiling_height of {r['room_id']}")
    
    return True
