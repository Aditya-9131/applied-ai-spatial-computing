"""Generate simulated LiDAR depth profiles for benchmark openings.

This script regenerates the depth_profile_m arrays in
benchmark_data/tier3_lidar/multi_room_lidar.json from a physical sensor model.

Physical model:
  - Wall surface returns at d_wall = 0.05 m (typical dToF wall return)
  - Opening void returns at d_void = 3.80 m (far-field, no surface behind)
  - Wall noise: sigma = 0.004 m  (4 mm -- Apple LiDAR dToF spec)
  - Void noise:  sigma = 0.050 m (50 mm -- noisier at range)
  - Sub-pixel boundary offset: uniform random fraction per opening so the
    opening edge does NOT coincide with an integer pixel boundary.
    This makes the ground-truth width incommensurate with the pixel grid,
    matching real-world sensor behaviour.

Ground truth (true physical widths) is stored ONLY in:
  benchmark_data/ground_truth/ground_truth_master.json
  benchmark_data/ground_truth/depth_profile_ground_truth.json  (generated here)

The JSON written to multi_room_lidar.json contains only sensor measurements.
Pipeline code (pipeline/) MUST NOT read ground_truth_master.json.

NOTE: The depth_profile_m arrays are SIMULATED from a parametric model,
not captured from a real device. See README.md for disclosure.
"""

import json
import os
import numpy as np

# ── Configuration ────────────────────────────────────────────────────────────
GLOBAL_SEED   = 42           # top-level RNG seed — set this, derive per-opening seeds
NUM_SAMPLES   = 200          # number of depth samples per wall scan
D_WALL        = 0.05         # metres — nominal wall return depth
D_VOID        = 3.80         # metres — nominal void return depth
NOISE_WALL    = 0.004        # metres sigma — dToF wall noise
NOISE_VOID    = 0.050        # metres sigma — dToF void (range) noise

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIDAR_FILE = os.path.join(BASE_DIR, "benchmark_data", "tier3_lidar", "multi_room_lidar.json")
GT_DIR     = os.path.join(BASE_DIR, "benchmark_data", "ground_truth")
GT_DEPTH_FILE = os.path.join(GT_DIR, "depth_profile_ground_truth.json")


def make_depth_profile(
    wall_length_m: float,
    opening_width_m: float,
    offset_m: float,
    rng: np.random.RandomState,
) -> tuple:
    """Generate one 1D depth profile from the physical sensor model.

    Uses a random sub-pixel boundary offset so the true opening edge is NOT
    aligned to an integer pixel boundary.  The ground-truth continuous boundary
    positions are returned separately and must not be embedded in the profile.

    Returns:
        profile      : list[float] -- rounded to 5 decimal places
        left_exact   : float       -- continuous left boundary (pixels)
        right_exact  : float       -- continuous right boundary (pixels)
        sub_px_left  : float       -- sub-pixel offset of left boundary [0, 1)
        sub_px_right : float       -- sub-pixel offset of right boundary [0, 1)
    """
    px_per_m = NUM_SAMPLES / wall_length_m

    # True continuous boundary positions (with random sub-pixel offsets)
    sub_px_left  = rng.uniform(0.0, 1.0)
    sub_px_right = rng.uniform(0.0, 1.0)

    left_exact  = offset_m * px_per_m + sub_px_left
    right_exact = (offset_m + opening_width_m) * px_per_m + sub_px_right

    # Integer pixel indices: a pixel is void if its centre falls inside [left_exact, right_exact]
    profile = np.full(NUM_SAMPLES, D_WALL) + rng.normal(0, NOISE_WALL, NUM_SAMPLES)
    for px in range(NUM_SAMPLES):
        px_centre = px + 0.5  # centre of pixel px
        if left_exact <= px_centre <= right_exact:
            profile[px] = D_VOID + rng.normal(0, NOISE_VOID)

    return (
        [round(float(v), 5) for v in profile],
        float(left_exact),
        float(right_exact),
        float(sub_px_left),
        float(sub_px_right),
    )


