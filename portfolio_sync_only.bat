@echo off
REM ====================================================
REM  BHARAT AI FUND MANAGER GILL
REM  Quick Portfolio Sync Only (No Dashboard)
REM
REM  Use this for a silent background sync via
REM  Windows Task Scheduler or manual double-click.
REM ====================================================
TITLE Bharat AI Quick Portfolio Sync

echo [%date% %time%] Starting portfolio sync...
python scheduler.py --sync-portfolio
echo [%date% %time%] Portfolio sync complete.
echo.
