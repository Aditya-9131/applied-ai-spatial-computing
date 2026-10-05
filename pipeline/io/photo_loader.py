"""Tier 1: Multi-view Photo Folder Ingestion and Monocular Room Layout Estimator.

DISCLOSURE: NOT IMPLEMENTED: simulated.
No live monocular depth (Depth-Anything-V2) or room layout model (HorizonNet)
is bundled with this runtime. All hard-coded room geometry and damage literals
have been completely removed to prevent benchmark ground truth leakage.
Tier 1 photos are excluded from claimed benchmark passes.
"""

import os
import glob
from typing import Dict, List, Any


class PhotoTierLoader:
    """Ingests still photos per room from iPhone 15 or newer without poses or depth."""

    def __init__(self):
        self.model_disclosure = {
            "depth_backbone": "NOT IMPLEMENTED: simulated",
            "layout_estimator": "NOT IMPLEMENTED: simulated",
            "feature_matcher": "NOT IMPLEMENTED: simulated",
            "scale_prior": "NOT IMPLEMENTED: simulated",
            "status": "NOT IMPLEMENTED: simulated"
        }

    def load_room_photos(self, room_folder_path: str) -> Dict[str, Any]:
        """Scans image files in a room folder, reporting NOT IMPLEMENTED: simulated."""
        image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.heic", "*.JPG", "*.PNG"]
        image_paths = []
        if os.path.exists(room_folder_path):
            for ext in image_extensions:
                image_paths.extend(glob.glob(os.path.join(room_folder_path, ext)))

        room_name = os.path.basename(os.path.normpath(room_folder_path))
        num_images = len(image_paths)

        return {
            "tier": "photos",
            "room_id": room_name,
            "image_count": num_images,
            "image_paths": image_paths,
            "model_disclosure": self.model_disclosure,
            "estimated_room_geometry": {
                "room_id": room_name,
                "name": room_name.replace("_", " ").title(),
                "status": "NOT IMPLEMENTED: simulated",
                "walls": [],
                "openings": []
            },
            "status": "NOT IMPLEMENTED: simulated"
        }

    def load_whole_property_photos(self, photos_base_dir: str) -> Dict[str, Any]:
        """Loads per-room photo folders with disclosure of simulated/not-implemented status."""
        rooms = []
        room_names = ["living_room", "hallway", "kitchen", "master_bedroom"]
        for rname in room_names:
            rpath = os.path.join(photos_base_dir, rname)
            rdata = self.load_room_photos(rpath)
            rooms.append(rdata["estimated_room_geometry"])

        return {
            "property_id": "BENCHMARK_MULTI_ROOM_PHOTOS",
            "device": "iPhone 15",
            "tier": "photos",
            "model_disclosure": self.model_disclosure,
            "status": "NOT IMPLEMENTED: simulated",
            "rooms": [],
            "staged_damages": [],
            "relative_odometry_edges": []
        }
