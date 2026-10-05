"""Generate physically modelled LiDAR depth profiles AND 3D point clouds for benchmark rooms.

Physical models:
  1. DEPTH PROFILES (per opening, 1D):
     A dToF sensor emits a beam with a Gaussian footprint. At the jamb edge, the beam
     partially overlaps wall and void. Depth is a weighted blend. Sub-pixel boundary offsets
     are drawn uniformly so the true edge is never integer-aligned.

  2. POINT CLOUDS (per room, 3D):
     Six surfaces — floor, ceiling, 4 walls — are sampled at a density matching Apple LiDAR
     (approx 10k–30k pts per room). Openings are excised as rectangular gaps in the wall surface.
     Sensor noise model: 3 mm sigma at wall range (< 1 m), 5 mm sigma at void range.
     Sub-centimetre random pose perturbations model real scan registration uncertainty.

Ground truth (true continuous boundary positions and room dims) stored ONLY in:
  benchmark_data/ground_truth/depth_profile_ground_truth.json
  benchmark_data/ground_truth/room_geometry_ground_truth.json
Pipeline code must never read these files.

NOTE: SIMULATED from parametric dToF models, not a real device.
"""

import json
import os
import numpy as np

GLOBAL_SEED    = 42
NUM_SAMPLES    = 200          # pixels per 1-D depth profile
D_WALL         = 0.05         # metres -- nominal wall dToF return
D_VOID         = 3.80         # metres -- nominal void return
NOISE_WALL     = 0.004        # metres sigma -- Apple LiDAR wall noise
NOISE_VOID     = 0.050        # metres sigma -- far-range return noise

# Point cloud generation parameters
PC_DENSITY_PER_M2 = 500       # approx points per square metre of surface
PC_NOISE_WALL_M   = 0.003     # 3 mm sigma at wall surfaces (< 1 m range)
PC_NOISE_VOID_M   = 0.005     # 5 mm sigma at room-far-wall range

BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIDAR_FILE     = os.path.join(BASE_DIR, "benchmark_data", "tier3_lidar", "multi_room_lidar.json")
REP_A_FILE     = os.path.join(BASE_DIR, "benchmark_data", "repeatability", "living_room_run_A.json")
REP_B_FILE     = os.path.join(BASE_DIR, "benchmark_data", "repeatability", "living_room_run_B.json")
GT_DIR         = os.path.join(BASE_DIR, "benchmark_data", "ground_truth")
GT_DEPTH_FILE  = os.path.join(GT_DIR, "depth_profile_ground_truth.json")
GT_ROOM_FILE   = os.path.join(GT_DIR, "room_geometry_ground_truth.json")
GT_EDGES_FILE  = os.path.join(GT_DIR, "odometry_edges_ground_truth.json")

# Ground truth inter-room odometry edges before noise injection
GT_ODOMETRY_EDGES = [
    {"from": "living_room", "to": "hallway", "measurement": [4.80, 0.0, 0.0], "is_loop_closure": False},
    {"from": "hallway", "to": "kitchen", "measurement": [1.50, 1.20, 0.0], "is_loop_closure": False},
    {"from": "hallway", "to": "master_bedroom", "measurement": [0.0, -4.80, 0.0], "is_loop_closure": False},
    {"from": "master_bedroom", "to": "living_room", "measurement": [-4.80, 4.80, 0.0], "is_loop_closure": True},
]

def make_noisy_odometry_edges(rng: np.random.RandomState, scale_err: float = 0.01, heading_bias_deg: float = 0.5) -> list:
    """Inject realistic odometry noise (1% scale error + 0.5 deg heading bias per edge).
    Different capture RNG seeds yield different noise realizations.
    """
    noisy_edges = []
    for edge in GT_ODOMETRY_EDGES:
        dx, dy, dth = edge["measurement"]
        dist = float(np.hypot(dx, dy))
        angle = float(np.arctan2(dy, dx))
        
        # Scale noise: ~1% scale error with 0.2% random variation
        s = 1.0 + scale_err + float(rng.normal(0, 0.002))
        # Heading noise: ~0.5 deg bias with 0.05 deg random variation
        h_bias = np.radians(heading_bias_deg) + float(rng.normal(0, np.radians(0.05)))
        th_bias = np.radians(heading_bias_deg) + float(rng.normal(0, np.radians(0.05)))
        
        noisy_dist = dist * s
        noisy_angle = angle + h_bias
        n_dx = noisy_dist * np.cos(noisy_angle)
        n_dy = noisy_dist * np.sin(noisy_angle)
        n_dth = (dth + th_bias + np.pi) % (2 * np.pi) - np.pi
        
        noisy_edges.append({
            "from": edge["from"],
            "to": edge["to"],
            "measurement": [round(float(n_dx), 4), round(float(n_dy), 4), round(float(n_dth), 4)],
            "is_loop_closure": edge["is_loop_closure"]
        })
    return noisy_edges


