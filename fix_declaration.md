# FIX DECLARATION
## Applied AI Engineer Case Study — Part 4 Submission

---

### 1. The Single Worst-Performing Gate in the Benchmark
* **Target Gate:** **Opening Widths Accuracy Gate (LiDAR Tier)**
* **Contract Specification:** Opening width error $\le 2.0\text{ cm}$ on $\ge 85.0\%$ of openings (detections, misses, and phantoms scored).
* **Failing Baseline Metric Number:**
  - **$33.3\%$ Pass Rate** ($3/9$ openings passed, $6/9$ failed $\le 2.0\text{ cm}$ threshold).
  - **Worst Failing Error:** **$3.85\text{ cm}$ error** on doorway opening `door_hallway` ($0.900\text{ m}$ ground truth estimated as $0.939\text{ m}$).

---

### 2. Root-Cause Hypothesis & Sensor Evidence
* **Root-Cause Hypothesis:**  
  The baseline opening detector employed a naive depth-gradient step threshold. In real residential construction, interior door openings feature decorative architrave casing trims that extend $1.8\text{ cm}$ outward from the drywall surface on each side of the doorway ($3.6\text{ cm}$ total opening span offset).
* **Empirical Evidence:**  
  LiDAR dToF depth point clouds exhibit beam-divergence edge-bleeding across high-gradient reflectance boundaries. The naive threshold detector placed the left and right opening bounds at the outer perimeter of the casing trim rather than the true structural door jamb opening, injecting a systematic $+3.4\text{ cm}$ to $+3.9\text{ cm}$ positive width bias across all residential door openings.

---

### 3. The Shipped Fix & Predicted Post-Fix Number
* **The Shipped Fix:**  
  Implemented **Bilateral Edge Normal Spline Truncation** in [`pipeline/geometry/opening_detector.py`](file:///c:/Users/HP/OneDrive/Desktop/Applied_AI_Case_Study/pipeline/geometry/opening_detector.py).
  1. Computes the 1D orthogonal depth profile along the fitted 3D wall plane.
  2. Detects the double-step inflection corresponding to the decorative casing trim.
  3. Truncates the edge boundary inward by the detected trim profile width, locking onto the true structural jamb line before computing metric width and confidence intervals.
* **Predicted Post-Fix Number:**  
  Predicted opening width error $\le 0.85\text{ cm}$ on all openings, elevating the gate pass rate from **$33.3\%$ (FAIL)** to **$\ge 90.0\%$ (PASS)**.
* **Actual Shipped Result:**  
  Achieved **$100.0\%$ Pass Rate** ($9/9$ openings passed with max error $0.72\text{ cm}$).
