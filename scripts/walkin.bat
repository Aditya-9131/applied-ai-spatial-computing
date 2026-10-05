@echo off
REM walkin.bat — Cold walk-in spatial reconstruction (Windows)
REM Usage: scripts\walkin.bat <capture_path> <tier> [output_dir]
REM
REM Produces: plan_output.json, floor_plan.svg, report.html
REM No ground-truth required. Network calls only for one-time weight fetch.
REM
REM tiers: photos | video | lidar
REM
REM Example:
REM   scripts\walkin.bat benchmark_data\real\living_room lidar output\walkin
REM   scripts\walkin.bat benchmark_data\real\photo_folders photos output\walkin

setlocal enabledelayedexpansion

SET CAPTURE_PATH=%~1
SET TIER=%~2
SET OUTPUT_DIR=%~3

IF "%CAPTURE_PATH%"=="" (
    echo ERROR: capture_path required.
    echo Usage: scripts\walkin.bat ^<capture_path^> ^<tier^> [output_dir]
    exit /b 1
)
IF "%TIER%"=="" SET TIER=lidar
IF "%OUTPUT_DIR%"=="" SET OUTPUT_DIR=output\walkin

SET PYTHON=C:\Users\HP\python311\python.exe
IF NOT EXIST "%PYTHON%" SET PYTHON=python

echo ==================================================
echo   Spatial Reconstruction Walk-In
echo   Capture: %CAPTURE_PATH%
echo   Tier:    %TIER%
echo   Output:  %OUTPUT_DIR%
echo ==================================================

SET STARTTIME=%TIME%

REM Check/list weights (no download if cached)
IF "%TIER%"=="photos" %PYTHON% scripts\fetch_weights.py --list
IF "%TIER%"=="video"  %PYTHON% scripts\fetch_weights.py --list

REM Run pipeline
%PYTHON% run_pipeline.py --input "%CAPTURE_PATH%" --tier %TIER% --output "%OUTPUT_DIR%"

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Pipeline failed with exit code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo ==================================================
echo   DONE
echo   plan_output.json -^> %OUTPUT_DIR%\plan_output.json
echo   floor_plan.svg   -^> %OUTPUT_DIR%\floor_plan.svg
echo   report.html      -^> %OUTPUT_DIR%\report.html
echo ==================================================
