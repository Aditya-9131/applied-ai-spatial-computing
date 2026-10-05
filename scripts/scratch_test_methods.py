"""Test multiple detector approaches on the existing integer-pixel profiles."""
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


# Method: gradient peak (original before-fix) - for reference
def detect_gradient_peak(profile, mpp):
    diff = np.abs(np.diff(profile))
    peaks = []
    for i in range(1, len(diff)-1):
        if diff[i] >= 1.0 and diff[i] >= diff[i-1] and diff[i] >= diff[i+1]:
            peaks.append((diff[i], i))
    if diff[0] >= 1.0: peaks.append((diff[0], 0))
    if diff[-1] >= 1.0: peaks.append((diff[-1], len(diff)-1))
    if len(peaks) < 2: return None
    peaks.sort(key=lambda x: -x[0])
    li = min(peaks[0][1], peaks[1][1])
    ri = max(peaks[0][1], peaks[1][1])
    return (ri - li) * mpp

# Method: gradient peak with -0.5px correction on each side
def detect_gradient_corrected(profile, mpp):
    diff = np.abs(np.diff(profile))
    peaks = []
    for i in range(1, len(diff)-1):
        if diff[i] >= 1.0 and diff[i] >= diff[i-1] and diff[i] >= diff[i+1]:
            peaks.append((diff[i], i))
    if diff[0] >= 1.0: peaks.append((diff[0], 0))
    if diff[-1] >= 1.0: peaks.append((diff[-1], len(diff)-1))
    if len(peaks) < 2: return None
    peaks.sort(key=lambda x: -x[0])
    li = min(peaks[0][1], peaks[1][1])
    ri = max(peaks[0][1], peaks[1][1])
    # diff[i] sits between samples i and i+1
    # Left peak at li: edge is at sample li+0.5 (midpoint between wall and void)
    # Right peak at ri: edge is at sample ri+0.5
    # But the true INNER span we want is from li+1 to ri (the void pixels)
    # li+1 = first void pixel, ri = last diff index of the void-to-wall transition
    # So the void pixel range is [li+1, ri] inclusive (ri samples are void at diff peak)
    # Width = (ri - (li+1) + 1) * mpp = (ri - li) * mpp  -- same as before!
    # The issue is that (ri-li)*mpp != gt_w because of rounding.
    # The gradient peak indices are always: left_peak = left_px-1, right_peak = right_px
    # So ri - li = right_px - (left_px - 1) = true_px_span_with_rounding + 1
    # Correct to true_px_span: subtract 1 pixel
    return (ri - li - 1) * mpp  # subtract the off-by-one

# Method: void region size (count void pixels, no +1)
def detect_void_count(profile, mpp):
    void_count = np.sum(profile > VOID_THRESHOLD)
    if void_count == 0: return None
    return void_count * mpp

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

for name, fn in [
    ("gradient_peak (before)", detect_gradient_peak),
    ("gradient_peak - 1px correction", detect_gradient_corrected),
    ("void_count (px count)", detect_void_count),
]:
    passed = 0
    print(f"\n{name}:")
    for oid, wall_len, gt_w, offset, seed in cases:
        prof, mpp, lp, rp = make_depth_profile(wall_len, gt_w, offset, seed)
        est = fn(prof, mpp)
        true_px_span = rp - lp  # true integer span (right_px - left_px)
        void_count   = rp - lp + 1  # number of void pixels
        if est is not None:
            err = (est - gt_w)*100
            ok = abs(err)<=2.0
            if ok: passed+=1
            status = "PASS" if ok else "FAIL"
            print(f"  {oid:22s} GT={gt_w:.3f} Est={est:.4f} Err={err:+.2f}cm  true_px={true_px_span} void_cnt={void_count}  {status}")
        else:
            print(f"  {oid:22s} NO DETECTION")
    print(f"  Pass: {passed}/9")