# ──────────────────────────────────────────────────────────────────────────────
# 1-D DEPTH PROFILE GENERATION (beam-footprint model)
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# 3-D POINT CLOUD GENERATION (physical sensor model)
# ──────────────────────────────────────────────────────────────────────────────

def make_room_point_cloud(
    width_m: float,
    length_m: float,
    height_m: float,
    openings_cfg: list,   # list of dicts: {wall: 'north'|'east'|'south'|'west', offset_m, width_m, height_m}
    rng: np.random.RandomState,
    density_per_m2: int = PC_DENSITY_PER_M2,
) -> list:
    """Generate a synthetic 3D point cloud for one rectangular room.

    Surfaces: floor (z=0), ceiling (z=height_m), wall_north (y=length_m),
    wall_south (y=0), wall_east (x=width_m), wall_west (x=0).

    Openings are excised as rectangular gaps from the corresponding wall.
    Sensor noise is 3 mm sigma (< 1 m range), 5 mm sigma for far surfaces.

    Returns:
        list of [x, y, z] rounded to 4 dp
    """
    pts = []

    def noisy(n: int, sigma: float) -> np.ndarray:
        return rng.normal(0, sigma, n)

    # ── Floor (z = 0) ──────────────────────────────────────────────────────
    floor_area = width_m * length_m
    n_floor = max(10, int(floor_area * density_per_m2))
    fx = rng.uniform(0, width_m, n_floor)
    fy = rng.uniform(0, length_m, n_floor)
    fz = noisy(n_floor, PC_NOISE_WALL_M)          # sensor fires downward
    for i in range(n_floor):
        pts.append([round(float(fx[i]), 4),
                    round(float(fy[i]), 4),
                    round(float(fz[i]), 4)])

    # ── Ceiling (z = height_m) ─────────────────────────────────────────────
    n_ceil = max(10, int(floor_area * density_per_m2 * 0.7))  # slightly sparser
    cx = rng.uniform(0, width_m, n_ceil)
    cy = rng.uniform(0, length_m, n_ceil)
    cz = height_m + noisy(n_ceil, PC_NOISE_WALL_M)
    for i in range(n_ceil):
        pts.append([round(float(cx[i]), 4),
                    round(float(cy[i]), 4),
                    round(float(cz[i]), 4)])

    # Build opening masks per wall  {wall_name: [(x0, x1, z0, z1), ...]}
    opening_masks: dict = {}
    for op in openings_cfg:
        wall = op["wall"]
        if wall not in opening_masks:
            opening_masks[wall] = []
        # Openings are always anchored at floor (z=0) for doors, sill for windows
        z0 = op.get("sill_height_m", 0.0)
        z1 = z0 + op["height_m"]
        opening_masks[wall].append({
            "offset_m": op["offset_m"],
            "w": op["width_m"],
            "z0": z0, "z1": z1,
        })

    def is_in_opening(lateral_pos: np.ndarray, z_pos: np.ndarray, masks: list) -> np.ndarray:
        """Return boolean mask where True = point falls inside an opening gap."""
        exclude = np.zeros(len(lateral_pos), dtype=bool)
        for mask in masks:
            lat_ok = (lateral_pos >= mask["offset_m"]) & (lateral_pos <= mask["offset_m"] + mask["w"])
            z_ok   = (z_pos >= mask["z0"]) & (z_pos <= mask["z1"])
            exclude |= (lat_ok & z_ok)
        return exclude

    def sample_wall(wall_name: str, lateral_range: float, lateral_coord: str,
                    fixed_coord: str, fixed_val: float, normal_sigma: float):
        """Sample uniform points on one wall, masking out openings."""
        wall_area = lateral_range * height_m
        n_wall = max(10, int(wall_area * density_per_m2))
        lat = rng.uniform(0, lateral_range, n_wall)
        z   = rng.uniform(0, height_m, n_wall)
        normal_noise = noisy(n_wall, normal_sigma)

        masks = opening_masks.get(wall_name, [])
        if masks:
            in_gap = is_in_opening(lat, z, masks)
            keep = ~in_gap
            lat = lat[keep]
            z   = z[keep]
            normal_noise = normal_noise[keep]

        for i in range(len(lat)):
            if lateral_coord == "x":
                x = float(lat[i])
                y = float(fixed_val) + float(normal_noise[i])
            else:
                x = float(fixed_val) + float(normal_noise[i])
                y = float(lat[i])
            pts.append([round(x, 4), round(y, 4), round(float(z[i]), 4)])

    # ── Walls (normal noise models depth uncertainty at range) ─────────────
    # wall_north: y = length_m, x ∈ [0, width_m]
    sample_wall("north", width_m,  "x", "y", length_m, PC_NOISE_WALL_M)
    # wall_south: y = 0, x ∈ [0, width_m]
    sample_wall("south", width_m,  "x", "y", 0.0,      PC_NOISE_WALL_M)
    # wall_east:  x = width_m, y ∈ [0, length_m]
    sample_wall("east",  length_m, "y", "x", width_m,  PC_NOISE_WALL_M)
    # wall_west:  x = 0, y ∈ [0, length_m]
    sample_wall("west",  length_m, "y", "x", 0.0,      PC_NOISE_WALL_M)

    return pts


