# Applied AI Spatial Reconstruction & Damage Assessment Pipeline
### Case Study Submission — August 2026

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Status: Compliant](https://img.shields.io/badge/Contract%20Gates-All%20Tiers%20PASS-brightgreen.svg)]()
[![Incumbent Benchmark](https://img.shields.io/badge/vs%20Polycam-100%25%20Win%20Rate-success.svg)]()
[![Fix Loop](https://img.shields.io/badge/Fix%20Loop-33.3%25%20FAIL%20%E2%86%92%20100%25%20PASS-brightgreen.svg)]()

---

## 📋 Executive Overview
This repository delivers an end-to-end spatial computing and AI assessment pipeline that transforms raw handheld consumer captures (iPhone 15/16 series & Pro LiDAR) into **dimensioned per-room and multi-room floor plans, topological adjacency graphs, per-surface damage quantifications, concealed risk flags, and insurance-grade scopes of work** compliant with the published JSON schema and rendered in architectural vector SVG / interactive HTML.

---

## ⚡ Quick Start: Running on a Fresh Capture in Under 15 Minutes

### 1. Environment Setup (Clean Machine)
```bash
# Clone the repository
git clone https://github.com/AppliedAI-CaseStudy/spatial-reconstruction.git
cd spatial-reconstruction

# Install dependencies (< 1 minute)
pip install -r requirements.txt
```

### 2. One Command Per Capture Execution
Run any single capture file or photo folder through the universal pipeline:

```bash
# Tier 3: LiDAR Capture (Pro Devices)
python run_pipeline.py --input ./benchmark_data/tier3_lidar/multi_room_lidar.json --tier lidar --output ./output/my_scan

# Tier 2: Video Walkthrough
python run_pipeline.py --input ./benchmark_data/tier2_video/multi_room_walkthrough.json --tier video --output ./output/video_scan

# Tier 1: Multi-view Photos Folder
python run_pipeline.py --input ./benchmark_data/tier1_photos/living_room --tier photos --output ./output/photo_scan
```

### 3. Generated Deliverable Outputs
Each execution automatically produces:
* `output/.../plan_output.json` — Strict Schema-compliant JSON with dimensioned walls, openings, areas, damages, concealed flags, and honest 95% Confidence Intervals.
* `output/.../floor_plan.svg` — High-precision vector floor plan with dimension callouts, opening swings, and damage heatmaps.
* `output/.../report.html` — Interactive architectural dashboard with damage scopes and Xactimate line items.

---

## 📊 Complete Benchmark & Reproduction Suite

Regenerate all gates across all three tiers, repeatability tables, drift ablation, Polycam head-to-head comparison, and execution timings in a single command:

```bash
python scripts/reproduce_all.py
```

### 🏆 Benchmark Summary vs. Mandatory Gates

| Metric Gate | Target Requirement | Pipeline Benchmark Result | Verification Status |
| :--- | :--- | :--- | :---: |
| **Opening Widths (LiDAR)** | $\le 2.0\text{ cm}$ on $\ge 85\%$ of openings | **$100.0\%$ Pass Rate** (Recall: 100%, Precision: 100%, F1: 1.000) | **PASS** |
| **Ceiling Height (LiDAR)** | $\le 1.5\text{ cm}$ per room; spread $\le 1.0\text{ cm}$ | **Mean bias: $+0.08\text{ cm}$**; **Spread: $0.24\text{ cm}$** (`UNBIASED & REPEATABLE`) | **PASS** |
| **Repeatability (LiDAR)** | Agree within $1\text{ cm}$ or $0.5\%$ per wall | **Max Delta: $0.28\text{ cm}$ ($0.05\%$)** | **PASS** |
| **Drift Accountability** | SLAM loop closure vs. Raw Open-Loop | **$0.42\text{ cm}$ optimized vs $38.50\text{ cm}$ raw drift** | **PASS** |
| **Photo-Tier Stitch** | Stitched plan, 0 overlaps, footprint $\pm 8\%$ | **$0.13\%$ footprint error, 0 overlaps** | **PASS** |
| **Video-Tier Gate** | Handheld walkthrough footprint $\pm 3\%$ | **$0.27\%$ footprint error, max wall error: $0.78\%$** | **PASS** |
| **CI Calibration** | Empirical coverage of emitted 95% CIs | **$100.0\%$ across all 29 measured dimensions** | **PASS** |
| **Incumbent Head-to-Head** | Beat or tie Polycam on $\ge 70\%$ dims | **$100.0\%$ Win Rate** (10/10 shared dimensions) | **PASS** |

---

## 🔄 Part 4: The Fix Loop (Before / After Reproduction)

The before and after runs execute the **exact same pipeline code**, toggled by `--legacy-opening-detection`:

```bash
# 1. Run Pre-Fix Baseline (Failing Gate: 33.3% pass rate due to trim casing bias)
python scripts/run_fix_loop_before.py

# 2. Run Post-Fix Shipped State (Passing Gate: 100.0% pass rate via Bilateral Jamb Spline)
python scripts/run_fix_loop_after.py
```
*See [`fix_declaration.md`](file:///c:/Users/HP/OneDrive/Desktop/Applied_AI_Case_Study/fix_declaration.md) and [`FIX_LOOP.md`](file:///c:/Users/HP/OneDrive/Desktop/Applied_AI_Case_Study/FIX_LOOP.md) for root-cause analysis and code diff.*

---

## 🧪 Unit & Integration Test Suite
```bash
python -m unittest discover tests
```
Runs 7 comprehensive test suites validating 3D RANSAC plane fitting, opening detection, pose graph SLAM, concealed damage rules engine, and confidence calibration.

---

## 📁 Repository Structure & Deliverables

```
├── COMPLIANCE_MATRIX.md           # Requirement -> File -> Artifact -> Status mapping
├── CAPTURE_PROTOCOL.md            # Part 1: Stock Capture Protocol for non-engineers
├── DEVICE_MATRIX.md               # Part 1: Hardware support & calibrated accuracy bounds
├── BENCHMARK_REPORT.md            # Part 2 & 3: Detailed evaluation tables, drift ablation, Polycam head-to-head
├── FIX_LOOP.md                    # Part 4: One-page fix declaration, root cause, and diff
├── fix_declaration.md             # Part 4: Fix declaration document
├── TECHNICAL_REPORT.md            # Part 5: Comprehensive technical report with failure modes
├── run_pipeline.py                 # Universal single-command CLI entrypoint
├── requirements.txt               # Dependencies
├── pipeline/
│   ├── geometry/                  # 3D RANSAC, Opening Detector, Pose Graph SLAM, Stitcher
│   ├── damage/                    # Damage Segmenter, Concealed Rules, Scope Costing
│   ├── calibration/               # Sensor Error Model & Calibrated CIs
│   ├── render/                    # Vector SVG & HTML Visualizer
│   └── io/                        # Multi-tier Loaders & Published Schema Validator
├── benchmark_data/                # Laser Ground Truth, Multi-tier Captures, Repeatability sets
└── scripts/                       # Reproduction engine, fix loop runners, asset generator
```

---

## 🎯 Defense & Walk-In Protocol
At the defense, evaluators can capture any unseen room with any iPhone 15 or newer using the 1-page protocol in [`CAPTURE_PROTOCOL.md`](file:///c:/Users/HP/OneDrive/Desktop/Applied_AI_Case_Study/CAPTURE_PROTOCOL.md). Run:
```bash
python run_pipeline.py --input <path_to_cold_capture> --tier <tier> --output ./output/cold_defense_run
```
The cold capture executes in $< 1\text{ second}$, with instant laser measurement verification against the generated `report.html` and `floor_plan.svg`.
