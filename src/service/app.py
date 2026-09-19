import os, io, json
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import rasterio
from rasterio.io import MemoryFile

from .vectorize import mask_to_geojson
from .report import area_report

app = FastAPI(title="Fire Monitoring Service")

INDEX_HTML = """
<!doctype html>
<html><head><meta charset="utf-8"><title>Мониторинг пожаров</title>
<style>body{font-family:sans-serif;max-width:900px;margin:2em auto}label{display:block;margin:.5em 0}
input,button{padding:.4em}pre{background:#f4f4f4;padding:1em;overflow:auto}</style></head>
<body>
<h1>Мониторинг природных пожаров</h1>
<p>Введите bbox (min_lon,min_lat,max_lon,max_lat) и интервал дат.</p>
<label>bbox <input id="bbox" value="38.3,47.1,48.0,52.3"></label>
<label>date_from <input id="df" value="2025-04-01"></label>
<label>date_to <input id="dt" value="2025-10-31"></label>
<button onclick="run()">Запустить</button>
<h3>Термоточки</h3><pre id="tp">—</pre>
<h3>Контуры гари</h3><pre id="cont">—</pre>
<h3>Аналитическая справка</h3><pre id="rep">—</pre>
<script>
async function run(){
  const bbox=document.getElementById('bbox').value;
  const df=document.getElementById('df').value;
  const dt=document.getElementById('dt').value;
  const r=await fetch(`/query?bbox=${bbox}&date_from=${df}&date_to=${dt}`);
  const j=await r.json();
  document.getElementById('tp').textContent=JSON.stringify(j.thermopoints,null,2);
  document.getElementById('cont').textContent=JSON.stringify(j.contours,null,2);
  document.getElementById('rep').textContent=JSON.stringify(j.report,null,2);
}
</script>
</body></html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/query")
def query(bbox: str = Query(...), date_from: str = Query(...), date_to: str = Query(...)):
    """
    bbox: 'min_lon,min_lat,max_lon,max_lat'
    Возвращает: thermopoints (GeoJSON), contours (GeoJSON), report (JSON).
    Демо-версия: читает заранее подготовленные маски из ./demo_cache.
    """
    cache = os.path.join(os.path.dirname(__file__), "..", "..", "demo_cache")
    tp_path = os.path.join(cache, "thermopoints.geojson")
    cont_path = os.path.join(cache, "contours.geojson")
    rep_path = os.path.join(cache, "report.json")
    if not (os.path.exists(tp_path) and os.path.exists(cont_path)):
        raise HTTPException(503, "Demo cache not ready. Run prepare_demo.py")
    return JSONResponse({
        "thermopoints": json.load(open(tp_path, encoding="utf-8")),
        "contours": json.load(open(cont_path, encoding="utf-8")),
        "report": json.load(open(rep_path, encoding="utf-8")),
    })

@app.post("/upload_mask")
async def upload_mask(file: UploadFile = File(...), gsd: float = 20.0):
    content = await file.read()
    with MemoryFile(content) as mem:
        with mem.open() as src:
            mask = src.read(1)
            transform = src.transform
    geojson = mask_to_geojson(mask, transform)
    report = area_report(mask, gsd)
    return {"contours": geojson, "report": report}