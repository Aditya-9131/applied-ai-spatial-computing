"""Real LiDAR capture loader: PLY and OBJ point clouds from mobile apps.

Supported inputs:
  - PLY (binary or ASCII) from 3D Scanner App, Polycam, LIDAR 3D Scanner
  - OBJ (mesh) from Polycam, RoomScan Pro, Canvas

The loader returns a capture_data dict identical in schema to the simulated
multi_room_lidar.json so run_pipeline.py can consume it without modification.

Each room in the PLY/OBJ is treated as a single-room capture. For multi-room
exports the user should segment by room before providing files, or pass a
directory containing one PLY/OBJ per room.

Opening detection falls back to the point-cloud occupancy-gap method.
No ground-truth is read here.
"""

import os
import json
import struct
import numpy as np
from typing import Dict, List, Any, Optional


class LiDARTierLoader:
    """Loads real LiDAR captures (PLY/OBJ) or falls back to JSON benchmark data."""

    def load_ply(self, ply_path: str) -> List[List[float]]:
        """Parse a PLY file (ASCII or binary little-endian) and return [[x,y,z], ...]."""
        with open(ply_path, "rb") as f:
            raw = f.read()

        lines = raw.split(b"\n")
        header_end = 0
        n_vertices = 0
        fmt = "ascii"
        x_idx = y_idx = z_idx = 0
        prop_count = 0
        prop_types: List[str] = []

        for i, line in enumerate(lines):
            txt = line.decode("utf-8", errors="replace").strip()
            if txt == "end_header":
                header_end = i + 1
                break
            if txt.startswith("element vertex"):
                n_vertices = int(txt.split()[-1])
            if txt.startswith("format"):
                fmt = txt.split()[1]  # ascii / binary_little_endian / binary_big_endian
            if txt.startswith("property"):
                parts = txt.split()
                prop_types.append(parts[1])
                name = parts[2]
                if name == "x":
                    x_idx = prop_count
                elif name == "y":
                    y_idx = prop_count
                elif name == "z":
                    z_idx = prop_count
                prop_count += 1

        pts: List[List[float]] = []

        if fmt == "ascii":
            for line in lines[header_end: header_end + n_vertices]:
                vals = line.decode("utf-8", errors="replace").strip().split()
                if len(vals) >= 3:
                    try:
                        pts.append([float(vals[x_idx]), float(vals[y_idx]), float(vals[z_idx])])
                    except ValueError:
                        pass
        else:
            # Binary: reconstruct byte offset past header
            header_bytes = b"\n".join(lines[:header_end]) + b"\n"
            data_bytes = raw[len(header_bytes):]

            # Build struct format string
            fmt_map = {"float": "f", "double": "d", "uchar": "B", "int": "i",
                       "uint": "I", "short": "h", "ushort": "H"}
            size_map = {"float": 4, "double": 8, "uchar": 1, "int": 4,
                        "uint": 4, "short": 2, "ushort": 2}
            struct_fmt = "<" + "".join(fmt_map.get(t, "f") for t in prop_types)
            row_size = sum(size_map.get(t, 4) for t in prop_types)

            for i in range(n_vertices):
                offset = i * row_size
                try:
                    vals = struct.unpack_from(struct_fmt, data_bytes, offset)
                    pts.append([float(vals[x_idx]), float(vals[y_idx]), float(vals[z_idx])])
                except struct.error:
                    break

        return pts

    def load_obj(self, obj_path: str) -> List[List[float]]:
        """Extract vertex positions from an OBJ file."""
        pts: List[List[float]] = []
        with open(obj_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("v "):
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        try:
                            pts.append([float(parts[1]), float(parts[2]), float(parts[3])])
                        except ValueError:
                            pass
        return pts

    def load_real_lidar_capture(self, path: str) -> Dict[str, Any]:
        """Load a real LiDAR capture from a PLY, OBJ, or directory of per-room files.

        Returns a capture_data dict compatible with run_pipeline.py.
        """
        if os.path.isdir(path):
            return self._load_directory(path)
        ext = os.path.splitext(path)[1].lower()
        if ext == ".ply":
            pts = self.load_ply(path)
        elif ext == ".obj":
            pts = self.load_obj(path)
        elif ext == ".json":
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        else:
            raise ValueError(f"Unsupported LiDAR file format: {ext}. Expected .ply, .obj, or .json")

        room_id = os.path.splitext(os.path.basename(path))[0]
        return self._wrap_single_room(room_id, pts)

    def _load_directory(self, dir_path: str) -> Dict[str, Any]:
        """Load a directory where each PLY/OBJ = one room."""
        rooms = []
        for fname in sorted(os.listdir(dir_path)):
            fpath = os.path.join(dir_path, fname)
            ext = os.path.splitext(fname)[1].lower()
            if ext not in (".ply", ".obj"):
                continue
            if ext == ".ply":
                pts = self.load_ply(fpath)
            else:
                pts = self.load_obj(fpath)
            room_id = os.path.splitext(fname)[0]
            rooms.append({
                "room_id": room_id,
                "name": room_id.replace("_", " ").title(),
                "point_cloud_xyz": pts,
                "openings": [],
            })

        if not rooms:
            raise ValueError(f"No PLY/OBJ files found in {dir_path}")

        return {
            "property_id": f"REAL_LIDAR_{os.path.basename(dir_path)}",
            "device": "iPhone LiDAR (3D Scanner App / Polycam)",
            "tier": "lidar",
            "capture_type": "real",
            "rooms": rooms,
            "staged_damages": [],
            "relative_odometry_edges": [],
            "model_disclosure": (
                "Real LiDAR capture. No ML model used for geometry. "
                "Point cloud loaded directly from PLY/OBJ export."
            ),
        }

    def _wrap_single_room(self, room_id: str, pts: List[List[float]]) -> Dict[str, Any]:
        return {
            "property_id": f"REAL_LIDAR_{room_id}",
            "device": "iPhone LiDAR (3D Scanner App / Polycam)",
            "tier": "lidar",
            "capture_type": "real",
            "rooms": [{
                "room_id": room_id,
                "name": room_id.replace("_", " ").title(),
                "point_cloud_xyz": pts,
                "openings": [],
            }],
            "staged_damages": [],
            "relative_odometry_edges": [],
            "model_disclosure": (
                "Real LiDAR capture. No ML model used for geometry. "
                "Point cloud loaded directly from PLY/OBJ export."
            ),
        }

    def load_video_capture(self, path: str) -> Dict[str, Any]:
        """Load a LiDAR JSON capture (legacy compatibility)."""
        if path.endswith(".json") and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        raise ValueError(f"LiDARTierLoader.load_video_capture expects a .json path, got: {path}")
