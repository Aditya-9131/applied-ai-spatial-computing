"""Calibration script: derive empirical 95% CI half-widths from simulated captures.

Protocol:
  1. Generate N_CAL calibration captures (different RNG seeds) → fit 95th-percentile |error|
     per measurement type (wall_length, ceiling_height, opening_width).
  2. Generate N_HELD held-out captures (different seeds) → report empirical CI coverage
     using the bounds derived in step 1.
  3. Write derived bounds to pipeline/calibration/empirical_bounds.json.
     SensorErrorModel loads this file at runtime; hard-coded tier specs are removed.

Run this script whenever the sensor model or room geometry changes.
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.generate_lidar_sim import (
    make_depth_profile_beam_footprint,
    make_room_point_cloud,
    OPENINGS_CFG, ROOM_DIMS, ROOM_OPENINGS_PC,
    NUM_SAMPLES, D_WALL, D_VOID,
)
from pipeline.geometry.opening_detector import OpeningDetector
from pipeline.geometry.plane_detector import PlaneDetector

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOUNDS_FILE = os.path.join(BASE_DIR, "pipeline", "calibration", "empirical_bounds.json")

N_CAL  = 80    # calibration captures per opening/room
N_HELD = 40    # held-out captures

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _run_opening_sim(wall_len, gt_w, offset, rng):
    profile, le, re, _, _ = make_depth_profile_beam_footprint(wall_len, gt_w, offset, rng)
    det = OpeningDetector()
    est_w, status = det._estimate_width_from_profile(profile, wall_len, "calib")
    return float(est_w), status

def _run_room_sim(room_id, seed):
    w_m, l_m, h_m = ROOM_DIMS[room_id]
    pc_rng = np.random.RandomState(seed)
    op_cfgs = ROOM_OPENINGS_PC.get(room_id, [])
    pts = make_room_point_cloud(w_m, l_m, h_m, op_cfgs, pc_rng)
    pts_arr = np.array(pts, dtype=np.float64)
    det = PlaneDetector()
    rw, rl, rh = det._estimate_room_dimensions_from_points(pts_arr, "lidar")
    # wall errors: north/south = width, east/west = length
    wall_errors = [abs(rw - w_m), abs(rl - l_m), abs(rw - w_m), abs(rl - l_m)]
    ceil_error  = abs(rh - h_m)
    return wall_errors, ceil_error, w_m, l_m

# ──────────────────────────────────────────────────────────────────────────────
# GATHER ERRORS
# ──────────────────────────────────────────────────────────────────────────────

def gather_errors(n_samples, seed_offset):
    opening_abs_errors  = []   # |est - gt| in metres
    wall_abs_errors     = []   # |est - gt| per wall in metres
    wall_pct_errors     = []   # |est - gt| / gt * 100
    ceiling_abs_errors  = []

    rng_master = np.random.RandomState(seed_offset)

    # Opening width errors
    for room_id, oid, wall_len, gt_w, offset in OPENINGS_CFG:
        for _ in range(n_samples):
            rng = np.random.RandomState(int(rng_master.randint(0, 2**31 - 1)))
            est_w, status = _run_opening_sim(wall_len, gt_w, offset, rng)
            opening_abs_errors.append(abs(est_w - gt_w))

    # Wall length + ceiling errors
    room_ids = list(ROOM_DIMS.keys())
    for room_id in room_ids:
        w_m, l_m, h_m = ROOM_DIMS[room_id]
        for _ in range(n_samples):
            seed = int(rng_master.randint(0, 2**31 - 1))
            wall_errs, ceil_err, gt_w, gt_l = _run_room_sim(room_id, seed)
            for i, we in enumerate(wall_errs):
                gt_dim = gt_w if i % 2 == 0 else gt_l
                wall_abs_errors.append(we)
                wall_pct_errors.append((we / gt_dim) * 100.0)
            ceiling_abs_errors.append(ceil_err)

    return (
        np.array(opening_abs_errors),
        np.array(wall_abs_errors),
        np.array(wall_pct_errors),
        np.array(ceiling_abs_errors),
    )

# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def run():
    print("=" * 70)
    print("EMPIRICAL CALIBRATION: LiDAR Tier CI Derivation")
    print(f"  Calibration set: {N_CAL} captures per opening/room")
    print(f"  Held-out set:    {N_HELD} captures per opening/room")
    print("=" * 70)

    # CALIBRATION set (seeds 1000–1999)
    print("\n[1/3] Gathering calibration errors ...")
    cal_open, cal_wall, cal_wall_pct, cal_ceil = gather_errors(N_CAL, seed_offset=1000)

    # Derive 95th-percentile CI half-widths
    opening_ci_m   = float(np.percentile(cal_open,    95))
    ceiling_ci_m   = float(np.percentile(cal_ceil,    95))
    wall_ci_m      = float(np.percentile(cal_wall,    95))
    wall_ci_pct    = float(np.percentile(cal_wall_pct, 95))

    print(f"\nCalibration-derived 95th-percentile half-widths (lidar tier):")
    print(f"  Opening width CI:   ±{opening_ci_m*100:.2f} cm")
    print(f"  Ceiling height CI:  ±{ceiling_ci_m*100:.2f} cm")
    print(f"  Wall length CI abs: ±{wall_ci_m*100:.2f} cm")
    print(f"  Wall length CI pct: ±{wall_ci_pct:.3f}%")

    # HELD-OUT set (seeds 5000–5999) — different from calibration
    print("\n[2/3] Gathering held-out errors ...")
    held_open, held_wall, held_wall_pct, held_ceil = gather_errors(N_HELD, seed_offset=5000)

    # Empirical coverage on held-out set
    def coverage(errors, half_width):
        return float(np.mean(errors <= half_width)) * 100.0

    open_cov   = coverage(held_open,    opening_ci_m)
    ceil_cov   = coverage(held_ceil,    ceiling_ci_m)
    wall_cov   = coverage(held_wall,    wall_ci_m)

    print(f"\nHeld-out empirical 95% CI coverage (using calibration-derived bounds):")
    print(f"  Opening width:  {open_cov:.1f}%  (N={len(held_open)})")
    print(f"  Ceiling height: {ceil_cov:.1f}%  (N={len(held_ceil)})")
    print(f"  Wall length:    {wall_cov:.1f}%  (N={len(held_wall)})")

    # Statistics for disclosure
    bounds = {
        "tier": "lidar",
        "derivation": "empirical_95th_percentile_of_absolute_error",
        "calibration_n_per_opening": N_CAL,
        "calibration_n_per_room": N_CAL,
        "held_out_n_per_opening": N_HELD,
        "held_out_n_per_room": N_HELD,
        "calibration_seed_offset": 1000,
        "held_out_seed_offset": 5000,
        "model": "beam_footprint_blend + synthetic_point_cloud",
        "calibration_stats": {
            "opening_width_abs_ci_m": round(opening_ci_m, 5),
            "ceiling_height_abs_ci_m": round(ceiling_ci_m, 5),
            "wall_length_abs_ci_m": round(wall_ci_m, 5),
            "wall_length_pct_ci": round(wall_ci_pct, 4),
            "opening_width_mean_abs_error_m": round(float(np.mean(cal_open)), 5),
            "ceiling_mean_abs_error_m": round(float(np.mean(cal_ceil)), 5),
            "wall_mean_abs_error_m": round(float(np.mean(cal_wall)), 5),
        },
        "held_out_empirical_coverage_pct": {
            "opening_width":   round(open_cov, 1),
            "ceiling_height":  round(ceil_cov, 1),
            "wall_length":     round(wall_cov, 1),
        },
        "note": (
            "SIMULATED: bounds derived from synthetic beam-footprint + point-cloud model, "
            "not from real device measurements. Use as an ordered lower bound only."
        )
    }

    os.makedirs(os.path.dirname(BOUNDS_FILE), exist_ok=True)
    with open(BOUNDS_FILE, "w", encoding="utf-8") as f:
        json.dump(bounds, f, indent=2)
    print(f"\n[3/3] Wrote empirical bounds -> {BOUNDS_FILE}")
    print("\nNOTE: Photo/Video tiers remain NOT IMPLEMENTED; their CI bounds are excluded.")

    return bounds

if __name__ == "__main__":
    run()
