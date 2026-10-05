# Capture Protocol
**One-page guide for non-engineers**

---

## What you need

| Item | Notes |
|---|---|
| iPhone 12 Pro or newer (with LiDAR) | Required for LiDAR tier. iPhone 12 or later (no LiDAR) works for photo/video only. |
| **3D Scanner App** (free) or **Polycam** (free tier) | For LiDAR tier. Download from App Store. |
| Apple Camera app | For photo and video tiers. |
| Tape measure or laser distance tool | For ground truth measurements. |
| Good lighting | Turn on all room lights. Open blinds. |

---

## LiDAR Capture (most accurate)

1. Open **3D Scanner App** or **Polycam**
2. Walk slowly (< 0.5 m/s) around the perimeter of each room
3. Scan all 4 walls, floor, and ceiling — point the phone at each
4. Stay 0.5–2 m from walls; avoid mirrors and glass surfaces
5. Include doorways and windows in the scan
6. Export: **3D Scanner App** → Share → Export PLY. **Polycam** → Export → Point Cloud (PLY)
7. Name files by room: `living_room.ply`, `kitchen.ply`, etc.
8. Put all PLY files in `benchmark_data/real/lidar/`

**What to avoid:** mirrors, glass shower doors, dark unlit corners, wet floors

---

## Photo Capture (per-room folders)

1. Use Apple Camera in **standard photo mode** (not portrait, not panorama)
2. Take **4–8 photos** per room from different corners and heights
3. Include at least one photo where a **full wall is visible** and one of the **ceiling**
4. Keep HEIC/JPEG format (default iPhone format is fine)
5. Create one folder per room: `benchmark_data/real/photos/living_room/`, `kitchen/`, etc.
6. Drop all photos into the correct room folder

---

## Video Capture (walkthrough)

1. Use Apple Camera in **4K 30fps video** mode
2. Walk slowly from room to room, ~0.3 m/s
3. Hold phone **landscape** at chest height
4. Pause 2 seconds when entering each new room
5. Total walkthrough: 3–5 minutes for a 3-room property
6. Save as `benchmark_data/real/video/walkthrough.mp4`

> ⚠️ Video tier geometry is currently **NOT IMPLEMENTED**. Capture the video now so it is available when the feature ships.

---

## Ground Truth Measurements

After capture, measure with tape or laser:

- Each wall length (inside face to inside face, metres)
- Ceiling height (floor to ceiling, metres)
- Door and window widths (jamb-to-jamb, metres)

Record in `benchmark_data/real/real_ground_truth.json`:

```json
{
  "rooms": {
    "living_room": {
      "walls": [
        {"wall_id": "wall_north", "length_m": 4.82},
        {"wall_id": "wall_east",  "length_m": 5.41}
      ],
      "ceiling_height_m": 2.70,
      "openings": [
        {"opening_id": "door_hallway", "width_m": 0.90}
      ]
    }
  },
  "whole_property_footprint_m2": 72.5
}
```

---

## Handing Over Files

```
benchmark_data/real/
  lidar/
    living_room.ply
    kitchen.ply
    hallway.ply
    master_bedroom.ply
  photos/
    living_room/    (4–8 .jpg files)
    kitchen/
    hallway/
    master_bedroom/
  video/
    walkthrough.mp4
  real_ground_truth.json
  polycam_export/   (Polycam PLY export for head-to-head comparison)
```

Share the `benchmark_data/real/` folder as a ZIP or via OneDrive/Google Drive.

---

## Run the pipeline (once files are in place)

```bat
# LiDAR
scripts\walkin.bat benchmark_data\real\lidar lidar output\real_lidar

# Photos
scripts\walkin.bat benchmark_data\real\photos photos output\real_photos
```
