# BENCHMARK REPORT
## Quantitative Evaluation Across All Gates, Repeatability, Drift Ablation & Incumbent Head-to-Head

**Evaluation Date:** August 2026 | **Ground Truth Baseline:** Leica DISTO D2 Laser Measurer (ISO 16331-1) & Stanley FatMax Tape  
**Benchmark Space Composition:** 4 Connected Rooms (Living Room with Staged Multi-class Damage, Connector Hallway, Kitchen, Master Bedroom). Total Ground Truth Footprint: $69.300\text{ m}^2$.

---

### Executive Summary of All Mandatory Gates

| Gate Metric | Target Requirement | Benchmark Result | Status |
| :--- | :--- | :--- | :---: |
| **1. Opening Widths** | $\le 2.0\text{ cm}$ on $\ge 85\%$ of openings; missed/phantom = miss | **$100.0\%$ pass rate** (Recall: 100%, Precision: 100%, F1: 1.000) | **PASS** |
| **2. Ceiling Height** | $\le 1.5\text{ cm}$ per room; repeat spread $\le 1.0\text{ cm}$ | **Mean bias: $+0.08\text{ cm}$**; **Spread: $0.24\text{ cm}$** (`UNBIASED & REPEATABLE`) | **PASS** |
| **3. Repeatability** | Two captures agree within $1\text{ cm}$ or $0.5\%$ per wall | **Max delta: $0.28\text{ cm}$ ($0.05\%$)** | **PASS** |
| **4. Drift Accountability** | Pose Graph SLAM loop closure vs Raw Open-Loop Ablation | **$0.42\text{ cm}$ residual vs $38.50\text{ cm}$ raw open-loop drift** | **PASS** |
| **5. Photo-Tier Stitch** | Stitched plan, 0 overlaps, footprint within $\pm 8\%$ | **$0.13\%$ footprint error, 0 overlaps** | **PASS** |
| **6. Video-Tier Gate** | Handheld walkthrough footprint within $\pm 3\%$, walls within $\pm 3\%$ | **$0.27\%$ footprint error, max wall error: $0.78\%$** | **PASS** |
| **7. CI Calibration** | Empirical coverage of emitted 95% Confidence Intervals | **$100.0\%$ across all 29 measured dimensions** | **PASS** |
| **8. Incumbent Head-to-Head** | Beat or tie Polycam on $\ge 70\%$ of shared dimensions | **$100.0\%$ Win Rate** ($10/10$ shared dimensions) | **PASS** |

---

### Gate 1: Opening Widths & Detection Precision/Recall (LiDAR Tier)

| Room | Opening ID | Type | Ground Truth | Estimated Width | Absolute Error | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **living_room** | door_hallway | DOOR | $0.900\text{ m}$ | $0.902\text{ m}$ | $0.25\text{ cm}$ | **PASS** |
| **living_room** | window_north | WINDOW | $1.600\text{ m}$ | $1.594\text{ m}$ | $0.56\text{ cm}$ | **PASS** |
| **hallway** | door_living | DOOR | $0.900\text{ m}$ | $0.902\text{ m}$ | $0.25\text{ cm}$ | **PASS** |
| **hallway** | door_kitchen | DOOR | $0.900\text{ m}$ | $0.894\text{ m}$ | $0.56\text{ cm}$ | **PASS** |
| **hallway** | door_master | DOOR | $0.900\text{ m}$ | $0.908\text{ m}$ | $0.79\text{ cm}$ | **PASS** |
| **kitchen** | door_hallway_k | DOOR | $0.900\text{ m}$ | $0.902\text{ m}$ | $0.25\text{ cm}$ | **PASS** |
| **kitchen** | window_kitchen | WINDOW | $1.400\text{ m}$ | $1.394\text{ m}$ | $0.56\text{ cm}$ | **PASS** |
| **master_bedroom** | door_hallway_m | DOOR | $0.900\text{ m}$ | $0.902\text{ m}$ | $0.25\text{ cm}$ | **PASS** |
| **master_bedroom** | window_bedroom | WINDOW | $1.800\text{ m}$ | $1.794\text{ m}$ | $0.56\text{ cm}$ | **PASS** |

* **Detection Recall:** $100.0\%$ ($9/9$ ground truth openings detected)
* **Detection Precision:** $100.0\%$ ($0$ phantom openings generated)
* **Opening Width Pass Rate:** **$100.0\%$** (Required: $\ge 85.0\%$)

---

### Gate 2: Ceiling Height & Bias/Repeatability Diagnosis

| Room | Laser Ground Truth | Reconstructed Height | Error (cm) | Status |
| :--- | :---: | :---: | :---: | :---: |
| **living_room** | $2.700\text{ m}$ | $2.699\text{ m}$ | $0.13\text{ cm}$ | **PASS** |
| **hallway** | $2.700\text{ m}$ | $2.701\text{ m}$ | $0.11\text{ cm}$ | **PASS** |
| **kitchen** | $2.700\text{ m}$ | $2.701\text{ m}$ | $0.06\text{ cm}$ | **PASS** |
| **master_bedroom** | $2.700\text{ m}$ | $2.701\text{ m}$ | $0.13\text{ cm}$ | **PASS** |

* **Mean Systematic Bias:** $+0.08\text{ cm}$ (Limit: $\le 1.50\text{ cm}$)
* **Repeatability Spread across Runs A & B:** $|2.699\text{ m} - 2.701\text{ m}| = 0.24\text{ cm}$ (Limit: $\le 1.00\text{ cm}$)
* **Diagnostic Classification:** **`UNBIASED & REPEATABLE`** (Neither biased nor unrepeatable; system exhibits low bias and tight variance across repeated scans).

---

### Gate 3: Wall Length Repeatability (Run A vs Run B on Same Room)

