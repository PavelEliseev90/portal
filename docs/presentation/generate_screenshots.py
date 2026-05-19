#!/usr/bin/env python3
"""Generate UI mock screenshots for the pricing presentation."""
from pathlib import Path

OUT = Path(__file__).parent / "screenshots"
OUT.mkdir(exist_ok=True)

W, H = 960, 540
BG = "#f4f6f9"
CARD = "#ffffff"
BORDER = "#dee2e6"
PRIMARY = "#2563eb"
PRIMARY_DARK = "#1d4ed8"
SUCCESS = "#16a34a"
DANGER = "#dc2626"
MUTED = "#6b7280"
TEXT = "#111827"


def svg_header(title: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
  <defs>
    <linearGradient id="hdr" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{PRIMARY}"/>
      <stop offset="100%" stop-color="{PRIMARY_DARK}"/>
    </linearGradient>
    <filter id="sh" x="-4%" y="-4%" width="108%" height="108%">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-opacity="0.08"/>
    </filter>
  </defs>
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <rect x="0" y="0" width="{W}" height="52" fill="url(#hdr)"/>
  <text x="20" y="33" fill="#fff" font-family="Segoe UI, system-ui, sans-serif" font-size="15" font-weight="600">Корс Групп · Портал</text>
  <text x="{W - 20}" y="33" fill="#dbeafe" font-family="Segoe UI, system-ui, sans-serif" font-size="12" text-anchor="end">{title}</text>
'''


def svg_footer() -> str:
    return "</svg>\n"


def card(x, y, w, h, label=None):
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{CARD}" stroke="{BORDER}" filter="url(#sh)"/>'
    ]
    if label:
        parts.append(
            f'<text x="{x + 14}" y="{y + 22}" fill="{MUTED}" font-family="Segoe UI, system-ui, sans-serif" font-size="11">{label}</text>'
        )
    return "\n  ".join(parts)


def btn(x, y, w, h, text, primary=False):
    fill = PRIMARY if primary else "#e5e7eb"
    tc = "#fff" if primary else TEXT
    return f'''<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}"/>
  <text x="{x + w/2}" y="{y + h/2 + 5}" fill="{tc}" font-family="Segoe UI, system-ui, sans-serif" font-size="12" text-anchor="middle">{text}</text>'''


def hub():
    s = svg_header("Ценообразование новых")
    s += card(24, 68, W - 48, 120, "Директор")
    for i, t in enumerate(["Склад", "Калькуляции", "Соглашения", "Задачи"]):
        s += btn(40 + i * 118, 108, 100, 34, t, i == 0)
    s += card(24, 210, 220, 130)
    s += f'<text x="38" y="242" fill="{TEXT}" font-family="Segoe UI" font-size="14" font-weight="600">Управление КМ</text>'
    s += f'<text x="38" y="262" fill="{MUTED}" font-family="Segoe UI" font-size="11">КМ по бренду на месяц</text>'
    for i, (t, x) in enumerate([("Бренды", 260), ("Индексы КМ", 496), ("Дисконт КМ", 732)]):
        s += card(x, 210, 204, 130)
        s += f'<text x="{x + 14}" y="242" fill="{TEXT}" font-family="Segoe UI" font-size="13" font-weight="600">{t}</text>'
    s += f'<text x="24" y="{H - 24}" fill="{MUTED}" font-family="Segoe UI" font-size="11">/prices_car/</text>'
    s += svg_footer()
    return s


def settings_km():
    s = svg_header("Управление КМ по брендам")
    s += card(24, 68, W - 48, 90)
    s += btn(W - 140, 98, 100, 34, "Добавить", True)
    s += f'<text x="38" y="100" fill="{TEXT}" font-family="Segoe UI" font-size="14" font-weight="600">Внести КМ по всем брендам</text>'
    s += card(24, 175, W - 48, 320)
    s += f'<text x="38" y="205" fill="{TEXT}" font-family="Segoe UI" font-size="13" font-weight="600">Текущие настройки · Май 2026</text>'
    headers = ["Бренд", "КМ", "Индекс", "Мин. КМ"]
    for i, h in enumerate(headers):
        s += f'<text x="{60 + i * 200}" y="235" fill="{MUTED}" font-family="Segoe UI" font-size="11" font-weight="600">{h}</text>'
    rows = [("Toyota", "4.2", "1.0", "185 000"), ("Hyundai", "3.8", "0.95", "162 000"), ("Chery", "5.1", "1.05", "98 500")]
    for ri, row in enumerate(rows):
        y = 260 + ri * 42
        s += f'<rect x="38" y="{y}" width="{W - 76}" height="34" rx="6" fill="#f9fafb"/>'
        for ci, val in enumerate(row):
            s += f'<text x="{60 + ci * 200}" y="{y + 22}" fill="{TEXT}" font-family="Segoe UI" font-size="12">{val}</text>'
    s += svg_footer()
    return s


def car_avto():
    s = svg_header("Ценообразование автомобиля")
    for i, t in enumerate(["Автомобиль", "ЗН доп.", "Склад", "Продажи", "Задачи"]):
        s += btn(24 + i * 108, 64, 98, 30, t, i == 0)
    s += card(24, 108, 420, 200)
    s += f'<text x="38" y="138" fill="{TEXT}" font-family="Segoe UI" font-size="13" font-weight="600">Toyota Camry · VIN ...4821</text>'
    s += f'<text x="38" y="168" fill="{MUTED}" font-family="Segoe UI" font-size="11">Себестоимость (+ДОП): 2 450 000 ₽</text>'
    s += f'<text x="38" y="192" fill="{MUTED}" font-family="Segoe UI" font-size="11">РРЦ: 3 200 000 ₽</text>'
    s += card(24, 320, 420, 100)
    s += f'<rect x="38" y="340" width="180" height="56" rx="10" fill="{PRIMARY}" fill-opacity="0.15"/>'
    s += f'<text x="52" y="365" fill="{PRIMARY}" font-family="Segoe UI" font-size="11">Ценовое правило КМ</text>'
    s += f'<text x="52" y="385" fill="{TEXT}" font-family="Segoe UI" font-size="16" font-weight="700">• 185 000 ₽</text>'
    s += card(460, 108, 476, 312)
    s += f'<rect x="476" y="128" width="444" height="72" rx="10" fill="{DANGER}" fill-opacity="0.85"/>'
    s += f'<text x="492" y="158" fill="#fff" font-family="Segoe UI" font-size="12">Минимальный КМ (правило)</text>'
    s += f'<text x="492" y="182" fill="#fff" font-family="Segoe UI" font-size="18" font-weight="700">185 000 ₽</text>'
    s += f'<text x="492" y="220" fill="{TEXT}" font-family="Segoe UI" font-size="12">Калькуляции по авто (2)</text>'
    s += svg_footer()
    return s


def car_sales():
    s = svg_header("Продажи · аналитика")
    s += card(24, 64, W - 48, 80)
    s += f'<text x="38" y="95" fill="{MUTED}" font-family="Segoe UI" font-size="11">Фильтр: подразделение · марка · модель</text>'
    metrics = ["ВП", "Маржа", "ОПФУ", "Trade-in", "Шины", "Работы"]
    for i, m in enumerate(metrics):
        x = 24 + (i % 3) * 310
        y = 160 + (i // 3) * 90
        s += card(x, y, 290, 72)
        s += f'<text x="{x + 12}" y="{y + 24}" fill="{MUTED}" font-family="Segoe UI" font-size="10">{m}</text>'
        val = f"{(i + 1) * 42000:,}".replace(",", " ")
        s += f'<text x="{x + 12}" y="{y + 48}" fill="{TEXT}" font-family="Segoe UI" font-size="16" font-weight="700">{val} ₽</text>'
    s += card(24, 340, W - 48, 170)
    s += f'<text x="38" y="368" fill="{TEXT}" font-family="Segoe UI" font-size="12" font-weight="600">График продаж по дням</text>'
    for i in range(12):
        h = 30 + (i % 5) * 18
        s += f'<rect x="{60 + i * 68}" y="{480 - h}" width="36" height="{h}" rx="4" fill="{PRIMARY}" fill-opacity="0.7"/>'
    s += svg_footer()
    return s


def calc_list():
    s = svg_header("Калькуляции автомобилей")
    s += card(24, 64, W - 48, 110)
    s += f'<text x="38" y="88" fill="{TEXT}" font-family="Segoe UI" font-size="12" font-weight="600">Фильтр</text>'
    s += f'<text x="38" y="115" fill="{MUTED}" font-family="Segoe UI" font-size="10">Период · VIN · подразделения · соглашение · отгрузка</text>'
    s += card(24, 190, W - 48, 300)
    cols = ["Дата", "№", "Подразделение", "VIN", "КВП"]
    for i, c in enumerate(cols):
        s += f'<text x="{40 + i * 170}" y="220" fill="{MUTED}" font-family="Segoe UI" font-size="10" font-weight="600">{c}</text>'
    for ri in range(5):
        y = 240 + ri * 44
        s += f'<rect x="32" y="{y}" width="{W - 64}" height="36" rx="6" fill="#f9fafb" stroke="{BORDER}" stroke-width="0.5"/>'
        vals = [f"15.05.{26 - ri}", f"КЛ-{1200 + ri}", "ДЦ Север", f"XTA...{ri}42", f"{280 + ri * 15} тыс."]
        for ci, v in enumerate(vals):
            s += f'<text x="{40 + ci * 170}" y="{y + 22}" fill="{TEXT}" font-family="Segoe UI" font-size="11">{v}</text>'
    s += svg_footer()
    return s


def deal_calc():
    s = svg_header("Калькуляция автомобиля")
    s += card(24, 64, 580, 140)
    s += f'<text x="38" y="92" fill="{TEXT}" font-family="Segoe UI" font-size="13" font-weight="600">Рабочий лист · КЛ-1247</text>'
    s += f'<text x="38" y="118" fill="{MUTED}" font-family="Segoe UI" font-size="11">Клиент · менеджер · подразделение</text>'
    s += card(24, 220, 580, 100)
    s += f'<text x="38" y="250" fill="{TEXT}" font-family="Segoe UI" font-size="12" font-weight="600">Применённые акции (3)</text>'
    s += card(620, 64, 316, 256)
    s += f'<rect x="636" y="84" width="284" height="64" rx="10" fill="{DANGER}" fill-opacity="0.85"/>'
    s += f'<text x="652" y="110" fill="#fff" font-family="Segoe UI" font-size="11">Минимальный КМ (правило)</text>'
    s += f'<text x="652" y="134" fill="#fff" font-family="Segoe UI" font-size="16" font-weight="700">185 000 ₽</text>'
    s += f'<text x="652" y="175" fill="{TEXT}" font-family="Segoe UI" font-size="12" font-weight="600">Итоги калькуляции</text>'
    s += f'<text x="652" y="200" fill="{MUTED}" font-family="Segoe UI" font-size="11">Цена · себестоимость · КВП</text>'
    s += f'<text x="652" y="230" fill="{SUCCESS}" font-family="Segoe UI" font-size="18" font-weight="700">КВП: 312 000 ₽</text>'
    s += card(24, 340, 580, 160)
    s += f'<text x="38" y="370" fill="{TEXT}" font-family="Segoe UI" font-size="12" font-weight="600">Расчётные данные · КВП</text>'
    s += svg_footer()
    return s


def deal_analytics():
    s = svg_header("Калькуляция · склад и продажи")
    s += card(24, 64, 440, 200)
    s += f'<text x="38" y="92" fill="{TEXT}" font-family="Segoe UI" font-size="12" font-weight="600">Склад · Toyota</text>'
    s += f'<circle cx="140" cy="175" r="55" fill="none" stroke="{BORDER}" stroke-width="24"/>'
    s += f'<circle cx="140" cy="175" r="55" fill="none" stroke="{PRIMARY}" stroke-width="24" stroke-dasharray="120 230" transform="rotate(-90 140 175)"/>'
    s += f'<circle cx="320" cy="175" r="55" fill="none" stroke="{SUCCESS}" stroke-width="24" stroke-dasharray="80 270" transform="rotate(-90 320 175)"/>'
    s += f'<text x="115" y="180" fill="{TEXT}" font-family="Segoe UI" font-size="11" text-anchor="middle">ДЦ</text>'
    s += f'<text x="295" y="180" fill="{TEXT}" font-family="Segoe UI" font-size="11" text-anchor="middle">Все</text>'
    s += card(480, 64, 456, 420)
    s += f'<text x="494" y="92" fill="{TEXT}" font-family="Segoe UI" font-size="12" font-weight="600">Средняя ВП по моделям</text>'
    colors = [PRIMARY, "#f59e0b", "#8b5cf6", "#ec4899"]
    labels = ["Железо", "ДОП", "ОПФУ", "ТИ"]
    for bi in range(4):
        bx = 520 + bi * 88
        total = 0
        for si, c in enumerate(colors):
            h = 40 + si * 22 + bi * 8
            s += f'<rect x="{bx}" y="{400 - h}" width="52" height="{h}" fill="{c}" rx="3"/>'
            total += h
        s += f'<text x="{bx + 26}" y="420" fill="{MUTED}" font-family="Segoe UI" font-size="9" text-anchor="middle">M{bi+1}</text>'
    for i, lb in enumerate(labels):
        s += f'<rect x="{494 + i*100}" y="440" width="10" height="10" fill="{colors[i]}"/>'
        s += f'<text x="{510 + i*100}" y="449" fill="{MUTED}" font-family="Segoe UI" font-size="9">{lb}</text>'
    s += svg_footer()
    return s


def director():
    s = svg_header("Склад директора")
    s += card(24, 64, W - 48, 70)
    s += f'<text x="38" y="95" fill="{MUTED}" font-family="Segoe UI" font-size="11">Фильтры: подразделение · марка · VIN · задачи · мин. КМ</text>'
    for ri in range(6):
        y = 150 + ri * 58
        s += card(24, y, W - 48, 50)
        s += f'<text x="40" y="{y + 30}" fill="{TEXT}" font-family="Segoe UI" font-size="12">Toyota RAV4 · VIN ... · 45 д. на складе · КМ 172 000 ₽</text>'
    s += svg_footer()
    return s


def brands():
    s = svg_header("Бренды ценообразования")
    s += card(24, 64, W - 48, 400)
    s += btn(W - 130, 88, 90, 32, "+ Бренд", True)
    for ri, name in enumerate(["Toyota", "Lexus", "Hyundai", "Chery", "Haval"]):
        y = 130 + ri * 58
        s += f'<rect x="38" y="{y}" width="{W - 76}" height="48" rx="8" fill="#f9fafb"/>'
        s += f'<text x="52" y="{y + 30}" fill="{TEXT}" font-family="Segoe UI" font-size="13" font-weight="600">{name}</text>'
        s += f'<text x="{W - 200}" y="{y + 30}" fill="{MUTED}" font-family="Segoe UI" font-size="11">марки Авто.ру →</text>'
    s += svg_footer()
    return s


def stage_km():
    s = svg_header("Индексы КМ по этапам")
    s += card(24, 64, W - 48, 380)
    for ri, (stage, idx) in enumerate([("РРЦ", "1.00"), ("Акция", "0.95"), ("Распродажа", "1.10"), ("Спец. условие", "0.85")]):
        y = 110 + ri * 72
        s += card(40, y, W - 80, 58)
        s += f'<text x="56" y="{y + 35}" fill="{TEXT}" font-family="Segoe UI" font-size="14" font-weight="600">{stage}</text>'
        s += f'<text x="{W - 120}" y="{y + 35}" fill="{PRIMARY}" font-family="Segoe UI" font-size="14" font-weight="700">× {idx}</text>'
    s += svg_footer()
    return s


def discount_km():
    s = svg_header("Дисконт КМ")
    s += card(24, 64, W - 48, 400)
    s += f'<text x="38" y="100" fill="{MUTED}" font-family="Segoe UI" font-size="11">Бренд → модель → модификация → комплектация → год</text>'
    rows = [
        ("Chery", "Tiggo 7 Pro", "2024", "78 000 ₽"),
        ("Hyundai", "Solaris", "2023", "65 000 ₽"),
    ]
    for ri, row in enumerate(rows):
        y = 140 + ri * 80
        s += card(40, y, W - 80, 64)
        s += f'<text x="56" y="{y + 38}" fill="{TEXT}" font-family="Segoe UI" font-size="12">{row[0]} · {row[1]} · {row[2]} → {row[3]}</text>'
    s += svg_footer()
    return s


SCREENS = {
    "01-hub.svg": hub,
    "02-settings-km.svg": settings_km,
    "03-brands.svg": brands,
    "04-stage-km.svg": stage_km,
    "05-discount-km.svg": discount_km,
    "06-director.svg": director,
    "07-car-avto.svg": car_avto,
    "08-car-sales.svg": car_sales,
    "09-calc-list.svg": calc_list,
    "10-deal-calc.svg": deal_calc,
    "11-deal-analytics.svg": deal_analytics,
}

if __name__ == "__main__":
    for name, fn in SCREENS.items():
        (OUT / name).write_text(fn(), encoding="utf-8")
    print(f"Wrote {len(SCREENS)} screenshots to {OUT}")
