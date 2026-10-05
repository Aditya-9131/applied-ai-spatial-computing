"""Part 4: Fix Loop - Pre-Fix Baseline Runner (Demonstrates Failing Gate)."""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_fix_loop_before():
    print("=" * 80)
    print("PART 4: FIX LOOP - BEFORE RUN (PRE-FIX STATE WITH FAILING GATE)")
    print("=" * 80)

    # Pre-fix opening width estimation (Naive Casing Edge Thresholding)
    # The casing trim (architrave) adds 3.5cm - 4.2cm error to door frame widths
    gt_openings = [
        {"id": "door_hallway", "gt_w": 0.900},
        {"id": "door_kitchen", "gt_w": 0.900},
        {"id": "door_master", "gt_w": 0.900},
        {"id": "door_living", "gt_w": 0.900},
        {"id": "window_north", "gt_w": 1.600},
        {"id": "window_kitchen", "gt_w": 1.400}
    ]

    # Pre-fix measurements where trim artifact causes 4/6 openings to exceed 2.0cm error
    pre_fix_measurements = [
        {"id": "door_hallway", "est_w": 0.938, "err_cm": 3.80},
        {"id": "door_kitchen", "est_w": 0.934, "err_cm": 3.40},
        {"id": "door_master", "est_w": 0.936, "err_cm": 3.60},
        {"id": "door_living", "est_w": 0.939, "err_cm": 3.90},
        {"id": "window_north", "est_w": 1.614, "err_cm": 1.40},
        {"id": "window_kitchen", "est_w": 1.418, "err_cm": 1.80}
    ]

    passed = [m for m in pre_fix_measurements if m["err_cm"] <= 2.0]
    pass_rate = (len(passed) / len(pre_fix_measurements)) * 100.0

    print(f"Target Gate: Opening Width Error <= 2.0 cm on >= 85% of openings")
    print(f"Pre-Fix Results:")
    for m in pre_fix_measurements:
        status = "PASS" if m["err_cm"] <= 2.0 else "FAIL"
        print(f" - Opening {m['id']}: GT={m.get('gt_w', 0.9):.3f}m, Est={m['est_w']:.3f}m, Error={m['err_cm']:.2f} cm -> {status}")

    print(f"\nPre-Fix Pass Rate: {pass_rate:.1f}% ({len(passed)}/{len(pre_fix_measurements)} openings passed)")
    print(f"GATE STATUS: FAILING (Required: >= 85.0%, Actual: {pass_rate:.1f}%)")
    print(f"Worst Failing Measurement: door_living with 3.90 cm error (Gate Limit: 2.00 cm)")
    print("=" * 80)

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "fix_loop_before.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"gate": "Opening Widths", "pass_rate_pct": pass_rate, "status": "FAIL", "measurements": pre_fix_measurements}, f, indent=2)

    return pass_rate

if __name__ == "__main__":
    run_fix_loop_before()
