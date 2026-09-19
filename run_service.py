import os
import sys

# Ensure safe UTF-8 output on Windows without detaching streams
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure current working directory is ALWAYS the project root
project_root = os.path.abspath(os.path.dirname(__file__))
os.chdir(project_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print(" >>> ЗАПУСК СЕРВИСА МОНИТОРИНГА ПРИРОДНЫХ ПОЖАРОВ <<<")
    print("=" * 70)
    print(f"Рабочая директория: {project_root}")
    print("Веб-интерфейс (Карта Leaflet):   http://localhost:8000")
    print("REST API (Swagger документация): http://localhost:8000/docs")
    print("=" * 70)
    print("Сервер готов к работе! Для остановки нажмите Ctrl + C\n")
    
    uvicorn.run("src.service.app:app", host="0.0.0.0", port=8000, reload=False, app_dir=project_root)
