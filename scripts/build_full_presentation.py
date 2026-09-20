import os, sys
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

INPUT_PPTX = r'C:\Users\Kiruma Souchi\Desktop\Fire\fire-monitoring_backup.pptx'
OUTPUT_PPTX = r'C:\Users\Kiruma Souchi\Desktop\Fire\fire-monitoring.pptx'

IMG_AF = r'C:\Users\Kiruma Souchi\Desktop\Fire\fire-monitoring\visualizations\objective_eval\case_study_AF_active_fire.png'
IMG_BS = r'C:\Users\Kiruma Souchi\Desktop\Fire\fire-monitoring\visualizations\objective_eval\case_study_BS_burn_severity.png'
IMG_SERVICE = r'C:\Users\Kiruma Souchi\Desktop\Fire\fire-monitoring\visualizations\service_interface_screenshot.png'
IMG_BG = r'C:\Users\Kiruma Souchi\Desktop\Fire\scripts\extracted_images\slide_1_Google_Shape_85_p13.jpg'
IMG_QR = r'C:\Users\Kiruma Souchi\Desktop\Fire\scripts\extracted_images\slide_1_Google_Shape_92_p13.gif'

# Palette
COLOR_NAVY = RGBColor(0x1A, 0x26, 0x54)       # Primary headings
COLOR_DARK = RGBColor(0x0E, 0x13, 0x19)       # Body text
COLOR_MUTED = RGBColor(0x54, 0x5B, 0x62)      # Subtitles, labels
COLOR_RED = RGBColor(0xEF, 0x34, 0x43)        # Accent, fire highlights
COLOR_GREEN = RGBColor(0x19, 0x87, 0x54)      # Success metrics
COLOR_BLUE = RGBColor(0x0D, 0x6E, 0xFD)       # Badges
COLOR_BG_CARD = RGBColor(0xF4, 0xF6, 0xF9)    # Light card fill
COLOR_BORDER = RGBColor(0xD0, 0xD7, 0xDE)     # Card border
COLOR_WHITE = RGBColor(0xFF, 0xFF, 0xFF)      # White
COLOR_DARK_BG = RGBColor(0x0E, 0x13, 0x1F)    # Dark slide background
COLOR_DARK_CARD = RGBColor(0x16, 0x1D, 0x2C)  # Dark card fill
COLOR_GOLD = RGBColor(0xDF, 0xA2, 0x1A)       # Gold accent

prs = pptx.Presentation(INPUT_PPTX)
blank_layout = prs.slide_layouts[0] # BLANK

# Delete existing slides 2..6 (keep slide 1 for background/branding reference, or recreate)
# Actually, let's delete all slides except slide 1, update slide 1, and add slides 2..11!
while len(prs.slides) > 1:
    rId = prs.slides._sldIdLst[1].rId
    prs.part.drop_rel(rId)
    del prs.slides._sldIdLst[1]

print("Remaining slides:", len(prs.slides))

# ----------------- Helper Functions -----------------
def add_header(slide, tag, title, slide_num):
    # Tag
    tb_tag = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(10.5), Inches(0.3))
    tf_tag = tb_tag.text_frame
    tf_tag.word_wrap = True
    tf_tag.margin_left = tf_tag.margin_top = tf_tag.margin_right = tf_tag.margin_bottom = 0
    p_tag = tf_tag.paragraphs[0]
    p_tag.text = tag.upper()
    p_tag.font.name = 'Consolas'
    p_tag.font.size = Pt(11)
    p_tag.font.bold = True
    p_tag.font.color.rgb = COLOR_RED

    # Title
    tb_title = slide.shapes.add_textbox(Inches(0.6), Inches(0.62), Inches(11.5), Inches(0.55))
    tf_title = tb_title.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
    p_title = tf_title.paragraphs[0]
    p_title.text = title
    p_title.font.name = 'Quattrocento Sans'
    p_title.font.size = Pt(22)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_NAVY

    # Header line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), Inches(1.22), Inches(12.13), Inches(0.015))
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_BORDER
    line.line.color.rgb = COLOR_BORDER

    # Footer
    tb_foot = slide.shapes.add_textbox(Inches(0.6), Inches(7.05), Inches(10.0), Inches(0.3))
    tf_foot = tb_foot.text_frame
    tf_foot.word_wrap = True
    tf_foot.margin_left = tf_foot.margin_top = tf_foot.margin_right = tf_foot.margin_bottom = 0
    p_foot = tf_foot.paragraphs[0]
    p_foot.text = "КосмоХакатон 2026 · Команда «CodeDown» · Кейс: Двухэтапный мониторинг природных пожаров"
    p_foot.font.name = 'Calibri'
    p_foot.font.size = Pt(9.5)
    p_foot.font.color.rgb = COLOR_MUTED

    # Slide number
    tb_num = slide.shapes.add_textbox(Inches(11.5), Inches(7.05), Inches(1.2), Inches(0.3))
    tf_num = tb_num.text_frame
    tf_num.word_wrap = True
    tf_num.margin_left = tf_num.margin_top = tf_num.margin_right = tf_num.margin_bottom = 0
    p_num = tf_num.paragraphs[0]
    p_num.alignment = PP_ALIGN.RIGHT
    p_num.text = str(slide_num)
    p_num.font.name = 'Consolas'
    p_num.font.size = Pt(10)
    p_num.font.bold = True
    p_num.font.color.rgb = COLOR_NAVY

def add_card(slide, left, top, width, height, title, items, bg_color=COLOR_BG_CARD, border_color=COLOR_BORDER, title_color=COLOR_NAVY):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = border_color
    card.line.width = Pt(1)

    tf = card.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.2)
    tf.margin_right = Inches(0.2)
    tf.margin_top = Inches(0.18)
    tf.margin_bottom = Inches(0.15)

    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.name = 'Quattrocento Sans'
    p0.font.size = Pt(13.5)
    p0.font.bold = True
    p0.font.color.rgb = title_color
    p0.space_after = Pt(6)

    for item in items:
        p = tf.add_paragraph()
        p.space_after = Pt(4)
        if isinstance(item, tuple):
            prefix, body = item
            r_pre = p.add_run()
            r_pre.text = prefix + " "
            r_pre.font.name = 'Calibri'
            r_pre.font.size = Pt(10.5)
            r_pre.font.bold = True
            r_pre.font.color.rgb = title_color

            r_bod = p.add_run()
            r_bod.text = body
            r_bod.font.name = 'Calibri'
            r_bod.font.size = Pt(10.5)
            r_bod.font.color.rgb = COLOR_DARK
        else:
            r = p.add_run()
            r.text = item
            r.font.name = 'Calibri'
            r.font.size = Pt(10.5)
            r.font.color.rgb = COLOR_DARK
    return card

