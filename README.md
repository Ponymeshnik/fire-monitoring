# Мониторинг природных пожаров — КосмоХакатон 2026

## Что внутри
- Модуль 1 (AF): детекция активного горения по VIIRS I1–I5.
- Модуль 2 (BS): контур гари и степень поражения по Sentinel-2/1.
- Сервис: FastAPI + UI, GeoJSON/Shapefile, аналитическая справка.
- Submission: `submission.csv` в формате RLE (1-based).

## Установка
```bash
pip install -r requirements.txt
```

Обучение
python train.py --config configs/af.yaml
python train.py --config configs/bs.yaml

Инференс
python inference.py --data-dir /path/to/test --output /path/to/submission.csv

Сервис
python -m src.service.prepare_demo
uvicorn src.service.app:app --host 0.0.0.0 --port 8000

UI: http://localhost:8000/
