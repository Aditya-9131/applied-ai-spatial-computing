# STOCK CAPTURE PROTOCOL (ROUTE 2)
## Standard Operating Procedure for Property Scanning & Spatial Assessment
**Audience:** Field Technicians, Adjusters, Homeowners & Defense Evaluators (Zero Engineering Background Required)  
**Setup Time:** Under 5 minutes | **Capture Time:** 2 to 4 minutes per room

---

### 1. Application Installation
Install **one** of the following free App Store tools based on the capture tier assigned:
* **Tier 3 (LiDAR - Recommended for iPhone Pro models):**  
  Install **Record3D** or **Polycam** (Free LiDAR Mode) or **Stray Scanner** from Apple App Store.  
  *Direct App Store Link:* Search `"Record3D - 3D Video & LiDAR"` (Developer: Filip Horinek).
* **Tier 2 (Handheld Video) & Tier 1 (Photos - All iPhone 15 & newer models):**  
  Use the **Native iOS Camera App** (pre-installed, zero install time).

---

### 2. Physical Walkthrough Protocol

#### A. LiDAR Walkthrough (Tier 3)
1. **Starting Point:** Stand at the primary entrance threshold of Room 1 facing inward.
2. **Device Grip:** Hold phone at chest level (approx. 1.3m to 1.5m height), tilted slightly downward (15° pitch).
3. **Motion Pattern:**
   - Walk slowly in a smooth **perimeter loop** around the room clockwise at **0.5 meters per second** (normal slow walking pace).
   - Keep the device moving continuously; avoid abrupt jerky rotations.
   - Ensure the camera sweeps across wall-floor junctions, door frames, windows, and ceiling boundaries.
4. **Transition to Adjacent Rooms:**
   - Walk through the connector doorway holding the phone forward.
   - Scan the connector hallway, then enter Room 2, maintaining the continuous logging stream.
   - Complete a closed loop by returning to the starting entrance point.
5. **Capture Duration:** 60 to 90 seconds per room (3 to 5 minutes total for a multi-room property).

#### B. Handheld Video Walkthrough (Tier 2)
1. Set Native iOS Camera to **Video Mode → 4K at 60 fps**. Enable *Action Mode* / *Enhanced Stabilization* in Settings.
2. Walk the same continuous perimeter loop as described above. Ensure smooth sweeping transitions through doorways.
3. Capture Duration: 45 to 60 seconds per room.

#### C. Still Photos (Tier 1)
1. Stand near the doorway and corners of the room.
2. Take **4 to 8 photos per room** using the 1x Main Lens (24mm):
   - **Shot 1 & 2:** Wide shots looking into opposite corners (capturing wall-floor-ceiling intersections).
   - **Shot 3 & 4:** Straight-on elevation shots of primary walls with openings (doors/windows).
   - **Shot 5 & 6:** Oblique shots capturing damage regions and connecting doorways.
3. Save each room's photos into a named folder (e.g., `living_room/`, `kitchen/`, `hallway/`).

---

### 3. What to Avoid (Critical Field Rules)
* ❌ **Do NOT walk backwards or make rapid 360° spins** (causes visual odometry tracking loss).
* ❌ **Do NOT cover the LiDAR sensor lens** located in the bottom camera glass cluster.
* ❌ **Do NOT walk in total darkness** — turn on standard room lighting or open blinds.
* ❌ **Avoid pointing purely at blank featureless ceilings or flat white floors** for extended periods. Keep 60% of frame focused on wall structures.
* ❌ **Do NOT omit connecting doorways** — hold the device steady for 2 seconds while crossing thresholds.

---

### 4. File Hand-off to Pipeline
1. Connect iPhone to computer via USB-C cable or AirDrop/File Share.
2. Export the capture file or folder to the project input directory:
   - For **LiDAR (Tier 3):** Export the `.json` or `.r3d` session folder from Record3D / Polycam.
   - For **Video (Tier 2):** Copy the `.mov` / `.mp4` video file.
   - For **Photos (Tier 1):** Copy the per-room folders containing `.jpg` / `.heic` stills.
3. Run the single execution command:
   ```bash
   python run_pipeline.py --input ./benchmark_data/tier3_lidar/multi_room_lidar.json --tier lidar --output ./output/my_scan
   ```
4. View the generated `report.html` and `floor_plan.svg` in your browser.