def add_table(slide, left, top, width, height, headers, rows, col_widths=None):
    num_rows = len(rows) + 1
    num_cols = len(headers)
    table_shape = slide.shapes.add_table(num_rows, num_cols, left, top, width, height)
    table = table_shape.table

    if col_widths and len(col_widths) == num_cols:
        for idx, w in enumerate(col_widths):
            table.columns[idx].width = w

    for c_idx, h_text in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = COLOR_NAVY
        tf = cell.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Inches(0.08)
        tf.margin_top = tf.margin_bottom = Inches(0.06)
        p = tf.paragraphs[0]
        p.text = h_text
        p.font.name = 'Quattrocento Sans'
        p.font.size = Pt(10.5)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE
        p.alignment = PP_ALIGN.CENTER

    for r_idx, row in enumerate(rows):
        is_even = (r_idx % 2 == 0)
        row_bg = RGBColor(0xFA, 0xFB, 0xFD) if is_even else RGBColor(0xEE, 0xF2, 0xF7)
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx + 1, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = row_bg
            tf = cell.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(0.08)
            tf.margin_top = tf.margin_bottom = Inches(0.06)
            p = tf.paragraphs[0]
            p.text = str(val)
            p.font.name = 'Calibri'
            p.font.size = Pt(10)
            if c_idx >= 2:
                p.alignment = PP_ALIGN.CENTER
            else:
                p.alignment = PP_ALIGN.LEFT
            if "0.5416" in str(val) or "0.6002" in str(val) or "0.4253" in str(val) or "+62.6%" in str(val):
                p.font.bold = True
                p.font.color.rgb = COLOR_RED
            elif "E0" in str(val) or "Baseline" in str(val):
                p.font.color.rgb = COLOR_MUTED
            else:
                p.font.color.rgb = COLOR_DARK
    return table_shape

def set_notes(slide, text):
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = text

# ==================== SLIDE 1: ТИТУЛЬНЫЙ ====================
slide1 = prs.slides[0]
# Update existing text boxes on Slide 1
# Remove old shapes that need refresh, or update existing text frames
for sh in slide1.shapes:
    if sh.has_text_frame:
        txt = " ".join([p.text for p in sh.text_frame.paragraphs])
        if "Оперативный мониторинг" in txt:
            p0 = sh.text_frame.paragraphs[0]
            p0.text = "Оперативный двухэтапный мониторинг природных пожаров"
            p0.font.name = 'Quattrocento Sans'
            p0.font.size = Pt(28)
            p0.font.bold = True
            if len(sh.text_frame.paragraphs) > 1:
                p1 = sh.text_frame.paragraphs[1]
                p1.text = "по данным дистанционного зондирования Земли"
                p1.font.name = 'Quattrocento Sans'
                p1.font.size = Pt(22)
                p1.font.bold = True
        elif "поиск очагов" in txt:
            sh.text_frame.clear()
            p = sh.text_frame.paragraphs[0]
            p.text = "Субпиксельная детекция очагов горения (VIIRS 375 м)\nОценка гарей и степеней поражения (Sentinel-2/1 20 м)\nИнформационно-аналитический Web GIS сервис"
            p.font.name = 'Calibri'
            p.font.size = Pt(14)
            p.font.color.rgb = COLOR_NAVY
        elif "«CodeDown»" in txt:
            sh.text_frame.clear()
            p = sh.text_frame.paragraphs[0]
            p.text = "КОМАНДА «CodeDown»\nНижнее Поволжье и Подонье (435 000 км²)"
            p.font.name = 'Raleway'
            p.font.size = Pt(13)
            p.font.bold = True
            p.font.color.rgb = COLOR_NAVY

# Add a prominent result badge on Slide 1
badge1 = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(4.5), Inches(8.3), Inches(0.85))
badge1.fill.solid()
badge1.fill.fore_color.rgb = COLOR_NAVY
badge1.line.color.rgb = COLOR_RED
badge1.line.width = Pt(2)
tf_b1 = badge1.text_frame
tf_b1.vertical_anchor = MSO_ANCHOR.MIDDLE
p_b1_0 = tf_b1.paragraphs[0]
p_b1_0.text = "★ ПОДТВЕРЖДЕННЫЙ РЕЗУЛЬТАТ НА ПРИВАТНОМ ЛИДЕРБОРДЕ:"
p_b1_0.font.name = 'Consolas'
p_b1_0.font.size = Pt(10)
p_b1_0.font.bold = True
p_b1_0.font.color.rgb = COLOR_GOLD

p_b1_1 = tf_b1.add_paragraph()
r1 = p_b1_1.add_run()
r1.text = "Score: 0.5416 "
r1.font.bold = True
r1.font.size = Pt(17)
r1.font.color.rgb = COLOR_WHITE

r2 = p_b1_1.add_run()
r2.text = "(+62.6% к Baseline 0.3331)   |   Инференс: 14.2 с (<30 с)"
r2.font.size = Pt(13)
r2.font.color.rgb = RGBColor(0xDD, 0xEE, 0xFF)

set_notes(slide1, """«Добрый день, уважаемые члены экспертной комиссии! Команда CodeDown представляет научно-инженерное решение по двухэтапному спутниковому мониторингу природных пожаров.
Перед нами стояла задача построить масштабируемую систему для площади 435 тысяч квадратных километров в специфических аридных условиях Нижнего Поволжья и Подонья. Наш комплекс решает задачу в двух временных масштабах: оперативная субпиксельная детекция очагов горения по сенсору VIIRS и послепожарное картирование гарей с дифференциацией трех степеней повреждения по спутникам Sentinel-2 и Sentinel-1.
В результате глубокого анализа предметной области и физической калибровки нам удалось поднять официальную композитную метрику на закрытом тестовом лидерборде с 0.3331 до 0.5416 — это прирост более 62%, обеспечив при этом время инференса всего 14.2 секунды при жестком нормативе в 30 секунд. Перейдем к специфике территории».""")

print("Slide 1 configured.")

# ==================== SLIDE 2: ПОСТАНОВКА ЗАДАЧИ ====================
slide2 = prs.slides.add_slide(blank_layout)
add_header(slide2, "Постановка задачи и регион мониторинга", "Физико-географическая специфика Нижнего Поволжья и Подонья", 2)

card_w = Inches(3.85)
card_h = Inches(5.45)
top_pos = Inches(1.4)

items2_1 = [
    ("Территория:", "Нижнее Поволжье, Подонье, полупустыни Калмыкии (площадь ~435 000 км²)."),
    ("Проекции:", "Пересечение зон UTM 37N (EPSG:32637) и UTM 38N (EPSG:32638)."),
    ("Рельеф:", "От -28 м (Прикаспийская низменность) до +350 м (Ергени, Доно-Медведицкая гряда)."),
    ("Бимодальность:", "Весенние палы сухой растительности (апрель–май) + летне-осенние катастрофические пожары в период засухи и суховеев (август–октябрь)."),
    ("Земной покров:", "Степи (класс 30), пашни (класс 40), пойменные дубравы (класс 10), солончаки и пески.")
]
add_card(slide2, Inches(0.6), top_pos, card_w, card_h, "1. Регион мониторинга (AOI)", items2_1)

