"""Unit tests for opening detection and confidence intervals."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.geometry.opening_detector import OpeningDetector

class TestOpeningDetector(unittest.TestCase):
    def setUp(self):
        self.detector = OpeningDetector()

    def test_detect_openings(self):
        walls = [{"wall_id": "wall_south", "length_m": 4.8}]
        sensor_slices = {
            "openings": [
                {"wall_id": "wall_south", "width": 0.90, "height": 2.05, "type": "door"}
            ]
        }
        openings = self.detector.detect_openings(walls, sensor_slices, tier="lidar")
        self.assertEqual(len(openings), 1)
        op = openings[0]
        self.assertEqual(op["type"], "door")
        self.assertAlmostEqual(op["width_m"]["value"], 0.90, delta=0.03)
        self.assertAlmostEqual(op["height_m"]["value"], 2.05, delta=0.03)
        self.assertGreater(op["confidence"], 0.90)

if __name__ == "__main__":
    unittest.main()
