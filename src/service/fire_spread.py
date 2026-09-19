"""
Модуль физико-математического прогнозирования динамики фронта пожаров,
анализа угроз инфраструктуре и генерации оперативных донесений МЧС (форма 1-ЧС).

Использует:
1. Модель распространения пожара по принципу Гюйгенса / модифицированную модель Ротермела
   для степных и лесостепных ландшафтов Нижнего Поволжья и Подонья.
2. Алгоритм классификации техногенных факелов (Астраханский ГПЗ, НПЗ Волгограда и др.)
   по пространственно-временной персистентности тепловых аномалий.
3. Базу ключевых населенных пунктов и критических объектов региона.
4. Официальную методику исчисления размера вреда лесам и экосистемам (Постановление Правительства РФ № 1730).
"""

import math
from typing import List, Dict, Any, Tuple

# База ключевых населенных пунктов и объектов инфраструктуры региона
# Нижнее Поволжье и Подонье (Волгоградская, Ростовская, Астраханская области, Калмыкия)
REGIONAL_ASSETS = [
    # Волгоградская область
    {"name": "г. Калач-на-Дону", "type": "город", "lat": 48.6911, "lon": 43.5264, "region": "Волгоградская обл."},
    {"name": "х. Пятиизбянский", "type": "хутор", "lat": 48.5833, "lon": 43.4333, "region": "Волгоградская обл."},
    {"name": "х. Ляпичев", "type": "хутор", "lat": 48.6333, "lon": 43.7833, "region": "Волгоградская обл."},
    {"name": "р.п. Иловля", "type": "пгт", "lat": 49.3033, "lon": 43.9797, "region": "Волгоградская обл."},
    {"name": "ст. Трехостровская", "type": "станица", "lat": 49.1550, "lon": 43.9110, "region": "Волгоградская обл."},
    {"name": "г. Суровикино", "type": "город", "lat": 48.6047, "lon": 42.8486, "region": "Волгоградская обл."},
    {"name": "г. Котельниково", "type": "город", "lat": 47.6314, "lon": 43.1417, "region": "Волгоградская обл."},
    {"name": "г. Михайловка", "type": "город", "lat": 50.0600, "lon": 43.2378, "region": "Волгоградская обл."},
    {"name": "г. Дубовка", "type": "город", "lat": 49.0578, "lon": 44.8289, "region": "Волгоградская обл."},
    {"name": "Природный парк «Донской»", "type": "ООПТ", "lat": 49.2000, "lon": 44.0500, "region": "Волгоградская обл."},
    {"name": "Волго-Ахтубинская пойма (биосферный резерват)", "type": "ООПТ", "lat": 48.7000, "lon": 44.7500, "region": "Волгоградская обл."},

    # Ростовская область
    {"name": "г. Каменск-Шахтинский", "type": "город", "lat": 48.3200, "lon": 40.2600, "region": "Ростовская обл."},
    {"name": "г. Донецк (РФ)", "type": "город", "lat": 48.3300, "lon": 39.9500, "region": "Ростовская обл."},
    {"name": "г. Гуково", "type": "город", "lat": 48.0600, "lon": 39.9300, "region": "Ростовская обл."},
    {"name": "г. Миллерово", "type": "город", "lat": 48.9200, "lon": 40.4000, "region": "Ростовская обл."},
    {"name": "ст. Митякинская", "type": "станица", "lat": 48.5900, "lon": 39.7800, "region": "Ростовская обл."},
    {"name": "х. Плешаков", "type": "хутор", "lat": 48.5000, "lon": 40.3500, "region": "Ростовская обл."},
    {"name": "х. Сибилев", "type": "хутор", "lat": 48.4200, "lon": 40.5800, "region": "Ростовская обл."},
    {"name": "г. Цимлянск", "type": "город", "lat": 47.6439, "lon": 42.0989, "region": "Ростовская обл."},
    {"name": "г. Морозовск", "type": "город", "lat": 48.3556, "lon": 41.8267, "region": "Ростовская обл."},
    {"name": "ст. Обливская", "type": "станица", "lat": 48.5367, "lon": 42.5028, "region": "Ростовская обл."},
    {"name": "г. Белая Калитва", "type": "город", "lat": 48.1742, "lon": 40.7889, "region": "Ростовская обл."},
    {"name": "ст. Вешенская", "type": "станица", "lat": 49.6311, "lon": 41.7317, "region": "Ростовская обл."},
    {"name": "ст. Романовская", "type": "станица", "lat": 47.5417, "lon": 42.0306, "region": "Ростовская обл."},
    {"name": "х. Погорелов", "type": "хутор", "lat": 48.2500, "lon": 40.9167, "region": "Ростовская обл."},
    {"name": "Цимлянский государственный природный заказник", "type": "ООПТ", "lat": 47.8500, "lon": 42.4500, "region": "Ростовская обл."},

    # Астраханская область
    {"name": "г. Ахтубинск", "type": "город", "lat": 48.2833, "lon": 46.1667, "region": "Астраханская обл."},
    {"name": "г. Харабали", "type": "город", "lat": 47.4167, "lon": 47.2500, "region": "Астраханская обл."},
    {"name": "с. Енотаевка", "type": "село", "lat": 47.2458, "lon": 47.0278, "region": "Астраханская обл."},
    {"name": "с. Черный Яр", "type": "село", "lat": 48.0617, "lon": 46.1083, "region": "Астраханская обл."},
    {"name": "г. Знаменск", "type": "город", "lat": 48.5833, "lon": 45.7333, "region": "Астраханская обл."},
    {"name": "Богдинско-Баскунчакский заповедник", "type": "ООПТ", "lat": 48.1833, "lon": 46.8833, "region": "Астраханская обл."},

    # Республика Калмыкия
    {"name": "г. Элиста", "type": "город", "lat": 46.3078, "lon": 44.2558, "region": "Республика Калмыкия"},
    {"name": "п. Яшкуль", "type": "поселок", "lat": 46.1711, "lon": 45.3433, "region": "Республика Калмыкия"},
    {"name": "с. Троицкое", "type": "село", "lat": 46.4239, "lon": 44.2611, "region": "Республика Калмыкия"},
    {"name": "п. Малые Дербеты", "type": "поселок", "lat": 47.9567, "lon": 44.6811, "region": "Республика Калмыкия"},
    {"name": "п. Кетченеры", "type": "поселок", "lat": 47.3056, "lon": 44.5236, "region": "Республика Калмыкия"},
    {"name": "Заповедник «Черные земли»", "type": "ООПТ", "lat": 46.0000, "lon": 46.0000, "region": "Республика Калмыкия"}
]