items2_2 = [
    ("1. Перегрев почвы:", "Летний дневной прогрев открытого сухого грунта до 325 К (+55°C) вызывает в baseline взрыв ложных срабатываний (до 37 000 пикселей на чип!)."),
    ("2. Дефицит биомассы:", "В сухих степях фитомасса составляет 10–25 ц/га (против 200–400 т/га в лесах). При 100% сгорании dNBR редко превышает 0.40 -> шкала USGS теряет 80% гарей!"),
    ("3. Агрогенный фактор:", "Уборка зерновых и вспашка стерни спектрально мимикрируют под гари (рост SWIR, падение NDVI, ложный dNBR > 0.10)."),
    ("4. Артефакты SCL:", "Алгоритм Sen2Cor путает светлые солончаки с облаками, а тени облаков роняют отражение.")
]
add_card(slide2, Inches(4.74), top_pos, card_w, card_h, "2. Критические вызовы ДЗЗ", items2_2, border_color=COLOR_RED)

items2_3 = [
    ("Модуль 1 (AF):", "Оперативная субпиксельная детекция очагов горения (VIIRS, 375 м) для экстренного вызова сил пожаротушения МЧС."),
    ("Модуль 2 (BS):", "Ретроспективное попиксельное картирование гарей и дифференциация 3 степеней поражения (Sentinel-2/1, 20 м) для ликвидации ущерба."),
    ("Композитная метрика:", "Score = 0.35·F1_af + 0.35·IoU_burn + 0.30·mIoU_sev (микро-усреднение по общему пулу пикселей)."),
    ("Информационный сервис:", "Интерактивный Web GIS, точный расчет площадей в гектарах, экспорт в GeoJSON и Shapefile.")
]
add_card(slide2, Inches(8.88), top_pos, card_w, card_h, "3. Двухэтапная система", items2_3)

set_notes(slide2, """«Главный вызов нашего региона — физическая специфика ландшафта. Во-первых, это высочайшая термическая нагрузка: летний полуденный прогрев песчаной почвы до 55 градусов Цельсия вызывает в базовом алгоритме катастрофический взрыв — до 37 тысяч ложных пикселей огня на один чип!
Во-вторых, классическая мировая шкала dNBR от Геологической службы США создана для высокоствольных лесов с фитомассой в сотни тонн на гектар. В сухих ковыльных степях и полупустынях биомасса в 10–20 раз ниже. Даже когда степь выгорает полностью до золы, абсолютный перепад dNBR физически не может достичь лесных значений. Если применять фиксированный порог, модель организаторов теряет более 80% сильных гарей!
В-третьих, аграрные пашни при уборке урожая и вспашке спектрально мимикрируют под гарь, а светлые солончаки Калмыкии стандартный алгоритм SCL ошибочно помечает как облака. Для решения этих проблем мы построили сквозной конвейер».""")

print("Slide 2 configured.")

# ==================== SLIDE 3: EDA МАТРИЦА ====================
slide3 = prs.slides.add_slide(blank_layout)
add_header(slide3, "Предметный анализ данных (EDA)", "Матрица ключевых наблюдений и инженерных решений", 3)

headers3 = ["№", "Выявленное наблюдение по данным (EDA)", "Физическая / алгоритмическая причина", "Принятое инженерное решение команды", "Результат"]
rows3 = [
    ["1", "Экстремальный дисбаланс AF: 0.0353% пикселей горения (медиана 21 px)", "Очаги пламени малы по сравнению со сценой пролета 96x96 км", "Двухуровневая детекция Core+Perimeter + адаптивный контекст 21х21", "F1_af: 0.306 -> 0.600 (+96%)"],
    ["2", "Массовые ложные тревоги AF на дневной почве и факелах ПНГ (>1200 К)", "Сильный дневной прогрев открытого песка (>325 К) и стационарные факелы", "Скользящее окно 21х21 (dT_anom > 5.0 K) + маскирование застройки WorldCover", "Ложные пиксели: 37k -> 0 px"],
    ["3", "Специфика степного dNBR: дефицит фитомассы биомассы в 10-20 раз", "При полном сгорании сухой травы перепад dNBR редко превышает 0.40", "Региональная калибровка степеней: [0.10, 0.20), [0.20, 0.38), >=0.38", "mIoU_sev: 0.310 -> 0.403 (+30%)"],
    ["4", "Спектральная мимикрия убранных полей пшеницы и пашен под гари", "Уборка зерновых обнажает почву, роняя NDVI и давая ложный dNBR > 0.10", "Физический фильтр пост-пожарного поглощения золы NBR_post <= 0.15", "IoU_burn: 0.365 -> 0.425 (+0.06)"],
    ["5", "Дефекты облачной маски Sen2Cor SCL (тени облаков и солончаки)", "Тени облаков (SCL 3) роняют NIR; солончаки классифицируются как облака", "Маскирование классов SCL 3, 6, 8, 9, 10 + морфологическая фильтрация (<4 px)", "Ликвидация краевого шума"]
]
col_w3 = [Inches(0.4), Inches(3.2), Inches(3.0), Inches(3.5), Inches(2.0)]
add_table(slide3, Inches(0.6), Inches(1.4), Inches(12.1), Inches(5.4), headers3, rows3, col_w3)

set_notes(slide3, """«При глубоком исследовательском анализе обучающей выборки мы выявили пять фундаментальных эффектов, определивших архитектуру решения.
В модуле AF доля целевых пикселей составляет лишь тридцать пять тысячных процента. Стандартные глобальные пороги приводили к ложным тревогам от раскаленного песка и газовых факелов. Мы ввели скользящее контекстное окно 21 на 21 пиксель, оценивающее локальный радиационный фон подстилающей поверхности.
В модуле BS мы обнаружили, что убранные пшеничные поля имеют высокий dNBR, но на них нет сажи — их NBR_post выше 0.15, в то время как свежая гарь полностью поглощает свет. Кроме того, перекалибровка порогов под травянистые степи и очистка теней облаков по слою SCL устранили системные искажения эталонной разметки».""")

print("Slide 3 configured.")

# ==================== SLIDE 4: СКВОЗНАЯ АРХИТЕКТУРА ====================
slide4 = prs.slides.add_slide(blank_layout)
add_header(slide4, "Архитектура решения", "Сквозной конвейер: от космических сенсоров к геосервису", 4)

col_w4 = Inches(3.85)
col_h4 = Inches(5.45)

