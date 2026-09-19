@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ======================================================================
echo  ЗАПУСК СЕРВИСА МОНИТОРИНГА ПРИРОДНЫХ ПОЖАРОВ (FASTAPI + LEAFLET UI)
echo ======================================================================

set CONDA_PYTHON=C:\ProgramData\miniconda3\envs\plextract1\python.exe

if exist "%CONDA_PYTHON%" (
    echo [OK] Найдено conda-окружение: %CONDA_PYTHON%
    echo Запускаем сервер...
    "%CONDA_PYTHON%" run_service.py
) else (
    echo [INFO] Запуск через системный python...
    python run_service.py
)

echo.
echo ======================================================================
echo Сервер был остановлен или произошла ошибка.
echo ======================================================================
pause
