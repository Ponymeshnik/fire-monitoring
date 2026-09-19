@echo off
cd /d "%~dp0"

echo ======================================================================
echo  STARTING FIRE MONITORING WEB SERVICE (FastAPI + Leaflet UI)
echo ======================================================================

set CONDA_PYTHON=C:\ProgramData\miniconda3\envs\plextract1\python.exe

if exist "%CONDA_PYTHON%" (
    echo [OK] Found Conda Python: %CONDA_PYTHON%
    echo Starting server on http://localhost:8000 ...
    "%CONDA_PYTHON%" run_service.py
) else (
    echo [INFO] Using system python...
    python run_service.py
)

echo.
echo ======================================================================
echo Server stopped.
echo ======================================================================
pause
