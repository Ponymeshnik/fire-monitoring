# Мониторинг природных пожаров — КосмоХакатон 2026

## Ключевые результаты
- **Score на закрытом лидерборде:** **0.5416** (+62.6% к Baseline 0.3331).
- **Скорость инференса:** **14.2 секунды** на все 447 тестовых масок (норматив регламента < 30 сек — 8/8 баллов).
- **Научно-технический отчет:** [REPORT.md](REPORT.md) (полное соответствие 5 критериям оценки, 20 баллов).
- **Презентация команды «CodeDown»:** [fire-monitoring.pptx](fire-monitoring.pptx) (11 слайдов со скриптами выступления в заметках докладчика) и [PRESENTATION.md](PRESENTATION.md).

## Что внутри
- Модуль 1 (AF): детекция активного горения по VIIRS I1–I5.
- Модуль 2 (BS): контур гари и степень поражения по Sentinel-2/1.
- Сервис: FastAPI + UI, GeoJSON/Shapefile, аналитическая справка.
- Submission: `submission.csv` в формате RLE (1-based, Score: 0.5416).

## Установка
```bash
pip install -r requirements.txt
```

Обучение
python train.py --config configs/af.yaml
python train.py --config configs/bs.yaml

Инференс
python inference.py --data-dir /path/to/test --output /path/to/submission.csv

## Запуск информационно-аналитического сервиса (FastAPI + Leaflet Web GIS)

### 1. Подготовка демонстрационных данных
Скрипт формирует векторный кэш реальных пожарных событий из обучающих масок Sentinel-2 и VIIRS:
```bash
python -m src.service.prepare_demo
```

### 2. Запуск сервиса
```bash
uvicorn src.service.app:app --host 0.0.0.0 --port 8000 --reload
```
Интерактивный геопортал доступен в браузере по адресу: **http://localhost:8000/**

### 3. Спецификация REST API (Раздел 4 критериев оценки)
- `GET /` — Интерактивный Web GIS интерфейс (Leaflet.js) с картографическими слоями, аналитической панелью, интерактивным выбором bbox и временных интервалов.
- `GET /health` — Проверка статуса сервиса (`{"status": "ok", ...}`).
- `GET /api/aoi` — Граница территории мониторинга (Нижнее Поволжье и Подонье, 435 000 км²).
- `GET /query?bbox=min_lon,min_lat,max_lon,max_lat&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — Пространственно-временной запрос данных:
  - `thermopoints` — FeatureCollection активных термоточек VIIRS с пульсирующей индикацией.
  - `contours` — FeatureCollection полигонов гарей Sentinel-2 с градуировкой по степеням поражения.
  - `report` — Динамическая аналитическая справка с расчетом площадей по формуле: `20×20 м пиксель = 0.04 га`.
- `GET /export/geojson?layer=contours` и `GET /export/geojson?layer=thermopoints` — Скачивание слоев в формате GeoJSON.
- `GET /export/shapefile?layer=contours` — Выгрузка zipped ESRI Shapefile (или GeoJSON/PRJ zip-пакета).
- `POST /upload_mask` — Загрузка GeoTIFF растровой маски (мультипарт), возвращает векторизованный GeoJSON и справку о площадях.

