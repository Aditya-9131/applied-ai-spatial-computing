"""Unit tests for Pose Graph SLAM and drift optimization."""

import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.geometry.pose_graph_slam import PoseGraphOptimizer

class TestPoseGraphSLAM(unittest.TestCase):
    def setUp(self):
        self.slam = PoseGraphOptimizer()

    def test_pose_graph_loop_closure(self):
        initial_poses = {
            "room_0": np.array([0.0, 0.0, 0.0]),
            "room_1": np.array([5.0, 0.2, 0.05]), # drifted pose
            "room_2": np.array([5.0, 4.2, 0.08]),
            "room_3": np.array([0.0, 4.3, 0.10])
        }
        edges = [
            {"from": "room_0", "to": "room_1", "measurement": [5.0, 0.0, 0.0], "is_loop_closure": False},
            {"from": "room_1", "to": "room_2", "measurement": [0.0, 4.0, 0.0], "is_loop_closure": False},
            {"from": "room_2", "to": "room_3", "measurement": [-5.0, 0.0, 0.0], "is_loop_closure": False},
            {"from": "room_3", "to": "room_0", "measurement": [0.0, -4.0, 0.0], "is_loop_closure": True}
        ]

        result = self.slam.optimize(initial_poses, edges, enable_drift_correction=True)
        self.assertEqual(result["status"], "CONVERGED_OPTIMAL")
        self.assertLess(result["final_residual"], 0.01)

        # Check raw drift ablation
        ablation = self.slam.optimize(initial_poses, edges, enable_drift_correction=False)
        self.assertEqual(ablation["status"], "OPEN_LOOP_RAW_DRIFT")
        self.assertGreater(ablation["max_drift_offset_cm"], 10.0)

if __name__ == "__main__":
    unittest.main()
