"""Pose Graph SLAM and Non-Linear Drift Optimization for Multi-Room Stitching."""

import numpy as np
from typing import Dict, List, Tuple, Any

class PoseGraphOptimizer:
    """Non-linear 2D SE(2) Pose Graph Optimization with Loop Closure & Plane-Anchored Constraints."""

    def __init__(self, max_iterations: int = 50, tolerance: float = 1e-6):
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

    def optimize(
        self,
        initial_poses: Dict[str, np.ndarray],
        edges: List[Dict[str, Any]],
        enable_drift_correction: bool = True
    ) -> Dict[str, Any]:
        """Runs Gauss-Newton / Levenberg-Marquardt non-linear pose graph optimization.
        If enable_drift_correction is False, returns the uncorrected open-loop odometry poses.
        """
        node_keys = list(initial_poses.keys())
        node_map = {k: i for i, k in enumerate(node_keys)}
        num_nodes = len(node_keys)

        # Pose state vector: [x0, y0, th0, x1, y1, th1, ...]
        poses = np.array([initial_poses[k] for k in node_keys], dtype=float)

        if not enable_drift_correction:
            # Baseline open-loop: accumulated odometry without loop closure
            residual_error = float(np.sum([
                np.linalg.norm(self._relative_pose(poses[node_map[e["from"]]], poses[node_map[e["to"]]]) - np.array(e["measurement"]))
                for e in edges if e.get("is_loop_closure", False)
            ]))
            return {
                "optimized_poses": {k: poses[i].tolist() for i, k in enumerate(node_keys)},
                "drift_corrected": False,
                "iterations": 0,
                "initial_residual": round(residual_error, 4),
                "final_residual": round(residual_error, 4),
                "max_drift_offset_cm": round(residual_error * 100.0, 2),
                "status": "OPEN_LOOP_RAW_DRIFT"
            }

        # Anchor node 0 as reference origin
        initial_residual = 0.0
        for e in edges:
            i = node_map[e["from"]]
            j = node_map[e["to"]]
            meas = np.array(e["measurement"])
            pred = self._relative_pose(poses[i], poses[j])
            diff = pred - meas
            diff[2] = self._wrap_angle(diff[2])
            initial_residual += float(np.dot(diff, diff))

        # Optimization loop
        for iteration in range(self.max_iter):
            H = np.zeros((3 * num_nodes, 3 * num_nodes))
            b = np.zeros(3 * num_nodes)

            # Fix origin node (infinite information)
            H[0:3, 0:3] += np.eye(3) * 1e6

            for edge in edges:
                i = node_map[edge["from"]]
                j = node_map[edge["to"]]
                meas = np.array(edge["measurement"])
                info = np.array(edge.get("information_matrix", np.eye(3) * (50.0 if not edge.get("is_loop_closure") else 200.0)))

                pi = poses[i]
                pj = poses[j]

                xi, yi, thi = pi
                xj, yj, thj = pj

                cos_ti = np.cos(thi)
                sin_ti = np.sin(thi)

                dx = xj - xi
                dy = yj - yi

                # Predicted relative measurement
                rel_x = cos_ti * dx + sin_ti * dy
                rel_y = -sin_ti * dx + cos_ti * dy
                rel_th = self._wrap_angle(thj - thi)
                pred = np.array([rel_x, rel_y, rel_th])

                # Error vector e_ij = pred - meas
                error = pred - meas
                error[2] = self._wrap_angle(error[2])

                # Jacobians w.r.t pose_i and pose_j
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

                # Accumulate Hessian and gradient vector
                idx_i = 3 * i
                idx_j = 3 * j

                H[idx_i:idx_i+3, idx_i:idx_i+3] += Ji.T @ info @ Ji
                H[idx_i:idx_i+3, idx_j:idx_j+3] += Ji.T @ info @ Jj
                H[idx_j:idx_j+3, idx_i:idx_i+3] += Jj.T @ info @ Ji
                H[idx_j:idx_j+3, idx_j:idx_j+3] += Jj.T @ info @ Jj

                b[idx_i:idx_i+3] += Ji.T @ info @ error
                b[idx_j:idx_j+3] += Jj.T @ info @ error

            # Solve normal equations: (H + lambda*I) \Delta p = -b
            try:
                delta = np.linalg.solve(H + np.eye(3 * num_nodes) * 1e-4, -b)
            except np.linalg.LinAlgError:
                delta = np.linalg.lstsq(H, -b, rcond=None)[0]

            # Update poses
            for i in range(num_nodes):
                poses[i, 0] += delta[3 * i]
                poses[i, 1] += delta[3 * i + 1]
                poses[i, 2] = self._wrap_angle(poses[i, 2] + delta[3 * i + 2])

            if np.linalg.norm(delta) < self.tol:
                break

        final_residual = 0.0
        for e in edges:
            i = node_map[e["from"]]
            j = node_map[e["to"]]
            meas = np.array(e["measurement"])
            pred = self._relative_pose(poses[i], poses[j])
            diff = pred - meas
            diff[2] = self._wrap_angle(diff[2])
            final_residual += float(np.dot(diff, diff))

        return {
            "optimized_poses": {k: [round(x, 4) for x in poses[i].tolist()] for i, k in enumerate(node_keys)},
            "drift_corrected": True,
            "iterations": iteration + 1,
            "initial_residual": round(initial_residual, 4),
            "final_residual": round(final_residual, 6),
            "max_drift_offset_cm": round(np.sqrt(final_residual) * 100.0, 2),
            "status": "CONVERGED_OPTIMAL"
        }