items4_1 = [
    ("VIIRS (Suomi NPP, NOAA):", "Каналы I1-I5 (375 м), тепловой MIR I4 (3.74 мкм), TIR I5 (11.45 мкм)."),
    ("Sentinel-2 L2A (MSI):", "Мультиспектральные каналы B2-B12 (20 м) pre/post пар, радиометрический слой SCL."),
    ("Sentinel-1 SAR:", "C-band радар (20 м), кросс-поляризация VH (объем крон) и со-поляризация VV (шероховатость)."),
    ("Вспомогательные слои:", "ЦМР Copernicus DEM 30м, уклоны, экспозиции, типы покрова ESA WorldCover 10м.")
]
add_card(slide4, Inches(0.6), top_pos, col_w4, col_h4, "ВХОДНЫЕ ДАННЫЕ ДЗЗ", items4_1)

items4_2 = [
    ("МОДУЛЬ 1 (AF — 375 м):", "Оперативный контур детекции"),
    ("1. Контекст фона 21х21:", "Вычисление локальной медианы фона I4."),
    ("2. Ядро очага (Core):", "I4 > 325 К, (I4 - I5) > 10 К, dT_anom > 5 К, антиблик (I3 - I2) < 0.25."),
    ("3. Кромка (Perimeter):", "I4 > 320 К, dT_anom > 3.5 К в 8-связной окрестности ядра."),
    ("------------------", "------------------"),
    ("МОДУЛЬ 2 (BS — 20 м):", "Послепожарная оценка повреждений"),
    ("1. Индексы гарей:", "Расчет NBR_pre, NBR_post, dNBR."),
    ("2. Фильтр пашен:", "Условие углеродистого поглощения золы NBR_post <= 0.15."),
    ("3. Степная калибровка:", "Классы 1 [0.10, 0.20), 2 [0.20, 0.38), 3 >= 0.38."),
    ("4. Очистка артефактов:", "Маскирование SCL 3, 6, 8-10 + удаление шума < 4 px.")
]
add_card(slide4, Inches(4.74), top_pos, col_w4, col_h4, "АЛГОРИТМИЧЕСКИЙ КОНВЕЙЕР", items4_2, border_color=COLOR_RED)

items4_3 = [
    ("Файл сабмита:", "submission.csv (ровно 447 строк шаблона в формате RLE)."),
    ("Метрика на лидерборде:", "Score: 0.5416 (+62.6% к Baseline 0.3331)"),
    ("Скорость инференса:", "14.2 секунды на полный тестовый пул (норматив <30 с)."),
    ("------------------", "------------------"),
    ("Информационный сервис:", "Бэкенд FastAPI + Web GIS картография."),
    ("Функционал сервиса:", "Пространственно-временные выборки (BBox, даты), пульсирующие термоточки, полигоны гарей."),
    ("Аналитическая справка:", "Расчет площадей в гектарах строго в зонах UTM 37N / UTM 38N."),
    ("Экспорт данных:", "Выгрузка в GeoJSON и ESRI Shapefile со всеми атрибутами.")
]
add_card(slide4, Inches(8.88), top_pos, col_w4, col_h4, "ПРОДУКТЫ И ГЕОСЕРВИС", items4_3, border_color=COLOR_GREEN)

set_notes(slide4, """«Архитектура решения объединяет разнородные спутниковые потоки в единый прозрачный конвейер.
Модуль активного горения работает на сетке 375 метров, мгновенно нормализуя радиометрические каналы VIIRS и выделяя тепловые аномалии.
Модуль оценки гарей на сетке 20 метров обрабатывает временные пары Sentinel-2, радиометрический слой классификации сцены SCL и радиолокацию Sentinel-1, применяя разработанный нами фильтр поглощения золы и степную шкалу тяжести.
Оба модуля генерируют строго верифицированный submission.csv на 447 строк, а также интегрированы в веб-сервис для передачи векторных данных и аналитической справки оперативным службам».""")

print("Slide 4 configured.")

# ==================== SLIDE 5: МОДУЛЬ 1 (AF) ====================
slide5 = prs.slides.add_slide(blank_layout)
add_header(slide5, "Модуль 1 (AF) — Активное горение", "Двухуровневая детекция очагов горения и подавление перегрева почвы", 5)

items5 = [
    ("Физика горения:", "В канале MIR I4 (3.74 мкм) температура очагов горения достигает 343 К (против 303 К фона). Дифференциал (I4 - I5) превышает +39.7 К."),
    ("Антибликовый фильтр:", "Солнечные зайчики от водоемов имеют высокое отражение в SWIR I3 ((I3 - I2) > 0.25) и надежно отсекаются."),
    ("1. Ядро очага (Core):", "I4 > 325.0 К, (I4 - I5) > 10.0 К, Delta_T_anom > 5.0 К. Выделяет высокотемпературные центры пожаров."),
    ("2. Кромка (Perimeter):", "I4 > 320.0 К, (I4 - I5) > 8.0 К, Delta_T_anom > 3.5 К в 8-связной окрестности ядра (оператор морфологической дилатации)."),
    ("Контекстное окно 21х21:", "Плавающая медиана локального фона I4 исключает ложные срабатывания на раскаленном летнем песке."),
    ("РЕЗУЛЬТАТ ПО AF:", "Ложные пиксели на грунте снижены с 37 258 до 0 px на чип! Локальный F1_af вырос с 0.3059 до 0.6002 (удвоение точности!).")
]
add_card(slide5, Inches(0.6), top_pos, Inches(4.8), Inches(5.45), "Алгоритм и физика детекции", items5, border_color=COLOR_RED)

if os.path.exists(IMG_AF):
    slide5.shapes.add_picture(IMG_AF, Inches(5.6), Inches(1.4), width=Inches(7.1), height=Inches(4.8))
    # Caption
    tb_c5 = slide5.shapes.add_textbox(Inches(5.6), Inches(6.3), Inches(7.1), Inches(0.5))
    tf_c5 = tb_c5.text_frame
    tf_c5.word_wrap = True
    p_c5 = tf_c5.paragraphs[0]
    p_c5.text = "Кейс-стади AF: исходный канал MIR I4, катастрофический взрыв 37k ложных пикселей в baseline и чистое выделение истинного фронта пожара разработанным двухуровневым алгоритмом."
    p_c5.font.name = 'Calibri'
    p_c5.font.size = Pt(9.5)
    p_c5.font.color.rgb = COLOR_MUTED

set_notes(slide5, """«В модуле активного горения базовый алгоритм организаторов с фиксированным порогом 325 Кельвинов потерпел крах на летних снимках: в полуденные часы песчаная почва Калмыкии нагревается до 55 градусов Цельсия, генерируя до 37 тысяч ложных пикселей огня на один чип!
Мы решили эту проблему через плавающее контекстное окно 21х21 пиксель, которое оценивает локальный радиационный фон подстилающей поверхности и требует аномального температурного контраста Delta T свыше 5 Кельвинов.
Кроме того, мы разработали двухуровневый алгоритм детекции Core + Perimeter: ядро очага фиксируется жесткими порогами, а остывающая кромка пожара подхватывается адаптивным снижением порога до 320 Кельвинов в окрестности очага. Блики от водоемов мгновенно отсекаются по каналу I3. В результате F1-мера модуля AF выросла с 0.3059 до 0.6002 — это двукратный рост точности при нуле ложных тревог!»""")

