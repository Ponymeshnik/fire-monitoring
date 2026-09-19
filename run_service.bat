@echo off
chcp 65001 > nul
echo ======================================================================
echo  ЗАПУСК СЕРВИСА МОНИТОРИНГА ПРИРОДНЫХ ПОЖАРОВ (FASTAPI + LEAFLET UI)
echo ======================================================================

set CONDA_PYTHON=C:\ProgramData\miniconda3\envs\plextract1\python.exe

if exist "%CONDA_PYTHON%" (
    echo Используется Python из conda-окружения: %CONDA_PYTHON%
    "%CONDA_PYTHON%" run_service.py
) else (
    echo Используется системный Python...
    python run_service.py
)

pause