def run():
    np.random.seed(GLOBAL_SEED)
    rng_master = np.random.RandomState(GLOBAL_SEED)

    # Per-opening config: (room_id, opening_id, wall_length_m, gt_width_m, offset_m)
    # gt_width_m matches ground_truth_master.json exactly.
    # offset_m is the nominal position of the opening along the wall.
    openings_cfg = [
        # living_room
        ("living_room",    "door_hallway",   4.8, 0.900, 1.80),
        ("living_room",    "window_north",   4.8, 1.600, 1.60),
        # hallway
        ("hallway",        "door_living",    1.5, 0.900, 0.30),
        ("hallway",        "door_kitchen",   5.4, 0.900, 2.10),
        ("hallway",        "door_master",    1.5, 0.900, 0.30),
        # kitchen
        ("kitchen",        "door_hallway_k", 4.2, 0.900, 1.50),
        ("kitchen",        "window_kitchen", 3.6, 1.400, 1.10),
        # master_bedroom
        ("master_bedroom", "door_hallway_m", 4.2, 0.900, 1.65),
        ("master_bedroom", "window_bedroom", 4.8, 1.800, 1.50),
    ]

    # Build lookup: (room_id, opening_id) -> profile data
    profile_lookup = {}
    gt_depth_records = {}

    for room_id, oid, wall_len, gt_w, offset in openings_cfg:
        # Derive a per-opening seed deterministically from the master RNG
        opening_seed = int(rng_master.randint(0, 2**31 - 1))
        opening_rng  = np.random.RandomState(opening_seed)

        profile, left_exact, right_exact, sub_left, sub_right = make_depth_profile(
            wall_len, gt_w, offset, opening_rng
        )

        key = f"{room_id}/{oid}"
        profile_lookup[key] = {
            "wall_length_m": wall_len,
            "offset_m": offset,
            "depth_profile_m": profile,
        }

        # Ground-truth record (stored separately, never read by pipeline code)
        gt_depth_records[key] = {
            "room_id": room_id,
            "opening_id": oid,
            "gt_width_m": gt_w,
            "gt_offset_m": offset,
            "wall_length_m": wall_len,
            "left_boundary_px_continuous": left_exact,
            "right_boundary_px_continuous": right_exact,
            "sub_pixel_offset_left": sub_left,
            "sub_pixel_offset_right": sub_right,
            "seed": opening_seed,
        }

    # ── Inject profiles into LiDAR JSON ──────────────────────────────────────
    with open(LIDAR_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for room in data["rooms"]:
        rid = room["room_id"]
        for op in room.get("openings", []):
            oid = op["opening_id"]
            key = f"{rid}/{oid}"
            if key in profile_lookup:
                op.update(profile_lookup[key])
                # Explicitly do NOT embed width_m/height_m from the GT into the profile object.
                # The GT fields (width_m, height_m) that were already in the opening dict
                # remain for human-readability but the pipeline MUST NOT read them.

    with open(LIDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Updated {LIDAR_FILE} with {len(profile_lookup)} simulated depth profiles.")
    print(f"Physical model: d_wall={D_WALL}m, d_void={D_VOID}m, "
          f"noise_wall={NOISE_WALL}m, noise_void={NOISE_VOID}m")
    print(f"Sub-pixel boundary offsets: random uniform [0,1) per edge (from seed {GLOBAL_SEED})")

    # ── Write ground-truth depth records ─────────────────────────────────────
    os.makedirs(GT_DIR, exist_ok=True)
    with open(GT_DEPTH_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "description": (
                "Ground-truth continuous boundary positions for simulated depth profiles. "
                "MUST NOT be read by pipeline/ code. Only scripts/scoring code may use this."
            ),
            "global_seed": GLOBAL_SEED,
            "num_samples_per_profile": NUM_SAMPLES,
            "d_wall_m": D_WALL,
            "d_void_m": D_VOID,
            "noise_wall_sigma_m": NOISE_WALL,
            "noise_void_sigma_m": NOISE_VOID,
            "openings": gt_depth_records,
        }, f, indent=2)

    print(f"Ground-truth continuous boundaries saved to {GT_DEPTH_FILE}")
    print("\nNOTE: These profiles are SIMULATED from a parametric dToF sensor model.")
    print("      They are NOT from a real device capture. See README.md for disclosure.")


if __name__ == "__main__":
    run()
