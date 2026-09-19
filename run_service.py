import os
import sys

if __name__ == "__main__":
    # Ensure current directory is in sys.path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    import uvicorn
    print("=" * 70)
    print(" 🔥 ЗАПУСК ИНФОРМАЦИОННО-АНАЛИТИЧЕСКОГО СЕРВИСА МОНИТОРИНГА ПОЖАРОВ")
    print("=" * 70)
    print("Веб-интерфейс (Интерактивная карта Leaflet):  http://localhost:8000")
    print("Интерактивная документация REST API (Swagger): http://localhost:8000/docs")
    print("=" * 70)
    print("Для остановки сервера нажмите Ctrl + C\n")
    
    uvicorn.run("src.service.app:app", host="0.0.0.0", port=8000, reload=True)
