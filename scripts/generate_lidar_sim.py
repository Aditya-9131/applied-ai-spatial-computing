"""Generate physically modelled LiDAR depth profiles for benchmark openings.

Physical model:
  A dToF sensor emits a beam with a Gaussian footprint. At the jamb edge, the beam
  partially overlaps both the wall surface and the void. The measured depth is a
  weighted blend of wall return and void (no-return treated as far-field distance).

  Concretely, for each pixel p with centre at position p + 0.5:
    - Compute the overlap fraction f between the beam footprint [p, p+1] and the
      true opening [left_exact, right_exact]
    - depth[p] = (1-f)*d_wall + f*d_void + noise
  This means the depth CROSSES the midpoint threshold at the true physical boundary,
  allowing sub-pixel interpolation to recover the true width.

Ground truth (true continuous boundary positions) stored ONLY in:
  benchmark_data/ground_truth/depth_profile_ground_truth.json
Pipeline code must never read this file.

NOTE: These profiles are SIMULATED. See README.md for disclosure.
"""

import json
import os
import numpy as np

GLOBAL_SEED   = 42
NUM_SAMPLES   = 200
D_WALL        = 0.05   # metres -- nominal wall dToF return
D_VOID        = 3.80   # metres -- nominal void return
NOISE_WALL    = 0.004  # metres sigma -- Apple LiDAR wall noise
NOISE_VOID    = 0.050  # metres sigma -- far-range return noise

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIDAR_FILE    = os.path.join(BASE_DIR, "benchmark_data", "tier3_lidar", "multi_room_lidar.json")
GT_DIR        = os.path.join(BASE_DIR, "benchmark_data", "ground_truth")
GT_DEPTH_FILE = os.path.join(GT_DIR, "depth_profile_ground_truth.json")


def make_depth_profile_beam_footprint(
    wall_length_m: float,
    opening_width_m: float,
    offset_m: float,
    rng: np.random.RandomState,
) -> tuple:
    """Generate one beam-footprint-blended depth profile.

    Each pixel integrates depth over its footprint [p, p+1] pixels.
    The overlap fraction with the opening determines the blend between
    wall depth and void depth. This places the D_WALL/D_VOID midpoint
    crossing EXACTLY at the true physical boundary (left_exact / right_exact),
    enabling sub-pixel interpolation to recover the true width.

    Sub-pixel boundary offsets are drawn uniformly so the true edge is never
    aligned to an integer pixel -- this is the hard case for integer detectors.

    Returns:
        profile       : list[float] rounded to 5 dp
        left_exact    : float -- true left boundary in pixels (continuous)
        right_exact   : float -- true right boundary in pixels (continuous)
        sub_px_left   : float -- sub-pixel offset of left edge [0,1)
        sub_px_right  : float -- sub-pixel offset of right edge [0,1)
    """
    px_per_m = NUM_SAMPLES / wall_length_m

    # True continuous boundary positions with random sub-pixel offsets
    sub_px_left  = rng.uniform(0.1, 0.9)   # avoid exact-integer edges
    sub_px_right = rng.uniform(0.1, 0.9)

    left_exact  = offset_m * px_per_m + sub_px_left
    right_exact = (offset_m + opening_width_m) * px_per_m + sub_px_right

    opening_width_px = right_exact - left_exact

    profile = np.empty(NUM_SAMPLES)
    for p in range(NUM_SAMPLES):
        # Pixel footprint spans [p, p+1]
        pixel_left  = float(p)
        pixel_right = float(p + 1)

        # Overlap of this pixel with the opening [left_exact, right_exact]
        overlap_left  = max(pixel_left,  left_exact)
        overlap_right = min(pixel_right, right_exact)
        overlap = max(0.0, overlap_right - overlap_left)
        frac = overlap  # pixel width = 1, so fraction = overlap / 1

        # Blend depth proportionally; add noise
        base_depth = (1.0 - frac) * D_WALL + frac * D_VOID
        if frac > 0.5:
            noise = rng.normal(0, NOISE_VOID)
        else:
            noise = rng.normal(0, NOISE_WALL)
        profile[p] = base_depth + noise

    return (
        [round(float(v), 5) for v in profile],
        float(left_exact),
        float(right_exact),
        float(sub_px_left),
        float(sub_px_right),
    )