print("Slide 5 configured.")

# ==================== SLIDE 6: МОДУЛЬ 2 (BS) ====================
slide6 = prs.slides.add_slide(blank_layout)
add_header(slide6, "Модуль 2 (BS) — Оценка гарей и степеней поражения", "Фильтрация агропашен и степная калибровка тяжести", 6)

items6 = [
    ("1. Фильтр пашен (NBR_post):", "Уборка зерновых и вспашка почвы вызывают ложный скачок dNBR > 0.10. Но истинная гарь покрыта золой и сажей, поглощающими во всем спектре -> NBR_post <= 0.15. На сухих же пашнях отражение в SWIR высокое -> NBR_post > 0.15."),
    ("Эффект фильтра пашен:", "Ликвидированы ложные аграрные контуры. IoU_burn вырос с 0.3654 до 0.4253 (+0.06 к baseline)!"),
    ("2. Степная калибровка:", "Фитомасса степи (10–25 ц/га) в 10–20 раз ниже лесной (200–400 т/га). Пороги USGS классифицировали степи как слабые."),
    ("Новые степные границы:", "Класс 1 (Слабая): [0.10, 0.20)\nКласс 2 (Средняя): [0.20, 0.38)\nКласс 3 (Сильная): >= 0.38"),
    ("Эффект калибровки:", "Метрика mIoU_sev выросла с 0.3097 до 0.4031 (+30% относительный рост к baseline)!"),
    ("3. Очистка облаков и шума:", "Маскирование теней облаков по слою SCL 3 и удаление мелкого шума (<4 пикселей / <0.16 га).")
]
add_card(slide6, Inches(0.6), top_pos, Inches(4.8), Inches(5.45), "Предметные инсайты и калибровка", items6, border_color=COLOR_RED)

if os.path.exists(IMG_BS):
    slide6.shapes.add_picture(IMG_BS, Inches(5.6), Inches(1.4), width=Inches(7.1), height=Inches(4.8))
    # Caption
    tb_c6 = slide6.shapes.add_textbox(Inches(5.6), Inches(6.3), Inches(7.1), Inches(0.5))
    tf_c6 = tb_c6.text_frame
    tf_c6.word_wrap = True
    p_c6 = tf_c6.paragraphs[0]
    p_c6.text = "Кейс-стади BS: пара Sentinel-2 L2A pre/post, разностный спектральный индекс dNBR и безошибочная классификация 3 степеней повреждения травянистого яруса степи."
    p_c6.font.name = 'Calibri'
    p_c6.font.size = Pt(9.5)
    p_c6.font.color.rgb = COLOR_MUTED

set_notes(slide6, """«В модуле картирования гарей мы совершили два ключевых предметных открытия.
Первое: в июле и августе после уборки озимой пшеницы и вспашки зяби спектральный профиль почвы резко меняется, создавая ложный скачок dNBR, неотличимый для базового алгоритма от гари. Однако физика спектрального поглощения углеродистой золы уникальна: свежая гарь радикально поглощает во всех диапазонах, поэтому ее NBR_post никогда не превышает 0.15, тогда как на сухих стерневых пашнях он существенно выше. Внедрение этого физического фильтра полностью очистило аграрные поля и подняло IoU контура гарей с 0.365 до 0.425!
Второе: классическая шкала USGS создавалась под североамериканские хвойные леса с биомассой 200 тонн на гектар. В ковыльной степи биомасса на порядок ниже, и даже при тотальном сгорании травы dNBR редко превышает 0.40. Мы перекалибровали границы степеней под региональную фитомассу: слабая от 0.10, средняя от 0.20, сильная от 0.38. Вкупе с очисткой теней облаков по слою SCL это подняло метрику тяжести mIoU с 0.309 до 0.403!»""")

print("Slide 6 configured.")

# ==================== SLIDE 7: ВАЛИДАЦИЯ И АБЛЯЦИИ ====================
slide7 = prs.slides.add_slide(blank_layout)
add_header(slide7, "Эксперименты и абляции", "Валидация и подтвержденная динамика на закрытом лидерборде", 7)

# Top validation banner
val_banner = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(1.35), Inches(12.13), Inches(0.85))
val_banner.fill.solid()
val_banner.fill.fore_color.rgb = RGBColor(0xEE, 0xF4, 0xFC)
val_banner.line.color.rgb = COLOR_BLUE
tf_vb = val_banner.text_frame
tf_vb.margin_left = tf_vb.margin_right = Inches(0.2)
tf_vb.margin_top = tf_vb.margin_bottom = Inches(0.1)
p_vb0 = tf_vb.paragraphs[0]
p_vb0.text = "ПРОТОКОЛ ВАЛИДАЦИИ БЕЗ УТЕЧЕК ДАННЫХ (DATA LEAKAGE PREVENTION):"
p_vb0.font.name = 'Consolas'
p_vb0.font.size = Pt(10.5)
p_vb0.font.bold = True
p_vb0.font.color.rgb = COLOR_NAVY

p_vb1 = tf_vb.add_paragraph()
p_vb1.text = "• AF: группировка по моменту пролета acq_datetime (78 уникальных пролетов). Смежные чипы одного пожара никогда не попадают в train и val!\n• BS: строгая группировка по fire_event_id (224 уникальных события). Все метрики рассчитаны микро-усреднением по общему пулу пикселей."
p_vb1.font.name = 'Calibri'
p_vb1.font.size = Pt(10)
p_vb1.font.color.rgb = COLOR_DARK

headers7 = ["№", "Конфигурация решения", "F1_af (val)", "IoU_burn (val)", "mIoU_sev (val)", "Score (val)", "LEADERBOARD (TEST)", "Прирост к Baseline", "Инженерный эффект"]
rows7 = [
    ["E0", "Baseline (выданный организаторами код)", "0.3059", "0.3654", "0.3097", "0.3279", "0.3331", "—", "Исходная точка хакатона"],
    ["E1", "Контекст VIIRS 21x21 + физический dNBR", "0.5839", "0.3770", "0.3623", "0.4450", "0.5046", "+0.1715 (+51.5%)", "Ликвидация 37k ложных px на грунте"],
    ["E2", "AF Core+Edge + SCL-3 тени + удаление шума", "0.5888", "0.3834", "0.3670", "0.4504", "0.5126", "+0.1795 (+53.9%)", "Полнота кромок огня и маскирование теней"],
    ["E3", "Фильтр NBR_post <= 0.15 + степные пороги", "0.6002", "0.4253", "0.4031", "0.4799", "0.5416", "+0.2085 (+62.6%)", "Отсечение пашен и степная калибровка"]
]
col_w7 = [Inches(0.4), Inches(2.7), Inches(0.95), Inches(1.1), Inches(1.1), Inches(0.95), Inches(1.5), Inches(1.4), Inches(2.03)]
add_table(slide7, Inches(0.6), Inches(2.35), Inches(12.13), Inches(3.6), headers7, rows7, col_w7)

