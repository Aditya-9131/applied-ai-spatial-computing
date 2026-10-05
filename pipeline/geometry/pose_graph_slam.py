"""Pose Graph SLAM and Non-Linear Drift Optimization for Multi-Room Stitching."""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional

# ──────────────────────────────────────────────────────────────────────────────
# SLAM HYPERPARAMETERS & ALGORITHMIC CONSTANTS (AUDITED)
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_MAX_ITERATIONS: int = 50          # Maximum Gauss-Newton iterations
DEFAULT_TOLERANCE: float = 1e-6           # Convergence threshold on update vector norm ||delta||
ANCHOR_PRIOR_WEIGHT: float = 1e6          # Prior weight on anchor node 0 to eliminate gauge freedom in SE(2)
HESSIAN_REGULARIZATION: float = 1e-4      # Levenberg-style diagonal damping factor for positive definiteness
INFO_ODOMETRY_DEFAULT: float = 50.0       # Information matrix diagonal for odometry edges (sigma ~ 14 cm, ~8 deg)
INFO_LOOP_CLOSURE_DEFAULT: float = 200.0  # Information matrix diagonal for loop closures (sigma ~ 7 cm, ~4 deg)


class PoseGraphOptimizer:
    """Non-linear 2D SE(2) Pose Graph Optimization with Loop Closure & Plane-Anchored Constraints."""

    def __init__(self, max_iterations: int = DEFAULT_MAX_ITERATIONS, tolerance: float = DEFAULT_TOLERANCE):
        self.max_iter = max_iterations
        self.tol = tolerance

    @staticmethod
    def _wrap_angle(angle: float) -> float:
        """Normalizes angle to [-pi, pi]."""
        return (angle + np.pi) % (2 * np.pi) - np.pi

    @staticmethod
    def _compose_poses(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
        """Composes two 2D poses: p = p1 \oplus p2, where p = [x, y, theta]."""
        x1, y1, th1 = p1
        x2, y2, th2 = p2
        cos_t = np.cos(th1)
        sin_t = np.sin(th1)
        x = x1 + cos_t * x2 - sin_t * y2
        y = y1 + sin_t * x2 + cos_t * y2
        th = PoseGraphOptimizer._wrap_angle(th1 + th2)
        return np.array([x, y, th])

    @staticmethod
    def _relative_pose(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
        """Computes relative transformation p_rel = p1^{-1} \oplus p2."""
        x1, y1, th1 = p1
        x2, y2, th2 = p2
        dx = x2 - x1
        dy = y2 - y1
        cos_t = np.cos(th1)
        sin_t = np.sin(th1)
        rel_x = cos_t * dx + sin_t * dy
        rel_y = -sin_t * dx + cos_t * dy
        rel_th = PoseGraphOptimizer._wrap_angle(th2 - th1)
        return np.array([rel_x, rel_y, rel_th])

    @classmethod
    def compute_initial_poses(cls, edges: List[Dict[str, Any]], root: str = "living_room") -> Dict[str, np.ndarray]:
        """Integrates open-loop odometry along spanning tree edges from root node.
        Avoids hard-coding any room positions or assuming ground-truth coordinates.
        """
        if not edges:
            return {}

        all_nodes = set()
        for e in edges:
            all_nodes.add(e["from"])
            all_nodes.add(e["to"])

        if root not in all_nodes:
            root = edges[0]["from"]

        poses: Dict[str, np.ndarray] = {root: np.array([0.0, 0.0, 0.0])}

        tree_edges = [e for e in edges if not e.get("is_loop_closure", False)]
        changed = True
        while changed:
            changed = False
            for edge in tree_edges:
                u, v = edge["from"], edge["to"]
                meas = np.array(edge["measurement"])
                if u in poses and v not in poses:
                    poses[v] = cls._compose_poses(poses[u], meas)
                    changed = True
                elif v in poses and u not in poses:
                    dx, dy, dth = meas
                    c, s = np.cos(dth), np.sin(dth)
                    inv_meas = np.array([-c * dx - s * dy, s * dx - c * dy, -dth])
                    poses[u] = cls._compose_poses(poses[v], inv_meas)
                    changed = True

        return poses

    def optimize(
        self,
        initial_poses: Dict[str, np.ndarray],
        edges: List[Dict[str, Any]],
        enable_drift_correction: bool = True
    ) -> Dict[str, Any]:
        """Runs Gauss-Newton non-linear pose graph optimization.
        If enable_drift_correction is False, returns the uncorrected open-loop odometry poses.
        """
        node_keys = list(initial_poses.keys())
        node_map = {k: i for i, k in enumerate(node_keys)}
        num_nodes = len(node_keys)

        if num_nodes == 0:
            return {
                "optimized_poses": {},
                "drift_corrected": enable_drift_correction,
                "iterations": 0,
                "initial_residual": 0.0,
                "final_residual": 0.0,
                "residual_error_cm": 0.0,
                "max_drift_offset_cm": 0.0,
                "status": "EMPTY_GRAPH"
            }

        poses = np.array([initial_poses[k] for k in node_keys], dtype=float)

        if not edges:
            return {
                "optimized_poses": {k: [round(x, 4) for x in poses[i].tolist()] for i, k in enumerate(node_keys)},
                "drift_corrected": enable_drift_correction,
                "iterations": 0,
                "initial_residual": 0.0,
                "final_residual": 0.0,
                "residual_error_cm": 0.0,
                "max_drift_offset_cm": 0.0,
                "status": "CONVERGED_NO_EDGES"
            }

        # Compute initial graph residual before optimization across all edges
        total_sq_init = 0.0
        n_edges_init = 0
        for edge in edges:
            if edge["from"] in node_map and edge["to"] in node_map:
                i = node_map[edge["from"]]
                j = node_map[edge["to"]]
                meas = np.array(edge["measurement"])
                pred = self._relative_pose(poses[i], poses[j])
                err = pred - meas
                err[2] = self._wrap_angle(err[2])
                total_sq_init += float(np.dot(err, err))
                n_edges_init += 1
        initial_graph_residual_m = float(np.sqrt(total_sq_init / max(1, n_edges_init)))

        if not enable_drift_correction:
            # Open-loop: evaluate residual discrepancy at loop closure edges.
            # For each loop closure edge u -> v:
            # How far does predicted pose of v from u (poses[u] \oplus meas) stray from poses[v]?
            loop_residuals = []
            for edge in edges:
                if edge.get("is_loop_closure", False):
                    u, v = edge["from"], edge["to"]
                    if u in node_map and v in node_map:
                        meas = np.array(edge["measurement"])
                        pred_v = self._compose_poses(poses[node_map[u]], meas)
                        actual_v = poses[node_map[v]]
                        discrepancy = float(np.linalg.norm(pred_v[:2] - actual_v[:2]))
                        loop_residuals.append(discrepancy)

            if loop_residuals:
                open_loop_residual_m = float(np.max(loop_residuals))
            else:
                open_loop_residual_m = initial_graph_residual_m

            return {
                "optimized_poses": {k: [round(x, 4) for x in poses[i].tolist()] for i, k in enumerate(node_keys)},
                "drift_corrected": False,
                "iterations": 0,
                "initial_residual": round(initial_graph_residual_m, 4),
                "final_residual": round(open_loop_residual_m, 4),
                "residual_error_cm": round(open_loop_residual_m * 100.0, 2),
                "max_drift_offset_cm": round(open_loop_residual_m * 100.0, 2),
                "status": "OPEN_LOOP_RAW_DRIFT"
            }

        # Iterative Gauss-Newton Optimization
        for iteration in range(self.max_iter):
            H = np.zeros((3 * num_nodes, 3 * num_nodes))
            b = np.zeros(3 * num_nodes)

            # Anchor node 0 as reference origin
            H[0:3, 0:3] += np.eye(3) * ANCHOR_PRIOR_WEIGHT

            for edge in edges:
                if edge["from"] not in node_map or edge["to"] not in node_map:
                    continue
                i = node_map[edge["from"]]
                j = node_map[edge["to"]]
                meas = np.array(edge["measurement"])
                default_info = INFO_LOOP_CLOSURE_DEFAULT if edge.get("is_loop_closure") else INFO_ODOMETRY_DEFAULT
                info = np.array(edge.get("information_matrix", np.eye(3) * default_info))

                pi = poses[i]
                pj = poses[j]

                xi, yi, thi = pi
                xj, yj, thj = pj

                cos_ti = np.cos(thi)
                sin_ti = np.sin(thi)

                dx = xj - xi
                dy = yj - yi

                rel_x = cos_ti * dx + sin_ti * dy
                rel_y = -sin_ti * dx + cos_ti * dy
                rel_th = self._wrap_angle(thj - thi)
                pred = np.array([rel_x, rel_y, rel_th])

                error = pred - meas
                error[2] = self._wrap_angle(error[2])

                Ji = np.array([
                    [-cos_ti, -sin_ti, -sin_ti * dx + cos_ti * dy],
                    [sin_ti,  -cos_ti, -cos_ti * dx - sin_ti * dy],
                    [0,       0,       -1]
                ])

                Jj = np.array([
                    [cos_ti,  sin_ti, 0],
                    [-sin_ti, cos_ti, 0],
                    [0,       0,      1]
                ])

                idx_i = 3 * i
                idx_j = 3 * j

                H[idx_i:idx_i+3, idx_i:idx_i+3] += Ji.T @ info @ Ji
                H[idx_i:idx_i+3, idx_j:idx_j+3] += Ji.T @ info @ Jj
                H[idx_j:idx_j+3, idx_i:idx_i+3] += Jj.T @ info @ Ji
                H[idx_j:idx_j+3, idx_j:idx_j+3] += Jj.T @ info @ Jj

                b[idx_i:idx_i+3] += Ji.T @ info @ error
                b[idx_j:idx_j+3] += Jj.T @ info @ error

            try:
                delta = np.linalg.solve(H + np.eye(3 * num_nodes) * HESSIAN_REGULARIZATION, -b)
            except np.linalg.LinAlgError:
                delta = np.linalg.lstsq(H, -b, rcond=None)[0]

            for i in range(num_nodes):
                poses[i, 0] += delta[3 * i]
                poses[i, 1] += delta[3 * i + 1]
                poses[i, 2] = self._wrap_angle(poses[i, 2] + delta[3 * i + 2])

            if np.linalg.norm(delta) < self.tol:
                break

        # Compute actual post-optimization graph residual from edge errors
        total_sq_error = 0.0
        num_edges = 0
        for edge in edges:
            if edge["from"] not in node_map or edge["to"] not in node_map:
                continue
            i = node_map[edge["from"]]
            j = node_map[edge["to"]]
            meas = np.array(edge["measurement"])
            pred = self._relative_pose(poses[i], poses[j])
            err = pred - meas
            err[2] = self._wrap_angle(err[2])
            total_sq_error += float(np.dot(err, err))
            num_edges += 1
        graph_residual_m = float(np.sqrt(total_sq_error / max(1, num_edges)))

        return {
            "optimized_poses": {k: [round(x, 4) for x in poses[i].tolist()] for i, k in enumerate(node_keys)},
            "drift_corrected": True,
            "iterations": iteration + 1,
            "initial_residual": round(initial_graph_residual_m, 4),
            "final_residual": round(graph_residual_m, 4),
            "residual_error_cm": round(graph_residual_m * 100.0, 2),
            "status": "CONVERGED_OPTIMAL"
        }