def run():
    rng_master = np.random.RandomState(GLOBAL_SEED)

    # (room_id, opening_id, wall_length_m, gt_width_m, offset_m)
    openings_cfg = [
        ("living_room",    "door_hallway",   4.8, 0.900, 1.80),
        ("living_room",    "window_north",   4.8, 1.600, 1.60),
        ("hallway",        "door_living",    1.5, 0.900, 0.30),
        ("hallway",        "door_kitchen",   5.4, 0.900, 2.10),
        ("hallway",        "door_master",    1.5, 0.900, 0.30),
        ("kitchen",        "door_hallway_k", 4.2, 0.900, 1.50),
        ("kitchen",        "window_kitchen", 3.6, 1.400, 1.10),
        ("master_bedroom", "door_hallway_m", 4.2, 0.900, 1.65),
        ("master_bedroom", "window_bedroom", 4.8, 1.800, 1.50),
    ]

    profile_lookup = {}
    gt_depth_records = {}

    for room_id, oid, wall_len, gt_w, offset in openings_cfg:
        opening_seed = int(rng_master.randint(0, 2**31 - 1))
        opening_rng  = np.random.RandomState(opening_seed)

        profile, left_exact, right_exact, sub_left, sub_right = \
            make_depth_profile_beam_footprint(wall_len, gt_w, offset, opening_rng)

        key = f"{room_id}/{oid}"
        profile_lookup[key] = {
            "wall_length_m":   wall_len,
            "offset_m":        offset,
            "depth_profile_m": profile,
        }

        gt_depth_records[key] = {
            "room_id":   room_id,
            "opening_id": oid,
            "gt_width_m": gt_w,
            "gt_offset_m": offset,
            "wall_length_m": wall_len,
            "left_boundary_px_continuous":  left_exact,
            "right_boundary_px_continuous":  right_exact,
            "sub_pixel_offset_left":  sub_left,
            "sub_pixel_offset_right": sub_right,
            "seed": opening_seed,
        }

        m_per_px = wall_len / NUM_SAMPLES
        print(f"  {room_id}/{oid}: left={left_exact:.3f}px right={right_exact:.3f}px "
              f"true_w={gt_w:.3f}m px_span={(right_exact-left_exact)*m_per_px:.4f}m")

    # Inject into LiDAR JSON
    with open(LIDAR_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for room in data["rooms"]:
        rid = room["room_id"]
        for op in room.get("openings", []):
            oid = op["opening_id"]
            key = f"{rid}/{oid}"
            if key in profile_lookup:
                op.update(profile_lookup[key])

    with open(LIDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"\nUpdated {LIDAR_FILE}")
    print(f"Model: beam-footprint blending, d_wall={D_WALL}m d_void={D_VOID}m "
          f"noise_wall={NOISE_WALL}m noise_void={NOISE_VOID}m")
    print(f"Sub-pixel offsets: uniform [0.1, 0.9) per edge -- true edge never on integer pixel")

    # Write GT file
    os.makedirs(GT_DIR, exist_ok=True)
    with open(GT_DEPTH_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "description": (
                "Ground-truth continuous boundary positions. "
                "MUST NOT be read by pipeline/ code. Only scripts/ scoring code may use this."
            ),
            "global_seed": GLOBAL_SEED,
            "model": "beam_footprint_blend",
            "num_samples": NUM_SAMPLES,
            "d_wall_m": D_WALL,
            "d_void_m": D_VOID,
            "noise_wall_sigma_m": NOISE_WALL,
            "noise_void_sigma_m": NOISE_VOID,
            "openings": gt_depth_records,
        }, f, indent=2)

    print(f"Ground-truth boundaries -> {GT_DEPTH_FILE}")
    print("\nNOTE: SIMULATED from a parametric dToF beam-footprint model, not a real device.")


if __name__ == "__main__":
    run()
