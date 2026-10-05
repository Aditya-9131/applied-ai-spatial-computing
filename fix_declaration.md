# FIX DECLARATION
## Applied AI Engineer Case Study — Part 4 Submission (Revised)

---

### 1. The Failing Gate

* **Target Gate:** Opening Widths Accuracy (LiDAR Tier)
* **Contract:** error ≤ 2.0 cm on ≥ 85.0% of openings (missed/phantom count as misses)
* **Baseline (`before-fix` tag):** **55.6% pass rate** (5/9 openings passed)
* **Failing openings:** `door_hallway` +3.60 cm, `door_hallway_k` +2.40 cm,
  `window_kitchen` +2.20 cm, `window_bedroom` +2.40 cm

---

### 2. Root Cause — Empirical Evidence

From `scripts/diagnose_openings.py` → `fix_evidence.txt`:

| Opening | GT (m) | Est (m) | Err (cm) | Err (px) | m/px | RndLeft | RndRight |
|---|---|---|---|---|---|---|---|
| door_hallway | 0.900 | 0.936 | +3.60 | +1.50 | 0.0240 | −0.000 | +0.500 |
| window_north | 1.600 | 1.608 | +0.80 | +0.33 | 0.0240 | +0.333 | −0.333 |
| door_living | 0.900 | 0.908 | +0.75 | +1.00 | 0.0075 | +0.000 | +0.000 |
| door_kitchen | 0.900 | 0.918 | +1.80 | +0.67 | 0.0270 | +0.222 | −0.111 |
| door_master | 0.900 | 0.908 | +0.75 | +1.00 | 0.0075 | +0.000 | +0.000 |
| door_hallway_k | 0.900 | 0.924 | +2.40 | +1.14 | 0.0210 | −0.429 | −0.286 |
| window_kitchen | 1.400 | 1.422 | +2.20 | +1.22 | 0.0180 | −0.111 | +0.111 |
| door_hallway_m | 0.900 | 0.903 | +0.30 | +0.14 | 0.0210 | +0.429 | −0.429 |
| window_bedroom | 1.800 | 1.824 | +2.40 | +1.00 | 0.0240 | +0.500 | +0.500 |

**Key diagnostics:**

```
Pearson corr(error_m,  m_per_px)               = +0.4715
Pearson corr(error_px, rnd_right − rnd_left)   = +1.0000
```

The error-in-pixels correlates **perfectly (r = 1.0)** with the rounding residual
`rnd_right − rnd_left`. This is not sampling noise — it is a deterministic
aliasing artefact.

**Mechanism:**

The depth profile is built by placing the left jamb at `left_px = int(round(offset × px_per_m))`
and the right jamb at `right_px = int(round((offset + gt_w) × px_per_m))`.
These are integer pixels. In `diff = |profile[i+1] − profile[i]|`:

```
Left gradient peak  → diff-index = left_px − 1
Right gradient peak → diff-index = right_px
```

The detector measures `width_px = right_idx − left_idx = right_px − (left_px − 1)`.
This is always `true_pixel_span + 1`.

When the true boundary does *not* land on an integer pixel, the rounding adds a
further residual of `(rnd_right − rnd_left)` pixels. The total measurement bias is:

```
bias_m = (1 + rnd_right − rnd_left) × m_per_px
```

which ranges from **+0.75 cm** (`door_living`, hallway, m/px = 0.0075 m)
to **+3.60 cm** (`door_hallway`, living room, m/px = 0.024 m).

---

### 3. Shipped Fix

**Sub-pixel linear interpolation at depth-crossing threshold.**

For each rising and falling edge, find the continuous sample index `t ∈ [i, i+1]`
where the depth profile crosses `threshold = 1.0 m` (midpoint between wall ~0.05 m
and void ~3.80 m):

```
t = i + (threshold − profile[i]) / (profile[i+1] − profile[i])
```

* `left_edge_continuous`  = t at the **wall → void** rising edge
* `right_edge_continuous` = t at the **void → wall** falling edge
* `width_m = (right_edge_continuous − left_edge_continuous) × m_per_px`

This eliminates both the systematic +1 pixel offset and the rounding residual.
Only dToF sensor noise remains (σ ≈ 4 mm, 95% CI ≈ ±7.8 mm < gate limit 2.0 cm).

No constant depends on a known ground-truth width.

---

### 4. Predicted Post-Fix Numbers

| Metric | Before-fix | Predicted after-fix |
|---|---|---|
| Pass rate | 55.6% (5/9) | **≥ 89%** (conservative) / **100%** (expected) |
| Max error | 3.60 cm | < 1.0 cm |
| Gate | FAIL | PASS |

Conservative bound: 8/9 (89%) allows for one opening where threshold noise
pushes a crossing outside the ≤ 2.0 cm limit. Expected: 9/9 (100%) since
4 mm noise × 1.96 = 7.8 mm ≪ 2.0 cm gate.
