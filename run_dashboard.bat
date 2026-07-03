@echo off
title BHARAT AI FUND MANAGER GILL - LAUNCHER
color 0A
cls
echo ==========================================================
echo           BHARAT AI FUND MANAGER GILL v1.0
echo ==========================================================
echo  [SYSTEM STATS]: Launching Jarvis Option/Fund Dashboard...
echo  [INFO]: Checking and installing missing packages...
echo ==========================================================
echo.

:: Ensure dependencies are installed
python -m pip install -r requirements.txt --quiet

echo.
echo ==========================================================
echo  [SUCCESS]: Packages verified. Starting Streamlit...
echo  [INFO]: Your browser should open automatically.
echo  [INFO]: Press Ctrl+C in this window to stop the dashboard.
echo ==========================================================
echo.

:: Clear Python cache to pick up new llm_harness.py changes
if exist __pycache__ rmdir /s /q __pycache__
if exist "C:\Users\%USERNAME%\AppData\Local\Streamlit\cache" rmdir /s /q "C:\Users\%USERNAME%\AppData\Local\Streamlit\cache" 2>nul

python -m streamlit run app.py

pause
