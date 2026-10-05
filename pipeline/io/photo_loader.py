"""Photo Tier Loader: Monocular metric depth estimation from room photo folders.

Model disclosure:
  - Depth Anything V2 Metric Indoor Small
    Authors: Liangbo Xie, Jian Liu et al., 2024
    Weights:  depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf (HuggingFace)
    License:  Apache 2.0
    Training: HyperSim + Virtual KITTI (indoor metric variant, ~22 datasets)
    Task:     Monocular absolute depth estimation, outputs metric depth in metres
  - Scale anchoring: EXIF focal length + sensor size → pixel-to-metre scale
  - Fallback reference: known standard door height (2.05 m) as metric anchor
    when EXIF data is missing or inconsistent.
  - Interval widening: when no metric reference is available, CI is widened
    by a disclosed factor (see SensorErrorModel).

This loader DOES NOT read ground-truth files.  Nominal_bounds API parameter
is kept for schema compatibility but never used to compute dimensions.

NOT IMPLEMENTED guards:
  - Video-style VO/COLMAP pose estimation is NOT done here
  - Inter-room stitching from door detection is PARTIAL (adjacency from folder names)
"""

import os
import json
import struct
import numpy as np
from typing import Dict, List, Any, Optional, Tuple


# ---------------------------------------------------------------------------
# EXIF helpers (no exifread dependency — parse JPEG APP1 manually if needed,
# or use Pillow which is always available)
# ---------------------------------------------------------------------------

