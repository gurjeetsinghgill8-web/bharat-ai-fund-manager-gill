@echo off
REM ====================================================
REM  BHARAT AI FUND MANAGER GILL
REM  One-Click Windows Task Scheduler Setup
REM
REM  This script creates TWO scheduled tasks:
REM    1. Morning scan at 10:00 AM IST
REM    2. Evening scan at  4:00 PM IST
REM
REM  Run this ONCE as Administrator to set up auto-refresh.
REM  After this, data will refresh automatically forever.
REM ====================================================
TITLE Bharat AI — Task Scheduler Setup
color 0A

echo ============================================
echo  BHARAT AI FUND MANAGER GILL
echo  Automatic Task Scheduler Setup
echo ============================================
echo.
echo This will create Windows Scheduled Tasks to
echo automatically refresh stock data twice daily:
echo   - Morning: 10:00 AM
echo   - Evening:  4:00 PM
echo.
echo You need to run this as ADMINISTRATOR.
echo.
pause

REM Get the project directory
set "PROJECT_DIR=C:\Users\pc\Desktop\BHARAT-SYSTEMS\BHARAT AI FUND MANAGER GILL"

REM Delete existing tasks if they exist (clean install)
schtasks /delete /tn "BharatAI_MorningScan" /f >nul 2>&1
schtasks /delete /tn "BharatAI_EveningScan" /f >nul 2>&1

echo.
echo [1/2] Creating Morning Scan task (10:00 AM)...
schtasks /create /tn "BharatAI_MorningScan" /tr "\"%PROJECT_DIR%\auto_refresh.bat\"" /sc daily /st 10:00 /rl HIGHEST /f
if %errorlevel% neq 0 (
    echo ERROR: Failed to create morning task. Are you running as Administrator?
    pause
    exit /b 1
)
echo ✅ Morning scan scheduled at 10:00 AM daily

echo.
echo [2/2] Creating Evening Scan task (4:00 PM)...
schtasks /create /tn "BharatAI_EveningScan" /tr "\"%PROJECT_DIR%\auto_refresh.bat\"" /sc daily /st 16:00 /rl HIGHEST /f
if %errorlevel% neq 0 (
    echo ERROR: Failed to create evening task. Are you running as Administrator?
    pause
    exit /b 1
)
echo ✅ Evening scan scheduled at 4:00 PM daily

echo.
echo ============================================
echo  SETUP COMPLETE!
echo ============================================
echo.
echo Two scheduled tasks have been created:
echo   - BharatAI_MorningScan  (10:00 AM daily)
echo   - BharatAI_EveningScan  (4:00 PM daily)
echo.
echo Your stock data will now refresh automatically!
echo No need to manually open the dashboard to scan.
echo.
echo To verify, open Task Scheduler and look for
echo "BharatAI_MorningScan" and "BharatAI_EveningScan"
echo.
echo To REMOVE these tasks later, run:
echo   schtasks /delete /tn "BharatAI_MorningScan" /f
echo   schtasks /delete /tn "BharatAI_EveningScan" /f
echo.
pause
