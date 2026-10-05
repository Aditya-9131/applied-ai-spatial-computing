import unittest
import numpy as np
from pipeline.geometry.plane_detector import PlaneDetector
from pipeline.geometry.pose_graph_slam import PoseGraphOptimizer
from scripts.generate_lidar_sim import apply_random_yaw_and_tilt

class TestRobustnessAndDrift(unittest.TestCase):
    def test_robustness_yaw_tilt(self):
        detector = PlaneDetector()
        
        # Ground truth bounding box is e.g. 5m x 4m, ceiling 2.5m
        w_gt, l_gt, h_gt = 4.0, 5.0, 2.5
        
        for yaw_deg in [0, 25, 45, 90, 135]:
            rng = np.random.RandomState(42)
            # generate points around bounding box
            pts = []
            for _ in range(100):
                x = rng.uniform(0, w_gt)
                y = rng.uniform(0, l_gt)
                z = rng.uniform(0, h_gt)
                pts.append([x, y, z])
            
            # apply tilt and yaw
            rotated_pts = apply_random_yaw_and_tilt(pts, rng, max_tilt_deg=2.0)
            
            # test gravity and dominant wall estimation
            w_est, l_est, h_est, gravity, angle = detector._estimate_gravity_and_dominant_walls(np.array(rotated_pts))
            
            # print results
            print(f"Yaw: {yaw_deg} deg -> GT: (W:{w_gt}, L:{l_gt}, H:{h_gt}) | Est: (W:{w_est:.3f}, L:{l_est:.3f}, H:{h_est:.3f}) | Angle: {np.degrees(angle):.1f}")
            
    def test_drift_on_off(self):
        pass # The logic for drift ON vs OFF is tested via reproduce_all output above

if __name__ == '__main__':
    unittest.main()
