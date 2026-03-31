# -*- coding: utf-8 -*-
"""
Схема переднего салона для осмотра: без текста, сиденья раздвинуты,
видны карты дверей (стиль близкий к технич. диаграммам осмотра).
"""
from PIL import Image, ImageDraw, ImageFilter

W, H = 1600, 1000
OUT = "static/images/front_interior_door_cards_visible.png"


def vertical_gradient(width, height, top, bottom):
    img = Image.new("RGB", (width, height), top)
    px = img.load()
    for y in range(height):
        t = y / max(1, height - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(width):
            px[x, y] = (r, g, b)
    return img


def main():
    base = vertical_gradient(W, H, (228, 230, 234), (198, 202, 208))
    base = base.convert("RGBA")
    d = ImageDraw.Draw(base)

    # Лёгкая тень пола
    floor_shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fs = ImageDraw.Draw(floor_shadow)
    fs.ellipse((120, 620, 1480, 920), fill=(40, 44, 52, 90))
    base.alpha_composite(floor_shadow.filter(ImageFilter.GaussianBlur(25)))

    d = ImageDraw.Draw(base)

    # Пол и коврики
    d.polygon([(100, 720), (1500, 720), (1520, 960), (80, 960)], fill=(175, 178, 184), outline=(55, 60, 68), width=2)
    d.polygon([(200, 740), (720, 740), (700, 920), (180, 900)], fill=(155, 160, 168), outline=(65, 70, 78), width=1)
    d.polygon([(880, 740), (1400, 740), (1420, 900), (860, 920)], fill=(155, 160, 168), outline=(65, 70, 78), width=1)

    # Педали (зона водителя)
    d.rounded_rectangle((220, 680, 280, 720), radius=4, fill=(95, 100, 108), outline=(45, 48, 54))
    d.rounded_rectangle((290, 690, 340, 725), radius=4, fill=(95, 100, 108), outline=(45, 48, 54))

    # --- Карта левой двери (между левым краем и сиденьем водителя) ---
    left_door_x0 = 80
    d.polygon(
        [
            (left_door_x0, 280),
            (280, 240),
            (320, 680),
            (left_door_x0 + 40, 720),
        ],
        fill=(138, 144, 152),
        outline=(48, 52, 58),
        width=2,
    )
    # Ручка, стеклоподъёмник, динамик (упрощённо)
    d.rounded_rectangle((120, 420, 240, 460), radius=8, fill=(110, 116, 126), outline=(48, 52, 58), width=2)
    d.ellipse((140, 500, 200, 560), outline=(70, 75, 82), width=2)
    d.line((150, 380, 260, 360), fill=(75, 80, 88), width=3)

    # --- Карта правой двери ---
    right_door_x1 = 1520
    d.polygon(
        [
            (right_door_x1, 280),
            (1320, 240),
            (1280, 680),
            (right_door_x1 - 40, 720),
        ],
        fill=(138, 144, 152),
        outline=(48, 52, 58),
        width=2,
    )
    d.rounded_rectangle((1360, 420, 1480, 460), radius=8, fill=(110, 116, 126), outline=(48, 52, 58), width=2)
    d.ellipse((1400, 500, 1460, 560), outline=(70, 75, 82), width=2)
    d.line((1340, 360, 1450, 380), fill=(75, 80, 88), width=3)

    # Торпеда (дуга)
    d.pieslice((180, 80, 1420, 520), 200, 340, fill=(125, 130, 138), outline=(48, 52, 58), width=2)
    d.rectangle((200, 200, 1400, 360), fill=(125, 130, 138), outline=None)

    # Щиток / экран
    d.rounded_rectangle((620, 220, 980, 340), radius=12, fill=(85, 90, 98), outline=(40, 44, 50), width=2)
    d.line((700, 260, 900, 260), fill=(55, 60, 68), width=2)
    d.line((700, 290, 880, 290), fill=(55, 60, 68), width=1)

    # Руль (слева)
    d.ellipse((240, 300, 460, 460), fill=(75, 80, 88), outline=(35, 38, 44), width=3)
    d.ellipse((300, 340, 400, 420), fill=(55, 60, 68), outline=(35, 38, 44), width=2)

    # Центральная консоль (у́же визуально — сиденья раздвинуты)
    cx0, cx1 = 720, 880
    d.polygon(
        [(cx0, 380), (cx1, 380), (cx1, 720), (cx0, 720)],
        fill=(118, 124, 132),
        outline=(48, 52, 58),
        width=2,
    )
    d.rounded_rectangle((740, 420, 860, 480), radius=6, fill=(95, 100, 108), outline=(45, 48, 54))
    d.rounded_rectangle((750, 520, 850, 580), radius=10, fill=(105, 110, 118), outline=(45, 48, 54))
    d.rounded_rectangle((760, 620, 840, 700), radius=8, fill=(125, 130, 138), outline=(45, 48, 54))

    # Сиденье водителя — сдвинуто влево (оставляем зазор у консоли и у двери)
    d.polygon(
        [
            (340, 360),
            (560, 340),
            (600, 680),
            (360, 700),
        ],
        fill=(148, 154, 162),
        outline=(48, 52, 58),
        width=2,
    )
    d.polygon([(380, 380), (520, 370), (545, 520), (400, 535)], fill=None, outline=(70, 75, 82), width=2)
    d.polygon([(400, 540), (530, 525), (560, 650), (420, 665)], fill=None, outline=(70, 75, 82), width=2)
    d.polygon(
        [
            (360, 680),
            (600, 660),
            (640, 860),
            (320, 880),
        ],
        fill=(142, 148, 156),
        outline=(48, 52, 58),
        width=2,
    )

    # Сиденье пассажира — сдвинуто вправо
    d.polygon(
        [
            (1040, 340),
            (1260, 360),
            (1240, 700),
            (1000, 680),
        ],
        fill=(148, 154, 162),
        outline=(48, 52, 58),
        width=2,
    )
    d.polygon([(1060, 370), (1220, 380), (1195, 520), (1080, 535)], fill=None, outline=(70, 75, 82), width=2)
    d.polygon([(1070, 540), (1200, 525), (1180, 650), (1040, 665)], fill=None, outline=(70, 75, 82), width=2)
    d.polygon(
        [
            (1000, 660),
            (1240, 680),
            (1280, 880),
            (960, 860),
        ],
        fill=(142, 148, 156),
        outline=(48, 52, 58),
        width=2,
    )

    # Подголовники
    d.rounded_rectangle((400, 260, 500, 340), radius=20, fill=(135, 141, 150), outline=(48, 52, 58), width=2)
    d.rounded_rectangle((1100, 260, 1200, 340), radius=20, fill=(135, 141, 150), outline=(48, 52, 58), width=2)

    # Ремни
    d.polygon([(520, 300), (560, 320), (540, 520), (500, 510)], fill=(95, 100, 108), outline=(45, 48, 54))
    d.polygon([(1080, 320), (1120, 300), (1140, 510), (1100, 520)], fill=(95, 100, 108), outline=(45, 48, 54))

    # Лёгкое затемнение по краям (без текста)
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    vd.rectangle((0, 0, W, 100), fill=(0, 0, 0, 25))
    vd.rectangle((0, 0, 60, H), fill=(0, 0, 0, 15))
    vd.rectangle((W - 60, 0, W, H), fill=(0, 0, 0, 15))
    base.alpha_composite(vignette)

    base.convert("RGB").save(OUT, "PNG", optimize=True)
    print("Saved", OUT)


if __name__ == "__main__":
    main()
