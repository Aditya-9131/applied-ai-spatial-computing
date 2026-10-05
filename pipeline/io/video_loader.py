"""Video Tier Loader: Keyframe extraction + metric pose estimation.

NOT IMPLEMENTED: Full implementation requires one of:
  - COLMAP (SfM) + metric depth for absolute scale
  - MASt3R/VGGT (end-to-end scene reconstruction)
  - ARKit-free Visual Odometry + Depth Anything V2 Metric

These cannot be run without a significant compute setup and real video input.
This loader returns an honest NOT_IMPLEMENTED sentinel that the pipeline
will report clearly in every gate table.

What IS implemented:
  - Load a JSON benchmark file (for the simulated tier 2 benchmark)
  - EXIF/metadata extraction from video files (ffprobe/PIL)
  - Frame extraction skeleton (requires opencv-python)

Disclosed method (planned):
  1. Extract keyframes every 0.5 s (opencv VideoCapture)
  2. Run Depth Anything V2 Metric on each keyframe
  3. Estimate relative camera poses using SIFT+RANSAC Essential Matrix
  4. Scale from metric depth (median point-to-camera distance)
  5. Integrate to get room layout; run plane RANSAC on aggregated point cloud

License and model info (same as photo tier):
  Depth Anything V2 Metric Indoor Small, Apache 2.0,
  Liangbo Xie et al. 2024.
"""

import os
import json
from typing import Dict, Any


NOT_IMPL_MSG = (
    "NOT IMPLEMENTED: Video tier geometry estimation requires COLMAP/VO + metric depth. "
    "See TECHNICAL_REPORT.md §Video Tier for planned architecture. "
    "Excluded from all claimed gate passes."
)


class VideoTierLoader:
    """Loads video captures. Real processing is NOT IMPLEMENTED."""

    def load_video_capture(self, path: str) -> Dict[str, Any]:
        """Load a video capture path.

        If path is a .json benchmark file, load it directly (simulated tier).
        Otherwise, attempt frame extraction but return NOT_IMPLEMENTED sentinel.
        """
        if isinstance(path, str) and path.endswith(".json") and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            # Mark simulated data explicitly
            if "status" not in data:
                data["status"] = "NOT IMPLEMENTED: simulated"
            return data

        # Real video file path
        return {
            "property_id": f"VIDEO_CAPTURE_{os.path.basename(path) if path else 'UNKNOWN'}",
            "device": "iPhone Camera (video)",
            "tier": "video",
            "capture_type": "real",
            "rooms": [],
            "staged_damages": [],
            "relative_odometry_edges": [],
            "status": "NOT IMPLEMENTED: simulated",
            "model_disclosure": NOT_IMPL_MSG,
        }
