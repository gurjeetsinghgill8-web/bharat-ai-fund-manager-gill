@echo off
REM ====================================================
REM  BHARAT AI FUND MANAGER GILL
REM  Portfolio Daily Sync — One-Click Auto-Updater
REM
REM  This script:
REM  1. Activates Python environment
REM  2. Syncs portfolio prices
REM  3. Sends email alerts for stocks below 200 SMA
REM  4. Starts the Streamlit Dashboard
REM ====================================================
TITLE Bharat AI Portfolio Sync

echo ============================================
echo  BHARAT AI FUND MANAGER - Portfolio Sync
echo  %date% %time%
echo ============================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Make sure Python is installed.
    pause
    exit /b 1
)

echo [1/3] Installing/updating dependencies...
python -m pip install --upgrade -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Some dependencies may not have installed.
)

echo [2/3] Running portfolio sync with alert checks...
python scheduler.py --sync-portfolio
if %errorlevel% neq 0 (
    echo WARNING: Portfolio sync may have had issues.
)

echo.
echo [3/3] Starting Streamlit Dashboard...
echo The dashboard will open in your browser.
echo Auto-refreshes every 15 minutes.
echo.
echo IMPORTANT: If any stock is below 200 SMA,
echo you will hear sound alerts + see notifications!
echo.
start http://localhost:8501
python -m streamlit run app.py

echo.
echo Done!
pause