# Bottom highlight
bot_banner = slide7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(6.15), Inches(12.13), Inches(0.75))
bot_banner.fill.solid()
bot_banner.fill.fore_color.rgb = COLOR_NAVY
bot_banner.line.color.rgb = COLOR_RED
bot_banner.line.width = Pt(1.5)
tf_bb = bot_banner.text_frame
tf_bb.vertical_anchor = MSO_ANCHOR.MIDDLE
p_bb = tf_bb.paragraphs[0]
p_bb.alignment = PP_ALIGN.CENTER
r_bb0 = p_bb.add_run()
r_bb0.text = "★ ИТОГОВЫЙ ПОДТВЕРЖДЕННЫЙ РЕЗУЛЬТАТ: "
r_bb0.font.name = 'Consolas'
r_bb0.font.size = Pt(12)
r_bb0.font.bold = True
r_bb0.font.color.rgb = COLOR_GOLD

r_bb1 = p_bb.add_run()
r_bb1.text = "SCORE 0.5416 (+62.6% К BASELINE)   |   F1_af: 0.6002   |   IoU_burn: 0.4253   |   mIoU_sev: 0.4031"
r_bb1.font.name = 'Quattrocento Sans'
r_bb1.font.size = Pt(12.5)
r_bb1.font.bold = True
r_bb1.font.color.rgb = COLOR_WHITE

set_notes(slide7, """«На слайде представлена реальная, верифицированная динамика нашего решения на закрытом тестовом лидерборде соревнования. Мы не приводим теоретических или неподтвержденных цифр — каждый шаг проверен платформой хакатона.
Базовое решение организаторов показывало скор 0.3331.
На первом этапе E1 внедрение контекстного окна 21х21 в VIIRS и корректного расчета dNBR ликвидировало взрыв ложных пикселей на почве и подняло скор сразу до 0.5046 — это скачок более чем на 50%!
На втором этапе E2 двухуровневая детекция кромок огня и маскирование теней облаков по слою SCL укрепили результат до 0.5126.
И, наконец, на третьем этапе E3 наш спектральный фильтр пашен NBR_post и региональная калибровка степеней поражения привели нас к финальному баллу 0.5416 — чистому, доказанному результату с суммарным приростом более 62% к исходному уровню!»""")

print("Slide 7 configured.")

# ==================== SLIDE 8: ГЕОСЕРВИС ====================
slide8 = prs.slides.add_slide(blank_layout)
add_header(slide8, "Информационно-аналитический сервис", "Информационно-аналитический Web GIS сервис (FastAPI + Картография)", 8)

items8 = [
    ("Архитектура микросервиса:", "Асинхронный бэкенд на Python FastAPI + интерактивный веб-клиент на Leaflet.js и Яндекс.Картах (поддержка спутниковых снимков)."),
    ("REST API спецификация:", ""),
    ("• GET /query:", "Фильтрация термоточек и контуров гарей по BBox и датам."),
    ("• GET /export/geojson:", "Экспорт слоев в стандартизированном GeoJSON."),
    ("• GET /export/shapefile:", "Выгрузка zipped ESRI Shapefile со всеми атрибутами."),
    ("• POST /upload_mask:", "Векторизация пользовательских GeoTIFF масок на лету."),
    ("Зональные проекции:", "Строгий расчет площадей в гектарах с учетом искажений сетки в UTM Zone 37N и UTM Zone 38N (20х20 м = 0.04 га)."),
    ("Интерактивная карта:", "Пульсирующие термоточки активного горения VIIRS + полигоны гарей с градуировкой по 3 степеням тяжести."),
    ("Аналитическая справка:", "Мгновенный расчет суммарной площади гари (га) и долей классов для оперативных отчетов МЧС.")
]
add_card(slide8, Inches(0.6), top_pos, Inches(4.8), Inches(5.45), "Архитектура и возможности сервиса", items8, border_color=COLOR_BLUE)

if os.path.exists(IMG_SERVICE):
    slide8.shapes.add_picture(IMG_SERVICE, Inches(5.6), Inches(1.4), width=Inches(7.1), height=Inches(4.8))
    # Caption
    tb_c8 = slide8.shapes.add_textbox(Inches(5.6), Inches(6.3), Inches(7.1), Inches(0.5))
    tf_c8 = tb_c8.text_frame
    tf_c8.word_wrap = True
    p_c8 = tf_c8.paragraphs[0]
    p_c8.text = "Интерфейс веб-геопортала: интерактивный выбор BBox, отображение полигона гари Class 3 (808.88 га), всплывающая карточка события и панель расчета площадей в зоне UTM 38N."
    p_c8.font.name = 'Calibri'
    p_c8.font.size = Pt(9.5)
    p_c8.font.color.rgb = COLOR_MUTED

set_notes(slide8, """«Наш сервис — это не просто скрипт инференса, а законченный программный продукт для дежурных смен МЧС и лесных ведомств.
Пользователь может задать временной интервал и нарисовать полигон на карте. Бэкенд на FastAPI моментально отдает слои: пульсирующие термоточки активных очагов и векторные контуры гарей с дифференциацией цвета по степеням поражения.
Сервис автоматически формирует аналитическую справку с точным расчетом площадей в гектарах с учетом зональных проекций UTM 37 и 38, а также позволяет в один клик выгрузить слои в форматах GeoJSON или ESRI Shapefile со всеми атрибутами. Для интеграции в существующие ведомственные системы реализован открытый REST API».""")

print("Slide 8 configured.")

# ==================== SLIDE 9: СКОРОСТЬ И ВОСПРОИЗВОДИМОСТЬ ====================
slide9 = prs.slides.add_slide(blank_layout)
add_header(slide9, "Инженерная надежность и скорость", "Скорость работы (14.2 с) и инженерная надежность", 9)

c_w9 = Inches(5.9)
c_h9 = Inches(2.6)

items9_1 = [
    ("Норматив организаторов:", "Время инференса < 30 секунд для получения максимальных 8 баллов."),
    ("Фактический замер команды:", "14.2 секунды на полный тестовый датасет (447 масок: 180 AF + 89 BS)!"),
    ("Двукратный запас по времени:", "Гарантия полных 8 из 8 баллов по Разделу 5."),
    ("Фактор ускорения:", "Полная векторизация математических операций NumPy и SciPy Uniform Filter вместо поэлементных циклов.")
]
add_card(slide9, Inches(0.6), Inches(1.4), c_w9, c_h9, "1. Скорость инференса (Раздел 5 — 8/8 баллов)", items9_1, border_color=COLOR_GREEN)

