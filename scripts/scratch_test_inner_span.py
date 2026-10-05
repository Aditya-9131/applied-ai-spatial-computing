import numpy as np

VOID_THRESHOLD = 1.0
NUM_SAMPLES = 200

def make_depth_profile(wall_length_m, opening_width_m, offset_m, seed):
    rng = np.random.RandomState(seed)
    n = NUM_SAMPLES
    px_per_m = n / wall_length_m
    left_px  = int(round(offset_m * px_per_m))
    right_px = int(round((offset_m + opening_width_m) * px_per_m))
    left_px  = max(0, min(left_px,  n - 1))
    right_px = max(0, min(right_px, n - 1))
    d_wall, d_void, noise_std = 0.05, 3.80, 0.004
    profile = np.full(n, d_wall) + rng.normal(0, noise_std, n)
    for px in range(left_px, right_px+1):
        profile[px] = d_void + rng.normal(0, 0.05)
    return profile, wall_length_m / n, left_px, right_px

def detect_inner_span(profile, mpp):
    """First void pixel to last void pixel (inclusive) gives the inner structural span."""
    void_mask = profile > VOID_THRESHOLD
    void_indices = np.where(void_mask)[0]
    if len(void_indices) < 2:
        return None
    left  = void_indices[0]
    right = void_indices[-1] + 1   # exclusive right edge
    return (right - left) * mpp

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

print("Method: first/last void pixel inner span")
passed = 0
for oid, wall_len, gt_w, offset, seed in cases:
    prof, mpp, lp, rp = make_depth_profile(wall_len, gt_w, offset, seed)
    est = detect_inner_span(prof, mpp)
    if est is not None:
        err = (est - gt_w) * 100
        ok = abs(err) <= 2.0
        if ok:
            passed += 1
        status = "PASS" if ok else "FAIL"
        print(f"  {oid:22s} GT={gt_w:.3f} Est={est:.4f} Err={err:+.2f}cm  true=[{lp},{rp}] detected_span={rp-lp+1}px  {status}")
    else:
        print(f"  {oid:22s} NO VOID FOUND")
print(f"Pass: {passed}/9")