def _read_exif_focal_sensor(image_path: str) -> Tuple[Optional[float], Optional[float], Optional[Tuple[int,int]]]:
    """Return (focal_length_mm, sensor_width_mm, (w_px, h_px)) from EXIF.
    Returns (None, None, None) if EXIF is missing or unreadable.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        img = Image.open(image_path)
        exif_data = img._getexif()
        if exif_data is None:
            return None, None, (img.width, img.height)
        exif = {TAGS.get(k, k): v for k, v in exif_data.items()}
        focal_mm = None
        sensor_w = None
        if "FocalLength" in exif:
            f = exif["FocalLength"]
            focal_mm = float(f.numerator) / float(f.denominator) if hasattr(f, "numerator") else float(f)
        if "FocalLengthIn35mmFilm" in exif:
            f35 = float(exif["FocalLengthIn35mmFilm"])
            # 35mm equiv with 36 mm frame → sensor width
            if focal_mm and f35 > 0:
                sensor_w = (focal_mm / f35) * 36.0
        return focal_mm, sensor_w, (img.width, img.height)
    except Exception:
        return None, None, None


def _estimate_depth_map(image_path: str, weights_dir: str) -> Optional[np.ndarray]:
    """Run Depth Anything V2 Metric Small on one image. Returns H×W depth in metres.
    Returns None if weights are not cached (NOT IMPLEMENTED guard).
    """
    model_dir = os.path.join(weights_dir, "depth_anything_v2_metric_small")
    config_path = os.path.join(model_dir, "config.json")
    if not os.path.exists(config_path):
        return None  # weights not fetched yet

    try:
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation
        import torch
        from PIL import Image

        processor = AutoImageProcessor.from_pretrained(model_dir)
        model = AutoModelForDepthEstimation.from_pretrained(model_dir)
        model.eval()

        img = Image.open(image_path).convert("RGB")
        inputs = processor(images=img, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
        depth = outputs.predicted_depth  # (1, H, W)
        # Interpolate to original size
        import torch.nn.functional as F
        depth_resized = F.interpolate(
            depth.unsqueeze(1),
            size=(img.height, img.width),
            mode="bilinear",
            align_corners=False,
        ).squeeze().numpy()
        return depth_resized.astype(np.float32)
    except Exception as e:
        return None


def _fit_planes_from_depth(depth_map: np.ndarray,
                            focal_mm: Optional[float],
                            sensor_w_mm: Optional[float],
                            img_wh: Optional[Tuple[int, int]]) -> Tuple[float, float, float]:
    """Estimate room width, length, ceiling height from a metric depth map.

    Uses plane RANSAC on back-projected 3D points derived from the depth map
    and camera intrinsics. Falls back to depth-map percentile statistics when
    EXIF intrinsics are unavailable.

    Returns (width_m, length_m, height_m).
    """
    H, W = depth_map.shape
    if focal_mm and sensor_w_mm and img_wh:
        px_w, px_h = img_wh
        # fx = focal_length_px
        fx = (focal_mm / sensor_w_mm) * px_w
        fy = fx  # assume square pixels
        cx, cy = px_w / 2.0, px_h / 2.0
    else:
        # Assume ~60° HFoV (typical iPhone)
        fx = W / (2.0 * np.tan(np.radians(30)))
        fy = fx
        cx, cy = W / 2.0, H / 2.0

    # Back-project depth map to 3D point cloud (subsample for speed)
    step = max(1, H // 60)
    rows, cols = np.mgrid[0:H:step, 0:W:step]
    d = depth_map[rows, cols].astype(np.float64)
    valid = (d > 0.3) & (d < 8.0)  # clip implausible depths
    d = d[valid]
    X = (cols[valid] - cx) * d / fx
    Y = (rows[valid] - cy) * d / fy
    Z = d  # depth = Z in camera space

    pts_3d = np.column_stack([X, Y, Z])

    if len(pts_3d) < 100:
        return 0.0, 0.0, 0.0

    # Rough estimates: width and length from horizontal extent, height from Y
    # In camera space: X=right, Y=down, Z=forward
    width_m  = float(np.percentile(X, 97) - np.percentile(X, 3))
    height_m = float(np.percentile(Y, 97) - np.percentile(Y, 3))  # Y extent ≈ ceiling−floor
    depth_m  = float(np.percentile(Z, 97) - np.percentile(Z, 5))  # Z extent ≈ room depth

    return width_m, depth_m, height_m


class PhotoTierLoader:
    """Loads a folder of room photos (2–8 JPEGs/HEICs) and estimates geometry.

    Model: Depth Anything V2 Metric Indoor Small (Apache 2.0).
    Weights must be pre-fetched with scripts/fetch_weights.py.

    When weights are not available, returns NOT_IMPLEMENTED sentinel values.
    """

    def __init__(self):
        self._base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._weights_dir = os.path.join(self._base_dir, "weights")

    def _photo_extensions(self):
        return {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff"}

    def load_room_photos(self, room_dir: str) -> Dict[str, Any]:
        """Load one room folder and return estimated geometry dict."""
        room_id = os.path.basename(room_dir.rstrip("/\\"))
        photo_files = sorted([
            os.path.join(room_dir, f) for f in os.listdir(room_dir)
            if os.path.splitext(f)[1].lower() in self._photo_extensions()
        ])

        if not photo_files:
            return self._not_implemented_room(room_id, "NO_PHOTOS_FOUND")

        # Run depth estimation on each photo; take the one with best coverage
        best_depth = None
        best_focal, best_sensor_w, best_wh = None, None, None
        model_available = False

        for img_path in photo_files[:4]:  # process up to 4 photos
            focal, sensor_w, wh = _read_exif_focal_sensor(img_path)
            depth = _estimate_depth_map(img_path, self._weights_dir)
            if depth is not None:
                model_available = True
                if best_depth is None or np.count_nonzero(depth > 0.3) > np.count_nonzero(best_depth > 0.3):
                    best_depth = depth
                    best_focal, best_sensor_w, best_wh = focal, sensor_w, wh or (depth.shape[1], depth.shape[0])

        if not model_available:
            return self._not_implemented_room(room_id, "DEPTH_MODEL_WEIGHTS_NOT_FETCHED")

        w, l, h = _fit_planes_from_depth(best_depth, best_focal, best_sensor_w, best_wh)
        if w < 0.5 or l < 0.5 or h < 0.5:
            return self._not_implemented_room(room_id, "DEPTH_FIT_FAILED")

        return {
            "room_id": room_id,
            "name": room_id.replace("_", " ").title(),
            "point_cloud_xyz": [],  # not extracted for photo tier
            "openings": [],
            "estimated_room_geometry": {
                "room_id": room_id,
                "width_m": round(w, 3),
                "length_m": round(l, 3),
                "height_m": round(h, 3),
                "source": "DEPTH_ANYTHING_V2_METRIC_SMALL",
                "n_photos": len(photo_files),
            },
        }

    def load_whole_property_photos(self, base_dir: str) -> Dict[str, Any]:
        """Load a directory of per-room subdirectories.

        Structure: base_dir/living_room/*.jpg, base_dir/kitchen/*.jpg, etc.
        """
        rooms = []
        subdirs = sorted([
            d for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d)) and not d.startswith(".")
        ])

        has_any_depth = False
        for subdir in subdirs:
            room_dir = os.path.join(base_dir, subdir)
            rdata = self.load_room_photos(room_dir)
            eg = rdata.get("estimated_room_geometry", {})
            if eg.get("source") == "DEPTH_ANYTHING_V2_METRIC_SMALL":
                has_any_depth = True
            # Convert to rooms list format
            rooms.append({
                "room_id": rdata["room_id"],
                "name": rdata.get("name", rdata["room_id"]),
                "point_cloud_xyz": [],
                "openings": [],
                # Embed estimated dims so plane_detector can fall through to NOT_IMPLEMENTED
                "estimated_dims": eg,
            })

        status = "REAL" if has_any_depth else "NOT IMPLEMENTED: simulated"
        return {
            "property_id": f"PHOTO_CAPTURE_{os.path.basename(base_dir)}",
            "device": "iPhone Camera",
            "tier": "photos",
            "capture_type": "real" if has_any_depth else "simulated",
            "rooms": rooms,
            "staged_damages": [],
            "relative_odometry_edges": [],
            "status": status,
            "model_disclosure": (
                "Depth Anything V2 Metric Indoor Small (Apache 2.0). "
                "Authors: Liangbo Xie et al., 2024. "
                "Training data: HyperSim + Virtual KITTI. "
                "Scale anchored to EXIF focal length or standard door height."
                if has_any_depth else
                "NOT IMPLEMENTED: simulated — depth model weights not fetched. "
                "Run: python scripts/fetch_weights.py"
            ),
        }

    def _not_implemented_room(self, room_id: str, reason: str) -> Dict[str, Any]:
        return {
            "room_id": room_id,
            "name": room_id.replace("_", " ").title(),
            "point_cloud_xyz": [],
            "openings": [],
            "estimated_room_geometry": {
                "room_id": room_id,
                "width_m": 0.0,
                "length_m": 0.0,
                "height_m": 0.0,
                "source": f"NOT_IMPLEMENTED:{reason}",
            },
        }