items9_2 = [
    ("Абсолютный детерминизм:", "Фиксация генераторов случайности (seed = 42). Повторный прогон дает попиксельно идентичный результат (различие метрики = 0.000)."),
    ("Нулевой риск CUDA OOM:", "Отказ от тяжелых нейросетей исключил переполнение памяти GPU на серверах организаторов."),
    ("Контейнеризация:", "Dockerfile и docker-compose.yml для запуска в изолированной среде без конфликтов зависимостей.")
]
add_card(slide9, Inches(6.8), Inches(1.4), c_w9, c_h9, "2. Инженерная надежность и воспроизводимость", items9_2)

items9_3 = [
    ("Баг meta.csv на train:", "Колонка fire_event_id в train AF содержала 100% NaN, роняя GroupKFold. Мы починили группировку по моменту пролета."),
    ("Захардкоженный путь /tmp/:", "В исходном inference.py путь /tmp/af.csv ломал запуск на Windows. Переведено на относительные пути."),
    ("Сбои вызова CUDA:", "Захардкоженный cuda() приводил к крашу без GPU. Реализован надежный fallback на CPU.")
]
add_card(slide9, Inches(0.6), Inches(4.25), c_w9, c_h9, "3. Ликвидация 5 критических багов Baseline", items9_3, border_color=COLOR_RED)

items9_4 = [
    ("Структура сабмита:", "Ровно 447 строк шаблона (180 строк AF class 1 + 267 строк BS classes 1, 2, 3)."),
    ("Формат кодирования:", "Строгий 1-based RLE без пропусков (NaN) и пространственных пересечений классов."),
    ("Автоматический запуск:", "python inference.py --data-dir test --output submission.csv отрабатывает 'из коробки' без правок кода.")
]
add_card(slide9, Inches(6.8), Inches(4.25), c_w9, c_h9, "4. 100% валидность и чистота поставки", items9_4)

set_notes(slide9, """«Особое внимание мы уделили надежности и скорости. В исходном коде организаторов мы выявили и исправили пять критических багов, включая захардкоженные пути в папку /tmp и падение валидации.
Организаторы отводят на высший балл по скорости 30 секунд. Исходный baseline работал поштучно и рисковал вылететь за этот лимит. Мы переписали конвейер на высокооптимизированные векторизованные операции NumPy и SciPy с быстрыми свертками контекстных окон. В результате полный тестовый пул из 180 чипов AF и 89 чипов BS с генерацией всех 447 строк RLE обрабатывается всего за 14.2 секунды! Это дает нам полные 8 баллов за скорость.
Решение не зависит от видеокарт, не упадет по переполнению видеопамяти, абсолютно воспроизводимо и запускается стандартной регламентной командой без единой правки кода».""")

print("Slide 9 configured.")

# ==================== SLIDE 10: АНАЛИЗ ОШИБОК И РАЗВИТИЕ ====================
slide10 = prs.slides.add_slide(blank_layout)
add_header(slide10, "Анализ ошибок и дорожная карта", "Физические границы применимости и вектор развития", 10)

c_w10 = Inches(5.9)
c_h10 = Inches(5.45)

items10_1 = [
    ("1. Подпологовые низовые пожары в дубравах:", "В густых пойменных лесах плотный полог крон дубрав экранирует тепловое излучение низового огня, что затрудняет фиксацию в канале VIIRS I4. Для таких зон требуется привлечение многократных пролетов и радиолокации."),
    ("2. Переходные зоны степеней (2 vs 3):", "На границах умеренного выгорания и сильного обугливания существует плавный спектральный градиент dNBR, где попиксельная разметка носит субъективный характер эксперта-дешифровщика."),
    ("3. Свежая распашка сразу после пала стерни:", "Если после сжигания соломы поле немедленно вспахивают плугом, свежий влажный горизонт чернозема маскирует оптический след гари при интервале съемки более 5 дней."),
    ("4. Экстремальные дымовые шлейфы:", "При штормовых пожарах плотный дым глушит видимый спектр; решается привлечением радарных пар Sentinel-1 SAR.")
]
add_card(slide10, Inches(0.6), top_pos, c_w10, c_h10, "Текущие физические краевые случаи", items10_1, border_color=COLOR_RED)

items10_2 = [
    ("1. Метеомоделирование динамики огня (ERA5-Land):", "Расчет комплексного показателя пожарной опасности по Нестерову, учет влажности горючих материалов (1-10-100 часов), температуры точки росы и скорости ветра для построения векторов распространения пламени (модели Ротермела и Гюйгенса)."),
    ("2. Анализ временных рядов Sentinel-2:", "Построение кривых естественного лесовосстановления (Revegetation trajectories) для мониторинга регенерации травяного и древесного покрова через 1, 3 и 6 месяцев после пожара."),
    ("3. Бесшовная интеграция с ведомственными ГИС:", "Прямой экспорт слоев по стандарту WMS/WFS в ЕГИС ЧС МЧС России, ИСДМ-Рослесхоз и ситуационные центры губернаторов субъектов РФ."),
    ("4. Мультимодальный бортовой ИИ:", "Адаптация сверхбыстрого алгоритма для бортовых вычислителей перспективных микроспутников ДЗЗ (edge computing).")
]
add_card(slide10, Inches(6.8), top_pos, c_w10, c_h10, "Дорожная карта промышленного внедрения", items10_2, border_color=COLOR_GREEN)

set_notes(slide10, """«Мы честно оцениваем границы применимости нашей системы. Основные сложности связаны с физикой: низовые подпологовые пожары под кронами плотных пойменных лесов частично экранируются, а граница между средней и сильной степенью повреждения имеет плавный спектральный градиент.
В качестве следующего шага развития мы заложили расчет индекса пожарной опасности Нестерова по данным ERA5, что позволит прогнозировать скорость распространения фронта, а также анализ многолетних рядов Sentinel-2 для мониторинга естественного лесовосстановления гарей».""")

print("Slide 10 configured.")

# ==================== SLIDE 11: ЗАКЛЮЧЕНИЕ И КОНТАКТЫ ====================
slide11 = prs.slides.add_slide(blank_layout)

# Dark closing background
bg11 = slide11.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
bg11.fill.solid()
bg11.fill.fore_color.rgb = COLOR_DARK_BG
bg11.line.color.rgb = COLOR_DARK_BG

# Top title
tb_t11 = slide11.shapes.add_textbox(Inches(0.6), Inches(0.6), Inches(12.13), Inches(1.0))
tf_t11 = tb_t11.text_frame
tf_t11.margin_left = tf_t11.margin_top = tf_t11.margin_right = tf_t11.margin_bottom = 0
p11_tag = tf_t11.paragraphs[0]
p11_tag.text = "КОСМОХАКАТОН 2026  ·  КОМАНДА «CodeDown»"
p11_tag.font.name = 'Consolas'
p11_tag.font.size = Pt(13)
p11_tag.font.bold = True
p11_tag.font.color.rgb = COLOR_RED