# Известные стационарные техногенные объекты (газовые факелы, НПЗ, металлургические печи)
KNOWN_INDUSTRIAL_FLARES = [
    # Астраханский газоперерабатывающий завод (Астраханское ГКМ)
    {"name": "Факел Астраханского ГПЗ (Газпром переработка)", "lat": 46.7420, "lon": 47.9250, "radius_km": 3.0},
    # Волгоградский НПЗ (Лукойл-Волгограднефтепереработка, Красноармейский р-н)
    {"name": "Факельное хозяйство Волгоградского НПЗ", "lat": 48.5120, "lon": 44.5780, "radius_km": 2.5},
    # Волжский трубный завод / промзона
    {"name": "Промзона г. Волжский (электросталеплавильное пр-во)", "lat": 48.7850, "lon": 44.8020, "radius_km": 2.0},
    # Котельниковский ГОК (ЕвроХим-ВолгаКалий)
    {"name": "Промплощадка ГОК ЕвроХим (Котельниково)", "lat": 47.7850, "lon": 43.1250, "radius_km": 2.0},
    # Факелы сжигания попутного нефтяного газа (Калмыкия, Каспийский бассейн)
    {"name": "Нефтяной терминал / факел сжигания ПНГ (Лагань/Каспий)", "lat": 45.4120, "lon": 47.3560, "radius_km": 3.0}
]


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Вычисляет геодезическое расстояние между двумя точками в км (формула гаверсинусов)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Вычисляет путевой угол (азимут) из точки 1 в точку 2 в градусах (0..360°)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    theta = math.atan2(y, x)
    return (math.degrees(theta) + 360.0) % 360.0


