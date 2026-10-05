"""Unit tests for RANSAC plane fitting and geometry reconstruction."""

import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.geometry.plane_detector import PlaneDetector

class TestPlaneDetector(unittest.TestCase):
    def setUp(self):
        self.detector = PlaneDetector()

    def test_fit_plane_ransac(self):
        # Generate 100 points on plane z = 2.5 + noise
        x = np.random.uniform(0, 5, 100)
        y = np.random.uniform(0, 5, 100)
        z = np.ones(100) * 2.5 + np.random.normal(0, 0.005, 100)
        pts = np.column_stack([x, y, z])

        plane, inliers = self.detector.fit_plane_ransac(pts)
        self.assertGreater(len(inliers), 80)
        # Normal should be close to [0, 0, 1]
        self.assertAlmostEqual(abs(plane[2]), 1.0, delta=0.05)

    def test_reconstruct_room_geometry(self):
        nominal = {"width": 4.0, "length": 5.0, "height": 2.6}
        geom = self.detector.reconstruct_room_geometry(np.zeros((10, 3)), nominal, tier="lidar")

        self.assertIn("walls", geom)
        self.assertEqual(len(geom["walls"]), 4)
        self.assertAlmostEqual(geom["ceiling_height_m"], 2.6, delta=0.03)
        self.assertAlmostEqual(geom["floor_area_m2"], 20.0, delta=0.5)

if __name__ == "__main__":
    unittest.main()
