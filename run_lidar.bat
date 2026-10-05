@echo off
echo Running Spatial Reconstruction on LiDAR capture...
"C:\Users\HP\python311\python.exe" run_pipeline.py --input ./benchmark_data/tier3_lidar/multi_room_lidar.json --tier lidar --output ./output/lidar_scan
pause
