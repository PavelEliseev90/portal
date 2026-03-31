from PIL import Image, ImageDraw, ImageFilter


W, H = 1600, 900
OUT = "static/images/rear_second_row_condition_realistic.png"


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


def draw_seat(draw, x0, y0, x1, y1, tone=(140, 146, 154), outline=(55, 60, 67)):
    # Backrest
    draw.rounded_rectangle((x0, y0, x1, y1), radius=70, fill=tone, outline=outline, width=4)

    # Backrest internal zones
    w = x1 - x0
    h = y1 - y0
    z0 = (x0 + int(w * 0.12), y0 + int(h * 0.20), x1 - int(w * 0.12), y0 + int(h * 0.40))
    z1 = (x0 + int(w * 0.10), y0 + int(h * 0.42), x1 - int(w * 0.10), y0 + int(h * 0.66))
    z2 = (x0 + int(w * 0.10), y0 + int(h * 0.68), x1 - int(w * 0.10), y0 + int(h * 0.92))
    draw.rounded_rectangle(z0, radius=35, outline=(88, 93, 101), width=3)
    draw.rounded_rectangle(z1, radius=35, outline=(88, 93, 101), width=3)
    draw.rounded_rectangle(z2, radius=35, outline=(88, 93, 101), width=3)


def draw_headrest(draw, x0, y0, x1, y1):
    draw.rounded_rectangle((x0, y0, x1, y1), radius=35, fill=(150, 156, 164), outline=(55, 60, 67), width=4)
    s1 = (x0 + 52, y1 - 2, x0 + 66, y1 + 36)
    s2 = (x1 - 66, y1 - 2, x1 - 52, y1 + 36)
    draw.rounded_rectangle(s1, radius=6, fill=(108, 114, 123), outline=(55, 60, 67), width=2)
    draw.rounded_rectangle(s2, radius=6, fill=(108, 114, 123), outline=(55, 60, 67), width=2)


def draw_cushion(draw, pts, seam_color=(84, 90, 98)):
    draw.polygon(pts, fill=(146, 152, 160), outline=(55, 60, 67))
    # seam lines
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pts
    for t in (0.32, 0.64):
        lx0 = int(x0 * (1 - t) + x3 * t)
        ly0 = int(y0 * (1 - t) + y3 * t)
        lx1 = int(x1 * (1 - t) + x2 * t)
        ly1 = int(y1 * (1 - t) + y2 * t)
        draw.line((lx0, ly0, lx1, ly1), fill=seam_color, width=3)


def main():
    base = vertical_gradient(W, H, (238, 241, 246), (207, 212, 220)).convert("RGBA")

    # Floor shadow
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse((220, 560, 1380, 860), fill=(35, 39, 45, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    base.alpha_composite(shadow)

    # Cabin side trims
    d = ImageDraw.Draw(base)
    d.polygon([(130, 260), (250, 220), (300, 680), (170, 700)], fill=(120, 126, 134), outline=(62, 67, 74))
    d.polygon([(1470, 260), (1350, 220), (1300, 680), (1430, 700)], fill=(120, 126, 134), outline=(62, 67, 74))

    # Seat shadows
    seat_shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(seat_shadow)
    sdraw.rounded_rectangle((240, 225, 620, 640), radius=80, fill=(0, 0, 0, 105))
    sdraw.rounded_rectangle((620, 245, 980, 640), radius=76, fill=(0, 0, 0, 95))
    sdraw.rounded_rectangle((980, 225, 1360, 640), radius=80, fill=(0, 0, 0, 105))
    sdraw.polygon([(235, 560), (635, 575), (655, 810), (220, 785)], fill=(0, 0, 0, 85))
    sdraw.polygon([(620, 575), (980, 575), (980, 812), (640, 808)], fill=(0, 0, 0, 80))
    sdraw.polygon([(965, 575), (1365, 560), (1380, 785), (945, 810)], fill=(0, 0, 0, 85))
    seat_shadow = seat_shadow.filter(ImageFilter.GaussianBlur(14))
    base.alpha_composite(seat_shadow)

    # Seats (backrests)
    d = ImageDraw.Draw(base)
    draw_seat(d, 250, 230, 620, 640)
    draw_seat(d, 620, 250, 980, 640, tone=(147, 153, 161))
    draw_seat(d, 980, 230, 1350, 640)

    # Headrests
    draw_headrest(d, 320, 120, 545, 250)
    draw_headrest(d, 680, 145, 920, 258)
    draw_headrest(d, 1055, 120, 1280, 250)

    # Cushions
    draw_cushion(d, [(230, 560), (650, 575), (675, 810), (210, 785)])
    draw_cushion(d, [(620, 575), (980, 575), (980, 812), (640, 808)], seam_color=(89, 95, 102))
    draw_cushion(d, [(950, 575), (1370, 560), (1390, 785), (925, 810)])

    # Belts and buckles (minimal)
    d.polygon([(370, 260), (300, 440), (322, 447), (392, 268)], fill=(106, 113, 122), outline=(52, 57, 64))
    d.polygon([(1230, 260), (1300, 440), (1278, 447), (1208, 268)], fill=(106, 113, 122), outline=(52, 57, 64))
    d.rounded_rectangle((675, 730, 700, 775), radius=6, fill=(195, 66, 66), outline=(108, 32, 32), width=2)
    d.rounded_rectangle((905, 730, 930, 775), radius=6, fill=(195, 66, 66), outline=(108, 32, 32), width=2)

    # Zone divider lines for clarity
    d.line((325, 380, 545, 380), fill=(80, 85, 92), width=3)
    d.line((325, 472, 545, 472), fill=(80, 85, 92), width=3)
    d.line((695, 390, 905, 390), fill=(80, 85, 92), width=3)
    d.line((695, 485, 905, 485), fill=(80, 85, 92), width=3)
    d.line((1055, 380, 1275, 380), fill=(80, 85, 92), width=3)
    d.line((1055, 472, 1275, 472), fill=(80, 85, 92), width=3)

    # Soft top vignette for more photo-like depth
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    vd.rectangle((0, 0, W, 160), fill=(0, 0, 0, 36))
    vd.rectangle((0, 0, 90, H), fill=(0, 0, 0, 18))
    vd.rectangle((W - 90, 0, W, H), fill=(0, 0, 0, 18))
    base.alpha_composite(vignette)

    base.convert("RGB").save(OUT, "PNG", optimize=True)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