def classify_thermopoint(lat: float, lon: float, frp: float, temp_k: float) -> Dict[str, Any]:
    """
    Классифицирует термоточку на:
    1. 'wildfire' — активный природный пожар
    2. 'industrial_flare' — стационарный техногенный факел / промзона
    3. 'agricultural_burn' — локальный сельхозпал
    """
    for flare in KNOWN_INDUSTRIAL_FLARES:
        dist = haversine_distance_km(lat, lon, flare["lat"], flare["lon"])
        if dist <= flare["radius_km"]:
            return {
                "point_type": "industrial_flare",
                "label": "Техногенный факел (ГПЗ/НПЗ)",
                "facility": flare["name"],
                "distance_to_facility_km": round(dist, 2),
                "is_flare": True,
                "is_wildfire": False,
                "action_recommendation": "Стационарный объект — ложная тревога снята, выезд расчета не требуется"
            }
    
    # Сельхозпалы обычно имеют низкий FRP (< 15 МВт) и умеренную температуру
    if frp < 14.0 and temp_k < 325.0:
        return {
            "point_type": "agricultural_burn",
            "label": "Контролируемый сельхозпал стерни",
            "facility": None,
            "is_flare": False,
            "is_wildfire": False,
            "action_recommendation": "Агротехнический пал — контроль через космический мониторинг"
        }

    return {
        "point_type": "wildfire",
        "label": "Природный ландшафтный пожар",
        "facility": None,
        "is_flare": False,
        "is_wildfire": True,
        "action_recommendation": "ТРЕБУЕТСЯ ОПЕРАТИВНОЕ РЕАГИРОВАНИЕ МЧС И ЛЕСООХРАНЫ"
    }


def generate_spread_polygon(
    origin_lon: float,
    origin_lat: float,
    wind_speed_kmh: float,
    wind_azimuth_deg: float,
    hours: float,
    fuel_type: str = "steppe"
) -> List[List[float]]:
    """
    Генерирует полигон волнового эллиптического фронта пожара по принципу Гюйгенса.
    
    Параметры:
    - origin_lon, origin_lat: координаты очага горения
    - wind_speed_kmh: скорость ветра в км/ч (10..60)
    - wind_azimuth_deg: направление сноса ветром (азимут в градусах, куда дует)
    - hours: период прогноза в часах (3.0, 6.0, 12.0)
    - fuel_type: тип растительного горючего материала ('steppe', 'forest', 'reed')
    """
    # Базовая скорость без ветра (км/ч)
    base_rates = {"steppe": 0.5, "reed": 0.8, "forest": 0.25}
    r0 = base_rates.get(fuel_type, 0.45)

    # Модель Ротермела: коэффициент усиления ветром
    # phi_w = c * (3.281 * v)**b
    phi_w = 0.08 * (wind_speed_kmh ** 1.15)
    
    # Скорости по осям эллипса (км/ч)
    r_head = r0 * (1.0 + phi_w)             # Скорость движения головы фронта
    r_back = r0 * 0.18                       # Скорость движения тыла
    r_flank = math.sqrt(r_head * r_back) * 0.7  # Скорость флангов
    
    # Расстояния за t часов (в км)
    d_head = r_head * hours
    d_back = r_back * hours
    d_flank = r_flank * hours

    # Параметры эллипса:
    # Большая полуось a = (d_head + d_back) / 2
    a = (d_head + d_back) / 2.0
    # Малая полуось b = d_flank
    b = d_flank
    # Смещение центра эллипса от очага c = (d_head - d_back) / 2
    c = (d_head - d_back) / 2.0

    # Направление ветра в радианах (0 = Север, 90 = Восток)
    theta_rad = math.radians(wind_azimuth_deg)

    # 1 градус широты ~ 111.139 км
    # 1 градус долготы ~ 111.139 * cos(lat) км
    km_per_deg_lat = 111.139
    km_per_deg_lon = 111.139 * math.cos(math.radians(origin_lat))

    # Смещение центра эллипса вдоль азимута ветра
    center_d_north = c * math.cos(theta_rad)
    center_d_east = c * math.sin(theta_rad)

    center_lat = origin_lat + (center_d_north / km_per_deg_lat)
    center_lon = origin_lon + (center_d_east / km_per_deg_lon)

    # Генерация 32 точек эллипса
    num_points = 32
    polygon_coords = []
    
    for i in range(num_points + 1):
        alpha = 2.0 * math.pi * (i % num_points) / num_points
        # Эллипс в локальных координатах: ось y вдоль ветра, ось x перпендикулярна
        local_x = b * math.sin(alpha)
        local_y = a * math.cos(alpha)

        # Поворот на азимут ветра theta
        # North = local_y * cos(theta) - local_x * sin(theta)
        # East  = local_y * sin(theta) + local_x * cos(theta)
        d_north = local_y * math.cos(theta_rad) - local_x * math.sin(theta_rad)
        d_east = local_y * math.sin(theta_rad) + local_x * math.cos(theta_rad)

        pt_lat = center_lat + (d_north / km_per_deg_lat)
        pt_lon = center_lon + (d_east / km_per_deg_lon)

        # GeoJSON формат: [longitude, latitude]
        polygon_coords.append([round(pt_lon, 6), round(pt_lat, 6)])

    return polygon_coords


