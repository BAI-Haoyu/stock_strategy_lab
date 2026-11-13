@echo off
setlocal
cd /d "%~dp0"
title Stock Strategy Lab
if exist ".venv\Scripts\python.exe" (
    set "STOCK_LAB_PYTHON=%~dp0.venv\Scripts\python.exe"
    goto run_app
)
if exist "..\..\work\.venv\Scripts\python.exe" (
    set "STOCK_LAB_PYTHON=%~dp0..\..\work\.venv\Scripts\python.exe"
    goto run_app
)
echo Creating a Python environment. Python 3.12 must be installed.
python -m venv .venv
if errorlevel 1 goto failed
set "STOCK_LAB_PYTHON=%~dp0.venv\Scripts\python.exe"
"%STOCK_LAB_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:run_app
echo Keep this window open while using the app. Press Ctrl+C to stop.
echo Local address: http://localhost:8501
"%STOCK_LAB_PYTHON%" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless false --browser.gatherUsageStats false
if errorlevel 1 goto failed
exit /b 0
:failed
echo The app could not start. Copy the error above for troubleshooting.
pause
exit /b 1