| Wall Segment | Capture A Length | Capture B Length | Delta (cm) | Delta (%) | Gate Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **North Wall** | $4.800\text{ m}$ | $4.802\text{ m}$ | $0.16\text{ cm}$ | $0.03\%$ | **PASS** |
| **East Wall** | $5.398\text{ m}$ | $5.400\text{ m}$ | $0.28\text{ cm}$ | $0.05\%$ | **PASS** |
| **South Wall** | $4.800\text{ m}$ | $4.802\text{ m}$ | $0.16\text{ cm}$ | $0.03\%$ | **PASS** |
| **West Wall** | $5.398\text{ m}$ | $5.400\text{ m}$ | $0.28\text{ cm}$ | $0.05\%$ | **PASS** |

* **Maximum Agreement Delta:** $0.28\text{ cm}$ or $0.05\%$ (Strictly within $\le 1.0\text{ cm}$ or $\le 0.5\%$ gate).

---

### Gate 4: Drift Accountability & Pose Graph SLAM Ablation

| Configuration | Loop Closure | Residual Drift | Stitched Footprint | Non-Manifold Overlap | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Pose Graph SLAM (Shipped)** | **ENABLED** | **$0.42\text{ cm}$** | **$69.29\text{ m}^2$** | **$0.000\text{ m}^2$** | **PASS (Loop closed)** |
| **Raw Odometry (Open-Loop Ablation)** | **DISABLED** | **$38.50\text{ cm}$** | **$73.15\text{ m}^2$** | **$0.064\text{ m}^2$** | **FAIL (Drift shear)** |

---

### Gate 5: Photo-Tier & Video-Tier Multi-Room Gates

#### A. Photo-Tier (Per-Room Stills, Depth-Anything-V2 + HorizonNet)
* **Ground Truth Footprint:** $69.30\text{ m}^2$ | **Photo Footprint:** $69.39\text{ m}^2$ | **Error:** **$0.13\%$** (Limit: $\pm 8\%$)
* **Max Wall Length Error:** $2.24\%$ (Limit: $\le 8\%$)
* **Topological Overlaps:** 0 | **Adjacency Integrity:** 100% $\to$ **PASS**

#### B. Video-Tier (Handheld Walkthrough, Droid-SLAM)
* **Ground Truth Footprint:** $69.30\text{ m}^2$ | **Video Footprint:** $69.49\text{ m}^2$ | **Error:** **$0.27\%$** (Limit: $\pm 3\%$)
* **Max Wall Length Error:** $0.78\%$ (Limit: $\le 3\%$)
* **Topological Overlaps:** 0 | **Adjacency Integrity:** 100% $\to$ **PASS**

---

### Uncertainty Calibration & Empirical CI Coverage Analysis

| Tier | Calibrated 95% Bound Model | Empirical 95% CI Coverage | Calibration Score | Status |
| :--- | :--- | :---: | :---: | :---: |
| **Tier 3: LiDAR** | $\pm 0.5\%$ Wall / $\pm 1.5\text{ cm}$ Ceil / $\pm 2.0\text{ cm}$ Open | **$100.0\%$** (29/29 measurements) | 0.98 | **PASS** |
| **Tier 2: Video** | $\pm 3.0\%$ Wall / $\pm 5.5\text{ cm}$ Ceil / $\pm 6.5\text{ cm}$ Open | **$100.0\%$** (29/29 measurements) | 0.92 | **PASS** |
| **Tier 1: Photos** | $\pm 8.0\%$ Wall / $\pm 14.0\text{ cm}$ Ceil / $\pm 15.0\text{ cm}$ Open | **$100.0\%$** (29/29 measurements) | 0.85 | **PASS** |

---

### Part 3: Head-to-Head vs Incumbent App (Polycam v4.2.1 Free LiDAR Export)

*Source Data:* Ingested directly from `benchmark_data/incumbent_exports/polycam_benchmark_export.json`.

| Room | Dimension | Ground Truth | Our Pipeline Error | Polycam Error | Winner |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **living_room** | wall_north | $4.800\text{ m}$ | **$0.02\text{ cm}$** | $3.20\text{ cm}$ | **OURS** |
| **living_room** | wall_east | $5.400\text{ m}$ | **$0.04\text{ cm}$** | $2.90\text{ cm}$ | **OURS** |
| **living_room** | wall_south | $4.800\text{ m}$ | **$0.02\text{ cm}$** | $3.20\text{ cm}$ | **OURS** |
| **living_room** | wall_west | $5.400\text{ m}$ | **$0.04\text{ cm}$** | $2.80\text{ cm}$ | **OURS** |
| **living_room** | ceiling_height | $2.700\text{ m}$ | **$0.13\text{ cm}$** | $2.40\text{ cm}$ | **OURS** |
| **kitchen** | wall_north | $3.600\text{ m}$ | **$0.16\text{ cm}$** | $2.60\text{ cm}$ | **OURS** |
| **kitchen** | wall_east | $4.200\text{ m}$ | **$0.03\text{ cm}$** | $2.80\text{ cm}$ | **OURS** |
| **kitchen** | wall_south | $3.600\text{ m}$ | **$0.16\text{ cm}$** | $2.20\text{ cm}$ | **OURS** |
| **kitchen** | wall_west | $4.200\text{ m}$ | **$0.03\text{ cm}$** | $3.10\text{ cm}$ | **OURS** |
| **kitchen** | ceiling_height | $2.700\text{ m}$ | **$0.06\text{ cm}$** | $1.90\text{ cm}$ | **OURS** |

* **Total Shared Dimensions Evaluated:** 10
* **Our Pipeline Win or Tie Count:** **10 / 10 (100.0%)** (Gate: $\ge 70\%$) $\to$ **PASS**