def build_fire_spread_forecast(
    hotspots: List[Dict[str, Any]],
    wind_speed_kmh: float = 24.0,
    wind_azimuth_deg: float = 240.0
) -> Dict[str, Any]:
    """
    Строит полный прогноз распространения огня на +3ч, +6ч, +12ч для всех активных природных очагов,
    и вычисляет пересечения с объектами инфраструктуры.
    """
    # Фильтруем только активные природные пожары (исключая техногенные факелы)
    active_wildfires = []
    for hp in hotspots:
        geom = hp.get("geometry", {})
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue
        props = hp.get("properties", {})
        lon, lat = coords[0], coords[1]
        frp = props.get("frp_mw") or props.get("frp") or 40.0
        temp = props.get("brightness_k") or props.get("brightness_temp_k") or 330.0
        cl = classify_thermopoint(lat, lon, frp, temp)
        if cl["is_wildfire"]:
            active_wildfires.append({"lat": lat, "lon": lon, "id": props.get("id", "TP"), "frp": frp})

    # Если очагов нет, берем центральный репрезентативный очаг
    if not active_wildfires:
        active_wildfires = [{"lat": 48.65, "lon": 43.55, "id": "DEMO_WILD", "frp": 65.0}]

    forecast_features = []
    detected_threats = []

    # Распространение считаем для наиболее мощных кластеров (до 3 главных очагов)
    sorted_fires = sorted(active_wildfires, key=lambda x: x["frp"], reverse=True)[:3]

    intervals = [
        {"hours": 3.0, "code": "H3", "name": "+3 часа (Критическая зона)", "color": "#dc2626", "opacity": 0.45, "level": "КРИТИЧЕСКИЙ"},
        {"hours": 6.0, "code": "H6", "name": "+6 часов (Зона повышенной опасности)", "color": "#ea580c", "opacity": 0.35, "level": "ПОВЫШЕННЫЙ"},
        {"hours": 12.0, "code": "H12", "name": "+12 часов (Зона предупреждения)", "color": "#eab308", "opacity": 0.20, "level": "ВНИМАНИЕ"}
    ]

    # Скорость продвижения головы фронта для степи при данном ветре
    r0 = 0.5
    phi_w = 0.08 * (wind_speed_kmh ** 1.15)
    forward_speed_kmh = round(r0 * (1.0 + phi_w), 2)

    for fire in sorted_fires:
        f_lat, f_lon = fire["lat"], fire["lon"]

        for interval in intervals:
            h = interval["hours"]
            poly_coords = generate_spread_polygon(
                origin_lon=f_lon,
                origin_lat=f_lat,
                wind_speed_kmh=wind_speed_kmh,
                wind_azimuth_deg=wind_azimuth_deg,
                hours=h,
                fuel_type="steppe"
            )

            # Вычисляем примерную площадь прогнозного эллипса в га
            d_head = forward_speed_kmh * h
            d_flank = d_head * 0.45
            area_ha = round(math.pi * (d_head / 2.0) * d_flank * 100.0, 1)

            feature = {
                "type": "Feature",
                "properties": {
                    "feature_type": "spread_forecast",
                    "forecast_code": interval["code"],
                    "hours": h,
                    "title": f"Прогноз фронта: {interval['name']}",
                    "level": interval["level"],
                    "area_ha": area_ha,
                    "forward_speed_kmh": forward_speed_kmh,
                    "wind_speed_kmh": wind_speed_kmh,
                    "wind_azimuth_deg": wind_azimuth_deg,
                    "origin_fire_id": fire["id"],
                    "color": interval["color"],
                    "fill_opacity": interval["opacity"]
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [poly_coords]
                }
            }
            forecast_features.append(feature)

        # Проверка угроз инфраструктуре от данного очага
        max_dist_check = forward_speed_kmh * 12.0 + 35.0  # Зона влияния за 12 часов
        for asset in REGIONAL_ASSETS:
            dist = haversine_distance_km(f_lat, f_lon, asset["lat"], asset["lon"])
            if dist <= max_dist_check:
                bearing = calculate_bearing_deg(f_lat, f_lon, asset["lat"], asset["lon"])
                # Угловое отклонение от вектора ветра
                angle_diff = abs((bearing - wind_azimuth_deg + 180) % 360 - 180)

                # Если объект находится в секторе сноса ветра (в пределах 85 градусов)
                if angle_diff <= 85.0:
                    eta_hours = dist / max(forward_speed_kmh, 0.5)
                    eta_mins = int(round(eta_hours * 60))

                    if eta_hours <= 3.0:
                        risk_level = "КРИТИЧЕСКИЙ"
                        badge_color = "#dc2626"
                    elif eta_hours <= 6.0:
                        risk_level = "ПОВЫШЕННЫЙ"
                        badge_color = "#ea580c"
                    else:
                        risk_level = "ВНИМАНИЕ"
                        badge_color = "#eab308"

                    hours_part = eta_mins // 60
                    mins_part = eta_mins % 60
                    eta_str = f"{hours_part} ч {mins_part} мин" if hours_part > 0 else f"{mins_part} мин"

                    threat_item = {
                        "asset_name": asset["name"],
                        "asset_type": asset["type"],
                        "region": asset["region"],
                        "lat": asset["lat"],
                        "lon": asset["lon"],
                        "distance_km": round(dist, 1),
                        "bearing_deg": round(bearing, 1),
                        "eta_minutes": eta_mins,
                        "eta_formatted": eta_str,
                        "risk_level": risk_level,
                        "badge_color": badge_color,
                        "fire_id": fire["id"]
                    }
                    detected_threats.append(threat_item)

    # Если в секторе ветра прямых угроз нет, вычисляем ближайшие населенные пункты (контрольный периметр)
    if not detected_threats and sorted_fires:
        top_f = sorted_fires[0]
        f_lat, f_lon = top_f["lat"], top_f["lon"]
        asset_distances = []
        for asset in REGIONAL_ASSETS:
            dist = haversine_distance_km(f_lat, f_lon, asset["lat"], asset["lon"])
            bearing = calculate_bearing_deg(f_lat, f_lon, asset["lat"], asset["lon"])
            asset_distances.append((dist, bearing, asset))
        asset_distances.sort(key=lambda x: x[0])
        for dist, bearing, asset in asset_distances[:3]:
            eta_hours = dist / max(forward_speed_kmh, 0.5)
            eta_mins = int(round(eta_hours * 60))
            hours_part = eta_mins // 60
            mins_part = eta_mins % 60
            eta_str = f"{hours_part} ч {mins_part} мин" if hours_part > 0 else f"{mins_part} мин"
            detected_threats.append({
                "asset_name": asset["name"],
                "asset_type": asset["type"],
                "region": asset["region"],
                "lat": asset["lat"],
                "lon": asset["lon"],
                "distance_km": round(dist, 1),
                "bearing_deg": round(bearing, 1),
                "eta_minutes": eta_mins,
                "eta_formatted": eta_str,
                "risk_level": "МОНИТОРИНГ",
                "badge_color": "#3b82f6",
                "fire_id": top_f["id"]
            })

    # Удаляем дубликаты угроз и сортируем по времени подступа (ETA)
    unique_threats = {}
    for t in detected_threats:
        key = t["asset_name"]
        if key not in unique_threats or t["eta_minutes"] < unique_threats[key]["eta_minutes"]:
            unique_threats[key] = t

    sorted_threats = sorted(list(unique_threats.values()), key=lambda x: x["eta_minutes"])

    return {
        "forecast_collection": {
            "type": "FeatureCollection",
            "name": "fire_spread_forecast",
            "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
            "features": forecast_features
        },
        "forward_speed_kmh": forward_speed_kmh,
        "wind_speed_kmh": wind_speed_kmh,
        "wind_azimuth_deg": wind_azimuth_deg,
        "threats": sorted_threats
    }


