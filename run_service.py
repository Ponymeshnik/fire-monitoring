import os
import sys

# Ensure UTF-8 output in Windows consoles
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach(), errors="replace")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach(), errors="replace")

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
    print("Для остановки нажмите Ctrl + C\n")
    
    # Passing app_dir ensures uvicorn reloader and subprocesses always look in project_root
    uvicorn.run("src.service.app:app", host="0.0.0.0", port=8000, reload=True, app_dir=project_root)
