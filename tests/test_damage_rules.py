"""Unit tests for damage segmentation, concealed rules engine, and repair scoping."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.damage.damage_segmenter import DamageSegmenter
from pipeline.damage.concealed_rules import ConcealedDamageEngine
from pipeline.damage.scope_generator import ScopeOfWorkGenerator

class TestDamageAssessment(unittest.TestCase):
    def setUp(self):
        self.seg = DamageSegmenter()
        self.rules = ConcealedDamageEngine()
        self.scope = ScopeOfWorkGenerator()

    def test_damage_and_concealed_rules(self):
        obs = [
            {"surface_id": "wall_north", "class": "water_damage", "nominal_extent_m2": 2.4, "surface_type": "drywall_wall"},
            {"surface_id": "ceiling", "class": "water_damage", "nominal_extent_m2": 1.2, "surface_type": "drywall_ceiling"}
        ]
        regions = self.seg.segment_damage("living_room", obs, tier="lidar")
        self.assertEqual(len(regions), 2)

        flags = self.rules.evaluate_flags(regions, {})
        self.assertGreaterEqual(len(flags), 2)
        fired_rules = [f["rule_fired"] for f in flags]
        self.assertIn("RULE_WATER_BEHIND_BASEBOARD", fired_rules)
        self.assertIn("RULE_CEILING_PLUMBING_LEAK", fired_rules)

        scope = self.scope.generate_scope(regions)
        self.assertGreater(len(scope), 0)
        self.assertGreater(sum(s["total_cost_usd"] for s in scope), 0)

if __name__ == "__main__":
    unittest.main()