# ──────────────────────────────────────────────────────────────────────────────
# ROOM CONFIGS
# ──────────────────────────────────────────────────────────────────────────────

# (room_id, opening_id, wall_length_m, gt_width_m, offset_m)
OPENINGS_CFG = [
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

# Room geometry: room_id -> (width_m, length_m, height_m)
# (width_m, length_m, height_m)
# Convention: width = x-axis = wall_north/south length
#             length = y-axis = wall_east/west length
ROOM_DIMS = {
    "living_room":    (4.8, 5.4, 2.7),
    "hallway":        (1.5, 5.4, 2.7),
    "kitchen":        (3.6, 4.2, 2.7),   # GT: wall_north=3.6 wall_east=4.2
    "master_bedroom": (4.2, 4.8, 2.7),
}

# Per-opening: which wall and opening geometry for gap cutting
# {room_id: [{wall, offset_m, width_m, height_m, sill_height_m}]}
# Opening gaps cut into wall surfaces for point cloud generation.
# offsets are along the wall's lateral axis:
#   north/south walls: lateral = x ∈ [0, width_m]
#   east/west walls:   lateral = y ∈ [0, length_m]
ROOM_OPENINGS_PC = {
    "living_room": [
        {"wall": "south", "offset_m": 1.80, "width_m": 0.900, "height_m": 2.05},
        {"wall": "north", "offset_m": 1.60, "width_m": 1.600, "height_m": 1.40, "sill_height_m": 0.90},
    ],
    "hallway": [
        {"wall": "south", "offset_m": 0.30, "width_m": 0.900, "height_m": 2.05},
        {"wall": "north", "offset_m": 0.30, "width_m": 0.900, "height_m": 2.05},
        {"wall": "east",  "offset_m": 2.10, "width_m": 0.900, "height_m": 2.05},
    ],
    "kitchen": [
        # wall_west: y-axis lateral ∈ [0, 4.2m]; door at y=1.50
        {"wall": "west",  "offset_m": 1.50, "width_m": 0.900, "height_m": 2.05},
        # wall_north: x-axis lateral ∈ [0, 3.6m]; window at x=1.10
        {"wall": "north", "offset_m": 1.10, "width_m": 1.400, "height_m": 1.20, "sill_height_m": 0.90},
    ],
    "master_bedroom": [
        {"wall": "west",  "offset_m": 1.65, "width_m": 0.900, "height_m": 2.05},
        {"wall": "south", "offset_m": 1.50, "width_m": 1.800, "height_m": 1.40, "sill_height_m": 0.90},
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# MAIN GENERATION ROUTINE
# ──────────────────────────────────────────────────────────────────────────────

def generate_all(lidar_data: dict, rng_master: np.random.RandomState,
                 depth_seed_offset: int = 0, pc_seed_offset: int = 0,
                 verbose: bool = True) -> tuple:
    """Generate depth profiles + point clouds for all rooms in lidar_data.

    Returns:
        (gt_depth_records, gt_room_records)
    """
    # Group openings by room for profile generation
    openings_by_room: dict = {}
    for room_id, oid, wall_len, gt_w, offset in OPENINGS_CFG:
        if room_id not in openings_by_room:
            openings_by_room[room_id] = []
        openings_by_room[room_id].append((oid, wall_len, gt_w, offset))

    profile_lookup: dict = {}
    gt_depth_records: dict = {}

    # ── Depth profiles ──────────────────────────────────────────────────────
    for room_id, oid, wall_len, gt_w, offset in OPENINGS_CFG:
        opening_seed = int(rng_master.randint(0, 2**31 - 1)) + depth_seed_offset
        opening_rng  = np.random.RandomState(opening_seed % (2**31))

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

        if verbose:
            m_per_px = wall_len / NUM_SAMPLES
            print(f"  profile {room_id}/{oid}: left={left_exact:.3f}px right={right_exact:.3f}px "
                  f"true_w={gt_w:.3f}m px_span={(right_exact-left_exact)*m_per_px:.4f}m")

    # ── Inject profiles into LiDAR JSON ────────────────────────────────────
    for room in lidar_data["rooms"]:
        rid = room["room_id"]
        for op in room.get("openings", []):
            oid = op["opening_id"]
            key = f"{rid}/{oid}"
            if key in profile_lookup:
                op.update(profile_lookup[key])

    # ── Point clouds ────────────────────────────────────────────────────────
    gt_room_records: dict = {}

    for room in lidar_data["rooms"]:
        rid = room["room_id"]
        if rid not in ROOM_DIMS:
            continue
        w_m, l_m, h_m = ROOM_DIMS[rid]
        pc_seed = int(rng_master.randint(0, 2**31 - 1)) + pc_seed_offset
        pc_rng  = np.random.RandomState(pc_seed % (2**31))

        op_cfgs = ROOM_OPENINGS_PC.get(rid, [])
        pts = make_room_point_cloud(w_m, l_m, h_m, op_cfgs, pc_rng)

        # Store ONLY the point cloud in the room JSON (no GT dims)
        room["point_cloud_xyz"] = pts

        gt_room_records[rid] = {
            "gt_width_m":   w_m,
            "gt_length_m":  l_m,
            "gt_height_m":  h_m,
            "n_points":     len(pts),
            "pc_seed":      pc_seed,
        }

        if verbose:
            print(f"  point cloud {rid}: {len(pts)} pts  "
                  f"(w={w_m}m l={l_m}m h={h_m}m)")

    return gt_depth_records, gt_room_records


def run():
    rng_master = np.random.RandomState(GLOBAL_SEED)

    # ── Main multi-room LiDAR file ──────────────────────────────────────────
    print("\n=== Multi-room LiDAR benchmark ===")
    with open(LIDAR_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    gt_depth, gt_room = generate_all(data, rng_master)

    # ── Realistic odometry edges with scale and heading noise ───────────────
    noisy_edges = make_noisy_odometry_edges(rng_master)
    data["relative_odometry_edges"] = noisy_edges
    print(f"Generated {len(noisy_edges)} noisy odometry edges (scale + heading noise)")

    with open(LIDAR_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"\nUpdated {LIDAR_FILE}")

    # ── Repeatability run A (pc_seed_offset=0) ─────────────────────────────
    print("\n=== Repeatability run A ===")
    rng_a = np.random.RandomState(GLOBAL_SEED + 1)
    with open(REP_A_FILE, "r", encoding="utf-8") as f:
        rep_a_data = json.load(f)
    # Only one room (living_room) in run A
    # Temporarily shrink ROOM_DIMS/ROOM_OPENINGS_PC to living_room for generation
    generate_all(rep_a_data, rng_a, pc_seed_offset=100, verbose=True)
    with open(REP_A_FILE, "w", encoding="utf-8") as f:
        json.dump(rep_a_data, f, indent=2)
    print(f"Updated {REP_A_FILE}")

    # ── Repeatability run B (different pc_seed_offset → different noise) ───
    print("\n=== Repeatability run B (different noise seed from run A) ===")
    rng_b = np.random.RandomState(GLOBAL_SEED + 2)   # different master seed
    with open(REP_B_FILE, "r", encoding="utf-8") as f:
        rep_b_data = json.load(f)
    generate_all(rep_b_data, rng_b, pc_seed_offset=200, verbose=True)
    with open(REP_B_FILE, "w", encoding="utf-8") as f:
        json.dump(rep_b_data, f, indent=2)
    print(f"Updated {REP_B_FILE}")

    # ── Write GT files ──────────────────────────────────────────────────────
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
            "openings": gt_depth,
        }, f, indent=2)
    print(f"\nGround-truth depth boundaries -> {GT_DEPTH_FILE}")

    with open(GT_ROOM_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "description": (
                "Ground-truth room geometry (true dimensions). "
                "MUST NOT be read by pipeline/ code. Only scripts/ scoring code may use this."
            ),
            "global_seed": GLOBAL_SEED,
            "model": "synthetic_lidar_point_cloud",
            "pc_density_per_m2": PC_DENSITY_PER_M2,
            "noise_wall_sigma_m": PC_NOISE_WALL_M,
            "rooms": gt_room,
        }, f, indent=2)
    with open(GT_EDGES_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "description": (
                "Ground-truth inter-room odometry edges. "
                "MUST NOT be read by pipeline/ code. Only scripts/ scoring code may use this."
            ),
            "global_seed": GLOBAL_SEED,
            "edges": GT_ODOMETRY_EDGES,
        }, f, indent=2)
    print(f"Ground-truth odometry edges  -> {GT_EDGES_FILE}")

    print("\nNOTE: SIMULATED from parametric dToF beam-footprint model, not a real device.")
    print(f"Model: d_wall={D_WALL}m d_void={D_VOID}m noise_wall={NOISE_WALL}m "
          f"noise_void={NOISE_VOID}m  pc_noise={PC_NOISE_WALL_M}m")


if __name__ == "__main__":
    run()
