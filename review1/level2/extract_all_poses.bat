@echo off
echo ================================================================
echo Level-2 Pose Extraction Batch Script
echo ================================================================

REM Create poses directory
if not exist "poses" mkdir "poses"

echo.
echo [1/5] Extracting expert pose from kabaddi_clip.mp4...
python ..\..\level1_pose\pose_extract_cli.py ..\..\samples\kabaddi_clip.mp4 poses\expert_pose.npy
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to extract expert pose
    exit /b 1
)
echo DONE: Expert pose saved

echo.
echo [2/5] Extracting user_1 pose...
python ..\..\level1_pose\pose_extract_cli.py ..\..\samples\users\user_1.mp4 poses\user_1_pose.npy
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to extract user_1 pose
    exit /b 1
)
echo DONE: User 1 pose saved

echo.
echo [3/5] Extracting user_2 pose...
python ..\..\level1_pose\pose_extract_cli.py ..\..\samples\users\user_2.mp4 poses\user_2_pose.npy
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to extract user_2 pose
    exit /b 1
)
echo DONE: User 2 pose saved

echo.
echo [4/5] Extracting user_3 pose...
python ..\..\level1_pose\pose_extract_cli.py ..\..\samples\users\user_3.mp4 poses\user_3_pose.npy
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to extract user_3 pose
    exit /b 1
)
echo DONE: User 3 pose saved

echo.
echo [5/5] Extracting user_4 pose...
python ..\..\level1_pose\pose_extract_cli.py ..\..\samples\users\user_4.mp4 poses\user_4_pose.npy
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to extract user_4 pose
    exit /b 1
)
echo DONE: User 4 pose saved

echo.
echo ================================================================
echo All pose extractions complete!
echo ================================================================
dir poses\*.npy
