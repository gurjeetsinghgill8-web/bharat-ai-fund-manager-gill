@echo off
REM ====================================================
REM  BHARAT AI FUND MANAGER GILL
REM  Auto-Refresh Script — For Windows Task Scheduler
REM
REM  This script is called by Windows Task Scheduler at:
REM    - 10:00 AM IST (Morning market scan)
REM    - 4:00 PM IST  (EOD closing scan)
REM
REM  It runs a full stock scan + portfolio sync, then exits.
REM  No manual intervention needed.
REM ====================================================
TITLE Bharat AI Auto-Refresh

REM Navigate to project directory
cd /d "C:\Users\pc\Desktop\BHARAT-SYSTEMS\BHARAT AI FUND MANAGER GILL"

echo ============================================
echo  BHARAT AI AUTO-REFRESH
echo  %date% %time%
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Make sure Python is installed.
    exit /b 1
)

echo [1/2] Running market schedule scan + portfolio sync...
python scheduler.py --market-schedule --universe 3000
if %errorlevel% neq 0 (
    echo WARNING: Scan may have had issues. Check logs.
)

echo.
echo [2/2] Auto-refresh complete!
echo Next run will be triggered by Windows Task Scheduler.
echo.

REM Log completion time
echo [%date% %time%] Auto-refresh completed >> auto_refresh_log.txt