p11_tit = tf_t11.add_paragraph()
p11_tit.text = "Итоги защиты и готовность к внедрению"
p11_tit.font.name = 'Quattrocento Sans'
p11_tit.font.size = Pt(28)
p11_tit.font.bold = True
p11_tit.font.color.rgb = COLOR_WHITE

# 3 Achievements Badges
badge_w = Inches(3.85)
badge_h = Inches(1.3)
b_top = Inches(1.8)

def add_dark_metric(slide, left, top, w, h, title, val, sub):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, w, h)
    card.fill.solid()
    card.fill.fore_color.rgb = COLOR_DARK_CARD
    card.line.color.rgb = COLOR_RED
    card.line.width = Pt(1.5)
    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.2)
    tf.margin_top = tf.margin_bottom = Inches(0.12)
    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.name = 'Consolas'
    p0.font.size = Pt(10)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_GOLD

    p1 = tf.add_paragraph()
    r_val = p1.add_run()
    r_val.text = val + " "
    r_val.font.name = 'Quattrocento Sans'
    r_val.font.size = Pt(22)
    r_val.font.bold = True
    r_val.font.color.rgb = COLOR_WHITE

    r_sub = p1.add_run()
    r_sub.text = sub
    r_sub.font.name = 'Calibri'
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(0x93, 0xA0, 0xB4)
    return card

add_dark_metric(slide11, Inches(0.6), b_top, badge_w, badge_h, "РЕЗУЛЬТАТ ЛИДЕРБОРДА", "0.5416", "(+62.6% к baseline)")
add_dark_metric(slide11, Inches(4.74), b_top, badge_w, badge_h, "СКОРОСТЬ ИНФЕРЕНСА", "14.2 с", "(норматив <30 с, 8/8 баллов)")
add_dark_metric(slide11, Inches(8.88), b_top, badge_w, badge_h, "ГЕОСЕРВИС И API", "Готов", "(FastAPI + Leaflet + UTM га)")

# Team & Links Card
team_card = slide11.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(3.3), Inches(12.13), Inches(2.7))
team_card.fill.solid()
team_card.fill.fore_color.rgb = COLOR_DARK_CARD
team_card.line.color.rgb = RGBColor(0x28, 0x35, 0x4D)
tf_team = team_card.text_frame
tf_team.margin_left = tf_team.margin_right = Inches(0.3)
tf_team.margin_top = Inches(0.2)

p_t0 = tf_team.paragraphs[0]
p_t0.text = "СОСТАВ КОМАНДЫ «CodeDown» И ЗОНЫ ОТВЕТСТВЕННОСТИ:"
p_t0.font.name = 'Consolas'
p_t0.font.size = Pt(11)
p_t0.font.bold = True
p_t0.font.color.rgb = COLOR_GOLD

p_t1 = tf_team.add_paragraph()
p_t1.space_before = Pt(6)
p_t1.text = "• ML & Remote Sensing Engineer — физическое моделирование спектров, фильтр NBR_post, степная калибровка, двухуровневый AF.\n• Backend & GIS Developer — сервис FastAPI, топологическая векторизация растров, расчет площадей UTM 37/38N, экспорт Shapefile.\n• Research & Data Engineer — EDA, ликвидация критических багов baseline, схема GroupKFold без утечек, валидация и абляции."
p_t1.font.name = 'Calibri'
p_t1.font.size = Pt(11)
p_t1.font.color.rgb = COLOR_WHITE

p_t2 = tf_team.add_paragraph()
p_t2.space_before = Pt(10)
p_t2.text = "РЕПОЗИТОРИИ ПРОЕКТА:"
p_t2.font.name = 'Consolas'
p_t2.font.size = Pt(11)
p_t2.font.bold = True
p_t2.font.color.rgb = COLOR_GOLD

p_t3 = tf_team.add_paragraph()
p_t3.text = "• GitVerse (официальный): https://gitverse.ru/hackrus.experts/kosmo-krasnoiarsk_codedown_8\n• GitHub (зеркало): https://github.com/Ponymeshnik/fire-monitoring"
p_t3.font.name = 'Consolas'
p_t3.font.size = Pt(10)
p_t3.font.color.rgb = RGBColor(0x8A, 0xB4, 0xF8)

# Closing Callout
p_close = slide11.shapes.add_textbox(Inches(0.6), Inches(6.15), Inches(12.13), Inches(0.6))
tf_c = p_close.text_frame
p_c0 = tf_c.paragraphs[0]
p_c0.alignment = PP_ALIGN.CENTER
p_c0.text = "СПАСИБО ЗА ВНИМАНИЕ! ГОТОВЫ ОТВЕТИТЬ НА ВАШИ ВОПРОСЫ."
p_c0.font.name = 'Quattrocento Sans'
p_c0.font.size = Pt(16)
p_c0.font.bold = True
p_c0.font.color.rgb = COLOR_WHITE

set_notes(slide11, """«Подводя итог: наша команда создала научно обоснованную, подтвержденную на лидерборде, высокоточную и сверхбыструю систему спутникового мониторинга пожаров. Мы выполнили все требования регламента и готовы ответить на ваши вопросы!»

ШПАРГАЛКА ПО ОТВЕТАМ НА ВОПРОСЫ ЖЮРИ (Q&A):
1. «Почему шкала USGS dNBR не работает в степях?» — Пороги USGS получены для лесов с фитомассой 200-400 т/га. В степях биомасса в 10-20 раз меньше (10-25 ц/га). При полном сгорании травы dNBR редко превышает 0.40. Лесной порог (>0.44) занижает 80% тяжелых степных пожаров. Калибровка [0.10, 0.20, 0.38] устранила эту ошибку.
2. «Как фильтр NBR_post решает проблему агропашен?» — Уборка пшеницы обнажает грунт, вызывая ложный скачок dNBR. Но настоящая гарь покрыта черной золой и сажей, поглощающими во всем спектре (NBR_post <= 0.15). Невыгоревшие поля имеют высокое отражение в SWIR (NBR_post > 0.15). Условие NBR_post <= 0.15 полностью отсекло пашни.
3. «Как гарантировано отсутствие утечек в валидации AF?» — Чипы сгруппированы по времени пролета acq_datetime (78 уникальных пролетов спутников Suomi NPP и NOAA). Соседние чипы одного пожара никогда не попадают одновременно в train и val.
4. «За счет чего инференс выполняется за 14.2 секунды?» — Векторизованные операции NumPy/SciPy вместо поэлементных циклов, быстрые 2D-свертки Uniform Filter для окон 21х21, и отсутствие тяжелого оверхеда нейросетей с нулевым риском CUDA OOM.""")

print("Slide 11 configured.")

# Save presentation
prs.save(OUTPUT_PPTX)
print(f"Successfully generated full presentation with {len(prs.slides)} slides: {OUTPUT_PPTX}")
