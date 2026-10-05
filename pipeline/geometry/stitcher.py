"""Multi-Room Floor Plan Stitcher and Topological Adjacency Graph Solver."""

import numpy as np
from typing import Dict, List, Any
from shapely.geometry import Polygon

class FloorPlanStitcher:
    """Stitches individual reconstructed rooms into a global whole-property floor plan."""

    def __init__(self):
        pass

    def stitch_rooms(
        self,
        room_geometries: Dict[str, Dict[str, Any]],
        optimized_poses: Dict[str, List[float]],
        adjacency_graph: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Transforms all rooms to global coordinates and validates non-overlapping topology."""
        global_rooms = {}
        polygons = {}
        all_points = []

        for room_id, rdata in room_geometries.items():
            pose = optimized_poses.get(room_id, [0.0, 0.0, 0.0])
            tx, ty, theta = pose

            cos_t = np.cos(theta)
            sin_t = np.sin(theta)
            rot = np.array([[cos_t, -sin_t], [sin_t, cos_t]])

            # Transform wall segments
            trans_walls = []
            room_pts = []
            for w in rdata["walls"]:
                sp = np.array(w["start_point"])
                ep = np.array(w["end_point"])

                g_sp = (rot @ sp + np.array([tx, ty])).tolist()
                g_ep = (rot @ ep + np.array([tx, ty])).tolist()

                trans_walls.append({
                    "wall_id": f"{room_id}_{w['wall_id']}",
                    "local_wall_id": w["wall_id"],
                    "start_point": [round(g_sp[0], 4), round(g_sp[1], 4)],
                    "end_point": [round(g_ep[0], 4), round(g_ep[1], 4)],
                    "length_m": w["length_m"],
                    "orientation_deg": round((w["orientation_deg"] + np.degrees(theta)) % 360, 2)
                })
                room_pts.append(g_sp)
                all_points.append(g_sp)

            # Room polygon in global coordinates
            poly = Polygon(room_pts)
            polygons[room_id] = poly

            global_rooms[room_id] = {
                "room_id": room_id,
                "name": rdata.get("name", room_id),
                "global_pose": [round(tx, 4), round(ty, 4), round(theta, 4)],
                "walls": trans_walls,
                "ceiling_height_m": rdata["ceiling_height_m"],
                "floor_area_m2": round(poly.area, 3),
                "openings": rdata.get("openings", [])
            }

        # Check for invalid room overlaps (excluding shared boundary walls)
        overlap_warnings = []
        room_ids = list(global_rooms.keys())
        for i in range(len(room_ids)):
            for j in range(i + 1, len(room_ids)):
                r1, r2 = room_ids[i], room_ids[j]
                inter = polygons[r1].intersection(polygons[r2])
                if inter.area > 0.05: # >0.05 m2 overlap is non-physical
                    overlap_warnings.append(f"Overlap detected between {r1} and {r2}: {inter.area:.3f} m2")

        # Total property footprint bounding box
        all_pts_arr = np.array(all_points)
        min_x, min_y = np.min(all_pts_arr, axis=0)
        max_x, max_y = np.max(all_pts_arr, axis=0)
        total_footprint_m2 = round(sum(r["floor_area_m2"] for r in global_rooms.values()), 3)

        return {
            "property_envelope": {
                "min_x": round(float(min_x), 4),
                "min_y": round(float(min_y), 4),
                "max_x": round(float(max_x), 4),
                "max_y": round(float(max_y), 4),
                "total_span_x_m": round(float(max_x - min_x), 4),
                "total_span_y_m": round(float(max_y - min_y), 4),
                "total_floor_area_m2": total_footprint_m2
            },
            "stitched_rooms": global_rooms,
            "adjacency_connections": adjacency_graph,
            "topology_valid": len(overlap_warnings) == 0,
            "overlap_warnings": overlap_warnings
        }
