#!/usr/bin/env bash
# walkin.sh — Cold walk-in spatial reconstruction
# Usage: bash scripts/walkin.sh <capture_path> <tier> [output_dir]
#
# Produces: plan_output.json, floor_plan.svg, report.html
# No ground-truth files required. No network calls (weights cached by fetch_weights.py).
#
# tiers: photos | video | lidar
# capture_path: directory of room folders (photos), .mp4 (video), .ply/.obj/.json (lidar)
#
# Example:
#   bash scripts/walkin.sh /path/to/my_scans/living_room lidar output/walkin
#   bash scripts/walkin.sh /path/to/photo_folders photos output/walkin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="${PROJECT_DIR}/python.bat"

# Use system python if project wrapper not found
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

CAPTURE_PATH="${1:-}"
TIER="${2:-lidar}"
OUTPUT_DIR="${3:-${PROJECT_DIR}/output/walkin}"

if [ -z "$CAPTURE_PATH" ]; then
    echo "ERROR: capture_path required."
    echo "Usage: bash scripts/walkin.sh <capture_path> <tier> [output_dir]"
    exit 1
fi

echo "=================================================="
echo "  Spatial Reconstruction Walk-In"
echo "  Capture: $CAPTURE_PATH"
echo "  Tier:    $TIER"
echo "  Output:  $OUTPUT_DIR"
echo "=================================================="

START_TIME=$(date +%s)

cd "$PROJECT_DIR"

# Check weights (no-op if already cached)
if [ "$TIER" = "photos" ] || [ "$TIER" = "video" ]; then
    echo "[weights] Checking model weights..."
    python scripts/fetch_weights.py --list
fi

# Run pipeline
python run_pipeline.py \
    --input "$CAPTURE_PATH" \
    --tier "$TIER" \
    --output "$OUTPUT_DIR"

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "=================================================="
echo "  DONE in ${ELAPSED}s"
echo "  plan_output.json → $OUTPUT_DIR/plan_output.json"
echo "  floor_plan.svg   → $OUTPUT_DIR/floor_plan.svg"
echo "  report.html      → $OUTPUT_DIR/report.html"
echo "=================================================="
