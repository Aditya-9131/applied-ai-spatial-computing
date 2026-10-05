@echo off
echo ===================================================
echo 1. Running Pre-Fix State (Failing Gate Demonstration)
echo ===================================================
"C:\Users\HP\python311\python.exe" scripts\run_fix_loop_before.py

echo.
echo ===================================================
echo 2. Running Post-Fix Shipped State (Passing Gate)
echo ===================================================
"C:\Users\HP\python311\python.exe" scripts\run_fix_loop_after.py
pause
