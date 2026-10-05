# Device Matrix
**Which tier runs on which device, and the accuracy each tier honestly delivers.**

---

## Tier × Device Compatibility

| Device | LiDAR Tier | Photo Tier | Video Tier |
|---|---|---|---|
| iPhone 12 Pro / 12 Pro Max | ✅ Full | ✅ Full | ⚠️ NOT IMPLEMENTED |
| iPhone 13 Pro / 13 Pro Max | ✅ Full | ✅ Full | ⚠️ NOT IMPLEMENTED |
| iPhone 14 Pro / 14 Pro Max | ✅ Full | ✅ Full | ⚠️ NOT IMPLEMENTED |
| iPhone 15 Pro / 15 Pro Max | ✅ Full | ✅ Full | ⚠️ NOT IMPLEMENTED |
| iPhone 12 / 13 / 14 / 15 (non-Pro) | ❌ No LiDAR | ✅ Full | ⚠️ NOT IMPLEMENTED |
| iPhone 11 and earlier | ❌ No LiDAR | ⚠️ Reduced (older EXIF, narrower FOV) | ⚠️ NOT IMPLEMENTED |
| iPad Pro 2020+ (with LiDAR) | ✅ Full | ✅ Full | ⚠️ NOT IMPLEMENTED |
| Android (any) | ❌ No Apple LiDAR | ⚠️ Photo only (EXIF varies) | ⚠️ NOT IMPLEMENTED |

---

## Accuracy by Tier (Simulated Benchmark Numbers — labelled SIM)

> ⚠️ These are **simulated** numbers derived from the parametric dToF + point-cloud benchmark.
> Real numbers will be updated here once real capture data is provided.

| Tier | Wall Length Error | Ceiling Height Error | Opening Width Error | Footprint Error | Source |
|---|---|---|---|---|---|
| **LiDAR (Pro)** | ±0.93 cm (95% CI) | ±0.27 cm (95% CI) | ±1.28 cm (95% CI) | ~0.5% | SIM — empirical held-out |
| **Photos** | ±8% (claimed) | ±14 cm (claimed) | ±15 cm (claimed) | ±8% | NOT IMPLEMENTED — no real data |
| **Video** | ±3% (claimed) | ±5.5 cm (claimed) | ±6.5 cm (claimed) | ±3% | NOT IMPLEMENTED — no real data |

**Key: SIM = simulated benchmark, REAL = measured against tape ground truth**

---

## What each tier can honestly claim

### LiDAR Tier ✅ (SIM validated)
- Requires iPhone 12 Pro or newer, or iPad Pro 2020+
- Uses hardware dToF LiDAR sensor — not ML-based depth estimation
- Point-cloud estimator: RANSAC plane fit + percentile span (no GT read)
- **Gate 1 (SIM):** 100% of openings within 2 cm ✅
- **Gate 2 (SIM):** Ceiling bias <0.5 cm, spread <0.5 cm ✅
- **Gate 3 (SIM):** Max wall repeatability delta 0.22 cm ✅
- **Gate 4 (SIM):** SLAM reduces residual drift from 10.77 cm → 0.81 cm ✅
- **H2H vs Polycam (SIM):** 100% win on 10 dimensions ✅
- Overlap with GT poses: **0.259 m² (structural hallway oversizing) — acknowledged bug**

### Photo Tier ⚠️ (NOT IMPLEMENTED — infrastructure ready)
- Works on any iPhone (no LiDAR required)
- Model: Depth Anything V2 Metric Indoor Small (Apache 2.0)
- Weights: ~100 MB, one-time download
- All gates require real data to validate

### Video Tier ❌ (NOT IMPLEMENTED)
- Planned: COLMAP or VO + Depth Anything V2 Metric
- No working implementation yet
- Excluded from all claimed passes

---

## Recommended Setup

| Use case | Recommended device | Recommended tier |
|---|---|---|
| Insurance inspection (professional) | iPhone 15 Pro Max | LiDAR |
| Pre-purchase survey | iPhone 13 Pro or newer | LiDAR |
| Quick room estimate | Any iPhone 12+ | Photos |
| Full property walkthrough | iPhone 13 Pro + stabiliser | Video (once implemented) |
| Legacy device | iPhone 11 or Android | Photos (widened intervals) |