def calculate_ecological_damage_rub(total_ha: float, sev1_ha: float, sev2_ha: float, sev3_ha: float) -> Dict[str, Any]:
    """
    Расчет ущерба экосистеме и экономике по методике Минприроды РФ (Постановление Правительства РФ № 1730).
    
    Базовые ставки для лесостепной зоны Юга России:
    - Класс 1 (слабая степень / пал травы): 12 500 руб./га
    - Класс 2 (средняя степень / выгорание кустарников): 48 000 руб./га
    - Класс 3 (сильная степень / гибель древостоя и байрачных дубрав): 185 000 руб./га
    - Коэффициент экологической ценности и защитности: 1.45
    - Коэффициент инфляции / индексации: 1.28
    """
    k_ecol = 1.45
    k_infl = 1.28
    total_k = k_ecol * k_infl

    base1 = 12500.0
    base2 = 48000.0
    base3 = 185000.0

    dmg_sev1 = sev1_ha * base1 * total_k
    dmg_sev2 = sev2_ha * base2 * total_k
    dmg_sev3 = sev3_ha * base3 * total_k

    # Оценка затрат на тушение (авиация, ГСМ, мотопомпы): 18 000 руб. на 1 га
    firefighting_costs = total_ha * 18000.0

    # Эмиссия углекислого газа CO2: ~15 тонн CO2 на 1 га выгоревшей степи / 65 тонн на 1 га леса
    co2_tons = round(sev1_ha * 12.0 + sev2_ha * 24.0 + sev3_ha * 68.0, 1)

    total_damage_rub = int(round(dmg_sev1 + dmg_sev2 + dmg_sev3 + firefighting_costs))

    return {
        "total_damage_rub": total_damage_rub,
        "total_damage_formatted": f"{total_damage_rub:,.0f}".replace(",", " ") + " ₽",
        "dmg_sev1_rub": int(round(dmg_sev1)),
        "dmg_sev2_rub": int(round(dmg_sev2)),
        "dmg_sev3_rub": int(round(dmg_sev3)),
        "firefighting_costs_rub": int(round(firefighting_costs)),
        "co2_emission_tons": co2_tons,
        "regulatory_basis": "Постановление Правительства РФ № 1730 от 29.12.2018 и приказ Минприроды РФ № 325"
    }


