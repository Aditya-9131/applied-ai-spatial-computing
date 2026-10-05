"""Part 4: Fix Loop - AFTER state runner.

Runs the current (post-fix) pipeline code and evaluates Gate 1 (opening widths).
Numbers come from live pipeline output, not stored constants.
"""

import os
import sys
import json
from tabulate import tabulate

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_pipeline import run_spatial_pipeline

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH_DIR = os.path.join(BASE_DIR, "benchmark_data")
GT_FILE   = os.path.join(BENCH_DIR, "ground_truth", "ground_truth_master.json")


def run_fix_loop_after():
    print("=" * 80)
    print("PART 4: FIX LOOP — AFTER (current code: sub-pixel threshold crossing)")
    print("Algorithm: linear interpolation at depth-crossing threshold (no GT, no bias)")
    print("=" * 80)

    lidar_input = os.path.join(BENCH_DIR, "tier3_lidar", "multi_room_lidar.json")
    out_dir     = os.path.join(BASE_DIR, "output", "fix_loop_after")

    pipeline_out = run_spatial_pipeline(
        input_path=lidar_input,
        tier="lidar",
        output_dir=out_dir,
    )

    with open(GT_FILE, "r", encoding="utf-8") as f:
        gt = json.load(f)

    total_openings  = 0
    passed_openings = 0
    opening_rows    = []
    max_error_cm    = 0.0

    for r in pipeline_out["rooms"]:
        rid = r["room_id"]
        gt_openings  = gt["rooms"][rid]["openings"]
        est_openings = r["openings"]

        for g_op in gt_openings:
            total_openings += 1
            match = next(
                (e for e in est_openings if e["opening_id"] == g_op["opening_id"]), None
            )
            if match:
                est_w  = match["width_m"]["value"]
                gt_w   = g_op["width_m"]
                err_cm = abs(est_w - gt_w) * 100.0
                passed = err_cm <= 2.0
                if passed:
                    passed_openings += 1
                if err_cm > max_error_cm:
                    max_error_cm = err_cm
                opening_rows.append([
                    rid, g_op["opening_id"],
                    f"{gt_w:.3f}m", f"{est_w:.4f}m",
                    f"{err_cm:.2f} cm",
                    "PASS" if passed else "FAIL",
                ])
            else:
                opening_rows.append([
                    rid, g_op["opening_id"],
                    f"{g_op['width_m']:.3f}m", "MISSED", "N/A", "FAIL (MISSED)",
                ])

    pass_rate = (passed_openings / total_openings) * 100.0
    gate_ok   = pass_rate >= 85.0

    print(f"\n[AFTER] Gate: Opening Width Error <= 2.0 cm on >= 85.0% of openings")
    print(tabulate(
        opening_rows,
        headers=["Room", "Opening ID", "Ground Truth", "Estimated", "Error (cm)", "Status"],
        tablefmt="grid",
    ))
    print(f"\n[AFTER] Pass Rate: {pass_rate:.1f}% ({passed_openings}/{total_openings})")
    print(f"[AFTER] Max Error: {max_error_cm:.2f} cm")
    print(f"[AFTER] GATE STATUS: {'PASS' if gate_ok else 'FAIL'}")
    print("=" * 80)

    # Save summary JSON
    summary_file = os.path.join(out_dir, "fix_loop_after_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "target_gate": "Opening Widths",
            "algorithm": "SUBPIXEL_THRESHOLD_CROSSING",
            "required_pass_rate_pct": 85.0,
            "actual_pass_rate_pct": round(pass_rate, 2),
            "status": "PASS" if gate_ok else "FAIL",
            "max_error_cm": round(max_error_cm, 2),
            "total_openings": total_openings,
            "passed_openings": passed_openings,
        }, f, indent=2)

    return pass_rate


if __name__ == "__main__":
    run_fix_loop_after()
