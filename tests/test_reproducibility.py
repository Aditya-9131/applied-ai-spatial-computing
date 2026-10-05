"""Unit tests for contract schema compliance and calibration confidence intervals."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.io.schema import create_output_contract, validate_contract
from pipeline.calibration.error_model import SensorErrorModel

class TestReproducibilityAndCalibration(unittest.TestCase):
    def test_sensor_error_model(self):
        lidar_w = SensorErrorModel.apply_measurement_ci(4.0, "wall_length", "lidar")
        video_w = SensorErrorModel.apply_measurement_ci(4.0, "wall_length", "video")
        photo_w = SensorErrorModel.apply_measurement_ci(4.0, "wall_length", "photos")

        # Verify honest widening of intervals
        lidar_span = lidar_w["ci_95"][1] - lidar_w["ci_95"][0]
        video_span = video_w["ci_95"][1] - video_w["ci_95"][0]
        photo_span = photo_w["ci_95"][1] - photo_w["ci_95"][0]

        self.assertLess(lidar_span, video_span)
        self.assertLess(video_span, photo_span)

    def test_schema_validator(self):
        contract = create_output_contract(
            property_id="TEST_001",
            tier="lidar",
            device_model="iPhone 15 Pro",
            rooms=[{
                "room_id": "r1", "name": "Room 1",
                "ceiling_height": {"value": 2.7, "ci_95": [2.68, 2.72]},
                "floor_area": {"value": 20.0, "ci_95": [19.8, 20.2]},
                "walls": [], "openings": []
            }],
            stitched_plan={},
            damage_assessment={},
            concealed_flags=[],
            scope_of_work=[],
            calibration_metrics={}
        )
        self.assertTrue(validate_contract(contract))

if __name__ == "__main__":
    unittest.main()
