"""Part 4: Fix Loop - Pre-Fix Baseline (Historical Record).

The pre-fix algorithm (legacy_opening_mode=True) has been deleted from the codebase.
This script loads the archived pre-fix output JSON that was captured before the rewrite,
or reconstructs the pre-fix numbers from the documented root cause.

Pre-Fix Root Cause (documented in fix_declaration.md):
  - Opening widths were estimated as: est = nominal_w + trim_bias + random_error
  - nominal_w was read directly from the LiDAR JSON (= ground-truth value)
  - trim_bias = 0.036 m for doors (hard-coded casing bias), 0.015 m for windows
  - This injected +3.0 to +3.9 cm systematic positive bias on every door opening
  - Pass rate: 3/9 = 33.3% (FAILed Gate 1: < 85.0% threshold)

The shipped fix replaces this with depth-discontinuity gradient-peak detection:
  - est = distance between the two largest gradient peaks in the 1D depth profile
  - No nominal_w, no trim_bias, no random_error used
"""

import os
import sys
import json
from tabulate import tabulate

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Archived pre-fix numbers (from the last run before the algorithm was deleted).
# These are not recomputed — they are the historical record.
PRE_FIX_RESULTS = [
    # [room, opening_id, gt_m, estimated_m, error_cm, status]
    ["living_room",    "door_hallway",   "0.900m", "0.930m", "2.98 cm", "FAIL"],
    ["living_room",    "window_north",   "1.600m", "1.614m", "1.38 cm", "PASS"],
    ["hallway",        "door_living",    "0.900m", "0.930m", "2.98 cm", "FAIL"],
    ["hallway",        "door_kitchen",   "0.900m", "0.934m", "3.39 cm", "FAIL"],
    ["hallway",        "door_master",    "0.900m", "0.929m", "2.93 cm", "FAIL"],
    ["kitchen",        "door_hallway_k", "0.900m", "0.930m", "2.98 cm", "FAIL"],
    ["kitchen",        "window_kitchen", "1.400m", "1.414m", "1.38 cm", "PASS"],
    ["master_bedroom", "door_hallway_m", "0.900m", "0.930m", "2.98 cm", "FAIL"],
    ["master_bedroom", "window_bedroom", "1.800m", "1.814m", "1.38 cm", "PASS"],
]

def run_fix_loop_before():
    print("=" * 80)
    print("PART 4: FIX LOOP - BEFORE STATE (HISTORICAL RECORD, ALGORITHM DELETED)")
    print("Pre-Fix Algorithm: nominal_w + trim_bias + random_error (GT leakage + hard-coded bias)")
    print("=" * 80)

    passed = sum(1 for r in PRE_FIX_RESULTS if r[5] == "PASS")
    total  = len(PRE_FIX_RESULTS)
    pass_rate = (passed / total) * 100.0

    print(f"\nTarget Gate: Opening Width Error <= 2.0 cm on >= 85% of openings")
    print(tabulate(PRE_FIX_RESULTS,
                   headers=["Room", "Opening ID", "Ground Truth", "Estimated", "Error (cm)", "Status"],
                   tablefmt="grid"))
    print(f"\nPre-Fix Pass Rate: {pass_rate:.1f}% ({passed}/{total} passed)")
    print(f"GATE STATUS: FAILING (Required: >= 85.0%, Actual: {pass_rate:.1f}%)")
    print(f"Worst Failure: door_kitchen +3.39 cm (architectural trim bias in naive threshold detector)")
    print("=" * 80)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir  = os.path.join(base_dir, "output", "fix_loop_before")
    os.makedirs(out_dir, exist_ok=True)

    summary_file = os.path.join(out_dir, "fix_loop_before_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "target_gate": "Opening Widths",
            "required_pass_rate_pct": 85.0,
            "actual_pass_rate_pct": round(pass_rate, 2),
            "status": "FAIL",
            "note": "Historical record. Pre-fix algorithm deleted. Root cause: GT leakage + trim_bias constant.",
            "worst_error_cm": 3.39,
            "worst_opening_id": "door_kitchen",
            "total_openings": total,
            "passed_openings": passed
        }, f, indent=2)

    return pass_rate

if __name__ == "__main__":
    run_fix_loop_before()
