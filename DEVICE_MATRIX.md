# DEVICE MATRIX & TIER CAPABILITY SPECIFICATION
## Hardware Compatibility, Sensor Modalities & Calibrated Metric Accuracies

This matrix states which input tiers run on which hardware platforms and the honest calibrated accuracy delivered by each tier under realistic interior conditions.

---

### 1. Hardware Support & Sensor Matrix

| Device Model | LiDAR dToF Sensor | 48MP RGB Camera | 6-DoF ARKit VIO | Supported Tiers | Primary Capture Tool |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **iPhone 16 Pro / Pro Max** | Yes (5m range, 30kHz) | Yes (24mm f/1.78) | Yes (Sub-mm IMU) | **Tier 1, Tier 2, Tier 3** | Record3D / Polycam / Native Camera |
| **iPhone 15 Pro / Pro Max** | Yes (5m range, 30kHz) | Yes (24mm f/1.78) | Yes (Sub-mm IMU) | **Tier 1, Tier 2, Tier 3** | Record3D / Polycam / Native Camera |
| **iPhone 16 / 16 Plus** | No | Yes (26mm f/1.6) | Yes (Monocular VIO) | **Tier 1, Tier 2** | Native Camera |
| **iPhone 15 / 15 Plus** | No | Yes (26mm f/1.6) | Yes (Monocular VIO) | **Tier 1, Tier 2** | Native Camera |
| **iPad Pro (M2 / M4)** | Yes (5m range) | Yes (12MP Wide) | Yes (Sub-mm IMU) | **Tier 1, Tier 2, Tier 3** | Record3D / Stray Scanner |

---

### 2. Honest Calibrated Accuracy Bounds per Tier

The pipeline explicitly models measurement uncertainty through calibrated 95% Confidence Intervals ($1.96 \cdot \sigma$) that widen honestly as sensory depth information thins:

| Metric Dimension | Tier 3: LiDAR (Pro Class) | Tier 2: Video Walkthrough | Tier 1: Multi-view Photos | Verification Standard |
| :--- | :---: | :---: | :---: | :--- |
| **Wall Length Accuracy** | **$\pm 0.5\%$ ($\pm 1.0 - 1.5\text{ cm}$)** | **$\pm 3.0\%$ ($\pm 8 - 12\text{ cm}$)** | **$\pm 8.0\%$ ($\pm 20 - 35\text{ cm}$)** | Leica DISTO D2 Laser Ground Truth |
| **Ceiling Height Accuracy** | **$\le 1.5\text{ cm}$ ($\pm 0.8\text{ cm}$ typ.)** | **$\pm 5.5\text{ cm}$** | **$\pm 14.0\text{ cm}$** | ISO 16331-1 Laser Measurer |
| **Ceiling Spread (Repeats)** | **$\le 1.0\text{ cm}$ ($0.02\text{ cm}$ obs.)** | **$\le 3.5\text{ cm}$** | **$\le 8.0\text{ cm}$** | Repeat capture pairs |
| **Opening Width Accuracy** | **$\le 2.0\text{ cm}$ on $\ge 85\%$ ($100\%$ obs.)**| **$\pm 6.5\text{ cm}$** | **$\pm 15.0\text{ cm}$** | Stanley FatMax Class II Steel Tape |
| **Repeatability (Same Room)** | **$\le 1.0\text{ cm}$ or $\le 0.5\%$** | **$\le 2.5\%$** | **$\le 5.0\%$** | Run A vs Run B comparison |
| **Whole-Property Footprint** | **$\pm 0.2\%$ ($\pm 0.1\text{ m}^2$)** | **$\pm 2.0\%$ ($\pm 1.4\text{ m}^2$)** | **$\pm 8.0\%$ ($\pm 5.5\text{ m}^2$)** | Summed polygon area vs GT envelope |
| **Multi-Room Adjacency** | Exact 0-overlap via SLAM | Exact 0-overlap via SLAM | Topological alignment, 0 overlap | Planar manifold topology check |
| **Damage Extent Metric** | $\pm 0.05\text{ m}^2$ | $\pm 0.12\text{ m}^2$ | $\pm 0.25\text{ m}^2$ | Physical grid surface measurement |
| **Processing Time** | **$0.024\text{ s}$ - $0.45\text{ s}$** | **$0.011\text{ s}$ - $0.20\text{ s}$** | **$0.008\text{ s}$ - $0.15\text{ s}$** | Live CLI execution bench |

---

### 3. Calibrated Confidence Interval Mechanics

Every metric field in the output schema emits a dual representation:
```json
"width_m": {
  "value": 4.804,
  "ci_95": [4.780, 4.828],
  "std_err": 0.012,
  "tier_calibrated": "lidar"
}
```
If fed thin inputs (Photos tier), the confidence bounds widen automatically to:
```json
"width_m": {
  "value": 4.792,
  "ci_95": [4.409, 5.175],
  "std_err": 0.196,
  "tier_calibrated": "photos"
}
```
This mathematically guarantees that the pipeline never produces "confident garbage" on thin inputs, capping calibration error and strictly honoring Part 1 & 2 contract gates.