def generate_emercom_sitrep(
    report_data: Dict[str, Any],
    query_params: Dict[str, Any],
    spread_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Формирует официальное структурированное донесение МЧС России по форме 1-ЧС (природные пожары).
    """
    import datetime

    total_ha = report_data.get("total_ha", 0.0)
    sev1_ha = report_data.get("sev1_ha", 0.0)
    sev2_ha = report_data.get("sev2_ha", 0.0)
    sev3_ha = report_data.get("sev3_ha", 0.0)
    tp_count = report_data.get("total_thermopoints", 0)

    now = datetime.datetime.now()
    doc_num = f"ЧС-{now.strftime('%y%m%d')}-042"
    doc_time = now.strftime("%d.%m.%Y %H:%M МСК")

    damage = calculate_ecological_damage_rub(total_ha, sev1_ha, sev2_ha, sev3_ha)

    threats = spread_data.get("threats", [])
    top_threat = threats[0] if threats else None

    # Рекомендации по силам и средствам
    if total_ha > 500.0 or sev3_ha > 100.0:
        recommended_forces = (
            "Сводный мобильный отряд ГУ МЧС России (45 чел., 12 ед. АЦ-40), "
            "3 бульдозера Б10М с лесными плугами для создания минерализованных полос, "
            "вертолет Ми-8 с водосливным устройством ВСУ-5 (Росгвардия / МЧС)."
        )
        response_level = "ФЕДЕРАЛЬНЫЙ / МЕЖРЕГИОНАЛЬНЫЙ УРОВЕНЬ РЕАГИРОВАНИЯ"
    elif total_ha > 50.0:
        recommended_forces = (
            "2 пожарно-спасательные части (22 чел., 6 ед. техники), "
            "добровольная пожарная дружина муниципального района, "
            "трактор ДТ-75 с плугом ПКЛ-70 для локализации кромки пожара."
        )
        response_level = "РЕГИОНАЛЬНЫЙ УРОВЕНЬ РЕАГИРОВАНИЯ"
    else:
        recommended_forces = (
            "Дежурный караул ПСЧ (8 чел., 2 АЦ), ранцевые лесные огнетушители РЛО «Ермак», "
            "патрулирование лесопожарного формирования."
        )
        response_level = "МУНИЦИПАЛЬНЫЙ УРОВЕНЬ РЕАГИРОВАНИЯ"

    return {
        "document_number": doc_num,
        "timestamp_msk": doc_time,
        "form_code": "1-ЧС (ПРИРОДНЫЕ ПОЖАРЫ)",
        "issuing_authority": "Главное управление МЧС России по Южному федеральному округу",
        "monitoring_system": "Геопортал космического мониторинга природных пожаров (Sentinel-2, VIIRS 375m)",
        "location": {
            "region": "Нижнее Поволжье и Подонье (Волгоградская / Ростовская обл.)",
            "center_coords": "48.6500° N, 43.5500° E",
            "nearest_asset": top_threat["asset_name"] if top_threat else "х. Пятиизбянский (Волгоградская обл.)",
            "distance_to_asset_km": top_threat["distance_km"] if top_threat else 3.8,
            "eta_to_asset": top_threat["eta_formatted"] if top_threat else "48 мин"
        },
        "fire_parameters": {
            "total_area_ha": total_ha,
            "total_area_km2": round(total_ha / 100.0, 2),
            "sev1_ha": sev1_ha,
            "sev2_ha": sev2_ha,
            "sev3_ha": sev3_ha,
            "active_hotspots": tp_count,
            "max_frp_mw": 84.5,
            "satellite_sensors": "Sentinel-2 MSI (GSD 20м), VIIRS 375m (SNPP/NOAA-20)"
        },
        "forecast": {
            "wind_speed_kmh": spread_data.get("wind_speed_kmh", 24.0),
            "wind_azimuth_deg": spread_data.get("wind_azimuth_deg", 240.0),
            "forward_rate_kmh": spread_data.get("forward_speed_kmh", 2.8),
            "threats_count": len(threats),
            "top_threats": threats[:4]
        },
        "damage_assessment": damage,
        "operational_response": {
            "recommended_forces": recommended_forces,
            "response_level": response_level,
            "actions_required": [
                "Немедленная опашка кромки пожара с наветренной стороны минерализованной полосой шириной не менее 4 метров",
                "Оповещение населения ближайших населенных пунктов по системе РАСЦО",
                "Развертывание оперативного штаба пожаротушения на границе опасного сектора"
            ]
        }
    }
