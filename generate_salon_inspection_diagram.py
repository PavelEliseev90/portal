# -*- coding: utf-8 -*-
"""Генерация схемы салона для осмотра и фиксации повреждений (PNG)."""
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1800, 1100
OUT_SVG = "static/images/salon_interior_inspection_diagram.svg"
OUT_PNG = "static/images/salon_interior_inspection_diagram.png"


def load_font(size: int):
    for name in ("arial.ttf", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    # Фон
    img = Image.new("RGB", (W, H), (245, 247, 250))
    d = ImageDraw.Draw(img)
    font_title = load_font(36)
    font_sub = load_font(22)
    font_leg = load_font(18)
    font_num = load_font(20)
    font_small = load_font(15)

    cx, cy = 720, 520
    # Контур кузова (вид сверху, упрощённо)
    body = [
        (cx - 380, cy - 420),
        (cx + 380, cy - 420),
        (cx + 400, cy - 200),
        (cx + 410, cy + 80),
        (cx + 400, cy + 380),
        (cx + 360, cy + 420),
        (cx - 360, cy + 420),
        (cx - 400, cy + 380),
        (cx - 410, cy + 80),
        (cx - 400, cy - 200),
    ]
    d.polygon(body, fill=(220, 224, 230), outline=(55, 62, 72), width=3)

    # Лобовое / капот
    d.polygon(
        [(cx - 320, cy - 400), (cx + 320, cy - 400), (cx + 300, cy - 280), (cx - 300, cy - 280)],
        fill=(200, 206, 216),
        outline=(55, 62, 72),
    )
    d.text((cx - 120, cy - 365), "Перед автомобиля", fill=(70, 76, 86), font=font_small)

    # Панель и руль (зона 7)
    dash_pts = [
        (cx - 280, cy - 260),
        (cx + 280, cy - 260),
        (cx + 270, cy - 160),
        (cx - 270, cy - 160),
    ]
    d.polygon(dash_pts, fill=(180, 186, 196), outline=(55, 62, 72), width=2)
    d.ellipse((cx - 95, cy - 248, cx + 95, cy - 178), fill=(120, 126, 136), outline=(55, 62, 72), width=2)

    # Центральная консоль (6)
    cons = [(cx - 42, cy - 150), (cx + 42, cy - 150), (cx + 38, cy + 120), (cx - 38, cy + 120)]
    d.polygon(cons, fill=(160, 166, 176), outline=(55, 62, 72), width=2)

    # Сиденья передние 1 — водитель, 2 — пассажир
    d.rounded_rectangle((cx - 320, cy - 130, cx - 55, cy + 140), radius=28, fill=(150, 156, 166), outline=(55, 62, 72), width=2)
    d.rounded_rectangle((cx + 55, cy - 130, cx + 320, cy + 140), radius=28, fill=(150, 156, 166), outline=(55, 62, 72), width=2)

    # Задний диван (3+4+5)
    d.rounded_rectangle((cx - 300, cy + 160, cx - 105, cy + 340), radius=22, fill=(145, 151, 161), outline=(55, 62, 72), width=2)
    d.rounded_rectangle((cx - 95, cy + 160, cx + 95, cy + 340), radius=22, fill=(145, 151, 161), outline=(55, 62, 72), width=2)
    d.rounded_rectangle((cx + 105, cy + 160, cx + 300, cy + 340), radius=22, fill=(145, 151, 161), outline=(55, 62, 72), width=2)

    # Пол передний (12) и задний (13) — условные прямоугольники
    d.polygon(
        [
            (cx - 360, cy + 130),
            (cx + 360, cy + 130),
            (cx + 370, cy + 360),
            (cx - 370, cy + 360),
        ],
        outline=(100, 108, 118),
        width=1,
    )
    d.polygon(
        [
            (cx - 370, cy + 350),
            (cx + 370, cy + 350),
            (cx + 350, cy + 400),
            (cx - 350, cy + 400),
        ],
        fill=(210, 214, 220),
        outline=(55, 62, 72),
        width=1,
    )

    # Двери: обивки 8–11
    d.polygon([(cx - 405, cy - 200), (cx - 330, cy - 200), (cx - 320, cy + 200), (cx - 405, cy + 180)], fill=(135, 142, 152), outline=(55, 62, 72), width=2)
    d.polygon([(cx + 330, cy - 200), (cx + 405, cy - 200), (cx + 405, cy + 180), (cx + 320, cy + 200)], fill=(135, 142, 152), outline=(55, 62, 72), width=2)
    d.polygon([(cx - 405, cy + 200), (cx - 330, cy + 210), (cx - 315, cy + 380), (cx - 405, cy + 360)], fill=(130, 137, 147), outline=(55, 62, 72), width=2)
    d.polygon([(cx + 330, cy + 210), (cx + 405, cy + 200), (cx + 405, cy + 360), (cx + 315, cy + 380)], fill=(130, 137, 147), outline=(55, 62, 72), width=2)

    # Потолок — условная зона 14 (пунктир сверху)
    d.arc((cx - 200, cy - 415, cx + 200, cy - 200), start=180, end=0, fill=(90, 98, 108), width=3)

    def mark(x, y, n: str):
        r = 22
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255), outline=(45, 50, 58), width=2)
        tw = d.textlength(n, font=font_num)
        d.text((x - tw / 2, y - 12), n, fill=(25, 28, 34), font=font_num)

    # Номера зон
    mark(cx - 190, cy - 5, "1")
    mark(cx + 190, cy - 5, "2")
    mark(cx - 200, cy + 250, "3")
    mark(cx, cy + 250, "4")
    mark(cx + 200, cy + 250, "5")
    mark(cx, cy - 25, "6")
    mark(cx, cy - 210, "7")
    mark(cx - 360, cy + 20, "8")
    mark(cx + 360, cy + 20, "9")
    mark(cx - 360, cy + 290, "10")
    mark(cx + 360, cy + 290, "11")
    mark(cx - 200, cy + 100, "12")
    mark(cx + 200, cy + 100, "13")
    mark(cx, cy - 340, "14")

    # Заголовок
    d.text((40, 40), "Схема салона — осмотр и фиксация повреждений", fill=(30, 34, 42), font=font_title)
    d.text((40, 88), "Отметьте номер зоны в акте и опишите характер повреждения (царапина, прожог, разрыв и т.д.)", fill=(80, 86, 96), font=font_sub)

    # Легенда справа
    leg_x = 1180
    leg_y = 160
    lines = [
        "Зоны:",
        "1 — сиденье водителя",
        "2 — сиденье переднего пассажира",
        "3 — заднее левое место",
        "4 — заднее среднее место",
        "5 — заднее правое место",
        "6 — центральная консоль (передняя часть)",
        "7 — панель приборов / зона руля",
        "8 — обивка передней левой двери",
        "9 — обивка передней правой двери",
        "10 — обивка задней левой двери",
        "11 — обивка задней правой двери",
        "12 — пол передний (коврики)",
        "13 — пол задний (коврики)",
        "14 — потолок / люк / освещение",
    ]
    for i, line in enumerate(lines):
        d.text((leg_x, leg_y + i * 32), line, fill=(35, 40, 48), font=font_leg if i == 0 else font_small)

    img.save(OUT_PNG, "PNG", optimize=True)
    print("Saved", OUT_PNG)

    basename = os.path.basename(OUT_PNG)
    svg_fixed = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <title>Схема салона для осмотра</title>
  <rect width="100%" height="100%" fill="#f5f7fa"/>
  <image xlink:href="{basename}" href="{basename}" x="0" y="0" width="{W}" height="{H}"/>
</svg>'''
    with open(OUT_SVG, "w", encoding="utf-8") as f:
        f.write(svg_fixed)
    print("Saved", OUT_SVG)


if __name__ == "__main__":
    main()
