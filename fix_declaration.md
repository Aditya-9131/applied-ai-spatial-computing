# Fix Declaration — Opening Width Estimation
## Applied AI Case Study, August 2026

Written BEFORE implementing the fix (commit: step1).

---

## 1. The Failing Gate

- **Gate:** Opening Width Error ≤ 2.0 cm on ≥ 85.0% of openings (LiDAR tier)
- **Before-fix result (live, tag `before-fix` on beam-footprint profiles):**
  - **55.6% pass rate (5/9)** — GATE FAILS
  - Max error: 3.60 cm (`door_hallway`)
  - Failing openings: `door_hallway` +3.60 cm, `door_hallway_k` +2.40 cm,
    `window_kitchen` +2.20 cm, `window_bedroom` +2.40 cm

---

## 2. Root Cause

**Single-scan sampling resolution limits edge position to ±1 pixel.**

The integer gradient-peak algorithm estimates the opening width as:

```
width = (right_peak_idx - left_peak_idx) × m_per_px
```

In `diff[i] = |profile[i+1] - profile[i]|` the left jamb gradient peak sits at
index `(left_pixel - 1)` and the right jamb peak at `right_pixel`. The measured
span is therefore `true_span_px + 1` — a systematic off-by-one (fencepost error).

Additionally, with a **single scan**, the true physical edge can lie anywhere
within the ±0.5 pixel band around a sample position. The integer detector cannot
resolve edge position beyond 1 pixel, so each edge contributes up to ±m_per_px/2
of quantisation error. For a 4.8 m wall with 200 samples, `m_per_px = 0.024 m`,
giving up to ±1.2 cm per edge, ±2.4 cm total — exactly matching the observed
failures.

**Evidence from `fix_evidence.txt`:**

| Diagnostic | Value |
|---|---|
| Pearson r(error_m, m_per_px) | +0.47 (errors scale with pixel size) |
| Pearson r(error_px, rnd_right − rnd_left) | **+1.00** (errors explained by rounding) |
| Sign match (error vs rounding direction) | 6/9 |

The r = 1.0 correlation proves the error is **entirely determined by how far
each true edge is from the nearest integer pixel** — a single-scan aliasing effect.

---

## 3. The Fix

**Multi-scan sub-pixel edge interpolation.**

A real dToF scanner (e.g. Apple LiDAR) captures a full 2D depth map, not a 1D
slice. We can extract N independent horizontal scan rows through the opening
region and estimate the jamb edge position from each row independently, then
average. Each row gives an independent sub-pixel estimate; averaging N rows
reduces the RMS edge error by √N.

But even for a single scan, the beam-footprint physical model provides a
**sub-pixel clue**: at the boundary pixel, depth is a blend of wall and void:

```
depth[boundary_px] = (1 - frac) × d_wall + frac × d_void
```

where `frac` is the fraction of the beam footprint inside the opening. Linear
interpolation finds the exact position `t ∈ [i, i+1]` where depth equals the
midpoint threshold:

```
t = i + (threshold - profile[i]) / (profile[i+1] - profile[i])
```

Because the beam-footprint model places the crossing **exactly at the physical
boundary**, this interpolation recovers the true sub-pixel edge position.

The corrected width estimator:

```python
# Find first rising crossing (wall -> void)
left_continuous = i + (threshold - profile[i]) / (profile[i+1] - profile[i])

# Find first falling crossing (void -> wall) after left_continuous
right_continuous = i + (profile[i] - threshold) / (profile[i] - profile[i+1])

width_m = (right_continuous - left_continuous) * m_per_px
```

**Why this works on beam-footprint profiles but failed on step-function profiles:**
In step-function profiles (integer-snapped boundaries), the crossing occurs at
`left_px - 0.75` (not at `left_px`), introducing a ~0.75 px systematic offset.
In beam-footprint profiles, the blended transition pixel has depth
`(1-frac)×0.05 + frac×3.8`, which crosses the 1.0 m threshold at the exact
fraction corresponding to the true physical boundary.

---

## 4. Predicted Post-Fix Numbers

| Metric | Before | Predicted after |
|---|---|---|
| Pass rate | 55.6% (5/9) | **≥ 88.9% (8/9)** conservative / **100% (9/9)** expected |
| Max error | 3.60 cm | < 1.5 cm |
| Root error | dToF noise σ=4mm → 95% CI ±7.8mm | Same noise, no bias |

**Reasoning for 100% expected:**
- Threshold crossing recovers sub-pixel edge to within dToF noise (σ ≈ 4 mm per edge)
- Combined 2-edge noise: σ_width = √2 × 4mm ≈ 5.7 mm
- 95% CI: ±1.96 × 5.7 mm ≈ ±1.1 cm < 2.0 cm gate

**Conservative bound 8/9 (88.9%):**
- Allows for 1 opening where void noise spike pushes crossing by 1-2 cm
- This would still clear the 85% gate threshold
