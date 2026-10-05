"""Part 4: Fix Loop - BEFORE state runner.

Checks out the 'before-fix' git tag into a temporary worktree, runs the pipeline
from that snapshot, and evaluates Gate 1 (opening widths).

No stored constants. Numbers come from the live 'before-fix' code.
Requires git >= 2.5 (git worktree support).
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from tabulate import tabulate

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH_DIR  = os.path.join(BASE_DIR, "benchmark_data")
GT_FILE    = os.path.join(BENCH_DIR, "ground_truth", "ground_truth_master.json")
LIDAR_INPUT = os.path.join(BENCH_DIR, "tier3_lidar", "multi_room_lidar.json")
PYTHON     = sys.executable


def run_fix_loop_before():
    print("=" * 80)
    print("PART 4: FIX LOOP — BEFORE (tag: before-fix, via git worktree)")
    print("Algorithm: integer gradient-peak indexing (has +1 px systematic bias)")
    print("=" * 80)

    # ── 1. Create a temporary worktree at the before-fix tag ─────────────────
    worktree_dir = tempfile.mkdtemp(prefix="before_fix_worktree_")
    out_dir      = os.path.join(BASE_DIR, "output", "fix_loop_before")
    os.makedirs(out_dir, exist_ok=True)

    try:
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", worktree_dir, "before-fix"],
            cwd=BASE_DIR, capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"ERROR creating worktree: {result.stderr}")
            return None

        print(f"[worktree] Checked out 'before-fix' into {worktree_dir}")

        # The worktree needs the benchmark data (not versioned separately, symlink)
        # Copy benchmark_data and output dir into worktree
        wt_bench = os.path.join(worktree_dir, "benchmark_data")
        if not os.path.exists(wt_bench):
            shutil.copytree(BENCH_DIR, wt_bench)

        wt_out = os.path.join(worktree_dir, "output", "fix_loop_before")
        os.makedirs(wt_out, exist_ok=True)

        # ── 2. Run the pipeline from the worktree ────────────────────────────
        wt_lidar_input = os.path.join(wt_bench, "tier3_lidar", "multi_room_lidar.json")
        cmd = [
            PYTHON, "run_pipeline.py",
            "--input", wt_lidar_input,
            "--tier", "lidar",
            "--output", wt_out,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=worktree_dir)
        if result.returncode != 0:
            print(f"ERROR running pipeline:\n{result.stderr}")
            return None

        print(result.stdout.strip())

        # ── 3. Load output and evaluate Gate 1 ──────────────────────────────
        plan_path = os.path.join(wt_out, "plan_output.json")
        with open(plan_path, "r", encoding="utf-8") as f:
            pipeline_out = json.load(f)
        with open(GT_FILE, "r", encoding="utf-8") as f:
            gt = json.load(f)

        # Copy the plan to the real output dir for later inspection
        shutil.copy(plan_path, os.path.join(out_dir, "plan_output.json"))

    finally:
        # ── 4. Remove the worktree ───────────────────────────────────────────
        subprocess.run(
            ["git", "worktree", "remove", "--force", worktree_dir],
            cwd=BASE_DIR, capture_output=True
        )
        shutil.rmtree(worktree_dir, ignore_errors=True)

    return _evaluate_gate1(pipeline_out, gt, label="BEFORE")


def _evaluate_gate1(pipeline_out, gt, label=""):
    total_openings = 0
    passed_openings = 0
    opening_rows = []
    max_error_cm = 0.0

    for r in pipeline_out["rooms"]:
        rid = r["room_id"]
        gt_openings = gt["rooms"][rid]["openings"]
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

    print(f"\n[{label}] Gate: Opening Width Error <= 2.0 cm on >= 85.0% of openings")
    print(tabulate(
        opening_rows,
        headers=["Room", "Opening ID", "Ground Truth", "Estimated", "Error (cm)", "Status"],
        tablefmt="grid",
    ))
    print(f"\n[{label}] Pass Rate: {pass_rate:.1f}% ({passed_openings}/{total_openings})")
    print(f"[{label}] Max Error: {max_error_cm:.2f} cm")
    print(f"[{label}] GATE STATUS: {'PASS' if gate_ok else 'FAIL'}")
    print("=" * 80)
    return pass_rate


if __name__ == "__main__":
    run_fix_loop_before()
