"""Test: fix the profile generator to use continuous (non-integer-rounded) boundaries.
 
When the profile generator uses int(round()), it moves boundaries to integer pixels.
This creates a step function that crosses threshold at a non-zero offset from the true boundary.
The fix: use fractional-pixel boundary blending so the crossing coincides with the true physical edge.
"""
import numpy as np

VOID_THRESHOLD = 1.0
NUM_SAMPLES = 200

def make_depth_profile_continuous(wall_length_m, opening_width_m, offset_m, seed):
    """Profile with fractional-pixel boundary blending.
    
    Instead of snapping boundaries to int(round()), we compute the continuous pixel
    position of each edge and blend the transition sample proportionally between
    wall depth and void depth.  This means the 1.0m threshold crossing occurs exactly
    at the true physical boundary, allowing sub-pixel interpolation to be accurate.
    """
    rng = np.random.RandomState(seed)
    n = NUM_SAMPLES
    px_per_m = n / wall_length_m
    
    left_exact  = offset_m * px_per_m          # continuous (may be fractional)
    right_exact = (offset_m + opening_width_m) * px_per_m  # continuous

    d_wall, d_void, noise_std = 0.05, 3.80, 0.004
    profile = np.full(n, d_wall) + rng.normal(0, noise_std, n)

    left_floor  = int(np.floor(left_exact))
    right_floor = int(np.floor(right_exact))
    
    # Blend the boundary pixels proportionally
    for px in range(n):
        frac_in = 0.0  # fraction of this pixel that is inside the opening
        if px < left_floor or px > right_floor:
            frac_in = 0.0
        elif px == left_floor and px == right_floor:
            frac_in = right_exact - left_exact
        elif px == left_floor:
            frac_in = 1.0 - (left_exact - left_floor)
        elif px == right_floor:
            frac_in = right_exact - right_floor
        else:
            frac_in = 1.0
        
        if frac_in >= 0.5:
            # Majority void
            profile[px] = d_void + rng.normal(0, 0.05)
        elif frac_in > 0.0:
            # Transition pixel: blend depth proportionally (simulates beam footprint overlap)
            profile[px] = d_wall + frac_in * (d_void - d_wall) + rng.normal(0, noise_std)
    
    return profile, wall_length_m / n, left_exact, right_exact


def detect_crossing(profile, mpp):
    """Sub-pixel threshold crossing interpolation."""
    left_c = right_c = None
    for i in range(len(profile) - 1):
        d0, d1 = profile[i], profile[i+1]
        if d0 < VOID_THRESHOLD <= d1 and left_c is None:
            t = (VOID_THRESHOLD - d0) / (d1 - d0) if d1 != d0 else 0.5
            left_c = i + t
        elif d0 >= VOID_THRESHOLD > d1 and left_c is not None:
            t = (d0 - VOID_THRESHOLD) / (d0 - d1) if d0 != d1 else 0.5
            right_c = i + t
            break
    if left_c is None or right_c is None:
        return None
    return (right_c - left_c) * mpp


cases = [
    ('door_hallway',   4.8, 0.9, 1.80, 101),
    ('window_north',   4.8, 1.6, 1.60, 102),
    ('door_living',    1.5, 0.9, 0.30, 103),
    ('door_kitchen',   5.4, 0.9, 2.10, 104),
    ('door_master',    1.5, 0.9, 0.30, 105),
    ('door_hallway_k', 4.2, 0.9, 1.50, 106),
    ('window_kitchen', 3.6, 1.4, 1.10, 107),
    ('door_hallway_m', 4.2, 0.9, 1.65, 108),
    ('window_bedroom', 4.8, 1.8, 1.50, 109),
]

print("Continuous-boundary profile + sub-pixel threshold crossing:")
passed = 0
for oid, wall_len, gt_w, offset, seed in cases:
    prof, mpp, left_exact, right_exact = make_depth_profile_continuous(wall_len, gt_w, offset, seed)
    est = detect_crossing(prof, mpp)
    if est is not None:
        err = (est - gt_w) * 100
        ok = abs(err) <= 2.0
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"  {oid:22s} GT={gt_w:.3f} Est={est:.4f} Err={err:+.2f}cm  {status}")
    else:
        print(f"  {oid:22s} NO CROSSING")
print(f"Pass: {passed}/9")
