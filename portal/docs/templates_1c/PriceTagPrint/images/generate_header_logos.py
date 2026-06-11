"""Generate header logo PNGs matching price_tag_print.html styles."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

COLOR_BRAND = (0, 0, 0)          # чёрный — заголовок и K
COLOR_SUB = (0, 0, 0)            # чёрный — подпись
SCALE = 3                        # sharper PNG for print

BOX = 32 * SCALE
BORDER = 2 * SCALE
RADIUS = 6 * SCALE
GAP = 8 * SCALE
PAD = 4 * SCALE


def load_font(size: int, bold: bool = False):
    candidates = []
    if bold:
        candidates += [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
        ]
    else:
        candidates += [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
        ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded_rect(draw, xy, radius, outline, width):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, outline=outline, width=width)


def draw_logo(title: str, subtitle: str) -> Image.Image:
    font_k = load_font(24 * SCALE, bold=True)
    font_title = load_font(14 * SCALE, bold=True)
    font_sub = load_font(9 * SCALE, bold=False)

    tmp = Image.new("RGBA", (1200, 200), (255, 255, 255, 0))
    td = ImageDraw.Draw(tmp)
    title_bbox = td.textbbox((0, 0), title, font=font_title)
    sub_bbox = td.textbbox((0, 0), subtitle, font=font_sub)
    text_w = max(title_bbox[2] - title_bbox[0], sub_bbox[2] - sub_bbox[0])
    text_h = (title_bbox[3] - title_bbox[1]) + (sub_bbox[3] - sub_bbox[1]) + 2 * SCALE
    content_h = max(BOX, text_h)
    width = PAD + BOX + GAP + text_w + PAD
    height = PAD + content_h + PAD

    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    box_top = PAD + (content_h - BOX) // 2
    box_left = PAD
    rounded_rect(
        draw,
        (box_left, box_top, box_left + BOX, box_top + BOX),
        RADIUS,
        COLOR_BRAND,
        BORDER,
    )
    k_bbox = draw.textbbox((0, 0), "K", font=font_k)
    k_w = k_bbox[2] - k_bbox[0]
    k_h = k_bbox[3] - k_bbox[1]
    draw.text(
        (box_left + (BOX - k_w) // 2, box_top + (BOX - k_h) // 2 - k_bbox[1]),
        "K",
        font=font_k,
        fill=COLOR_BRAND,
    )

    text_left = box_left + BOX + GAP
    title_y = PAD + (content_h - text_h) // 2
    draw.text((text_left, title_y), title, font=font_title, fill=COLOR_BRAND)
    draw.text(
        (text_left, title_y + (title_bbox[3] - title_bbox[1]) + 1 * SCALE),
        subtitle,
        font=font_sub,
        fill=COLOR_SUB,
    )
    return img


def main():
    out_dir = Path(__file__).resolve().parent
    logos = [
        ("logo_korsavto.png", "КорсАвто", "автомобили с пробегом"),
        ("logo_korsgroup.png", "КорсГрупп", "автомобильный холдинг"),
    ]
    for filename, title, subtitle in logos:
        img = draw_logo(title, subtitle)
        path = out_dir / filename
        img.save(path, "PNG")
        print(f"Saved {path} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
