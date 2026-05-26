from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icon"
ICO_PATH = ICON_DIR / "mediadump-icon.ico"
PNG_PATH = ICON_DIR / "mediadump-icon-1024.png"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def rounded_rectangle_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def draw_icon(size: int) -> Image.Image:
    scale = size / 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def xy(values):
        return tuple(round(v * scale) for v in values)

    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_pixels = bg.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / max(size * 2 - 2, 1)
            r = round(14 * (1 - t) + 20 * t)
            g = round(165 * (1 - t) + 184 * t)
            b = round(233 * (1 - t) + 166 * t)
            bg_pixels[x, y] = (r, g, b, 255)
    bg.putalpha(rounded_rectangle_mask(size, round(56 * scale)))
    image.alpha_composite(bg)

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(xy((36, 70, 206, 212)), radius=round(28 * scale), fill=(8, 51, 68, 42))
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(1, round(4 * scale))))
    image.alpha_composite(shadow)

    draw.rounded_rectangle(xy((92, 84, 232, 206)), radius=round(22 * scale), fill=(247, 253, 255, 255))
    draw.polygon([xy((114, 84))[0:2], xy((154, 84))[0:2], xy((172, 104))[0:2], xy((92, 104))[0:2]], fill=(224, 248, 255, 255))
    draw.rounded_rectangle(xy((92, 131, 232, 206)), radius=round(22 * scale), fill=(255, 255, 255, 255))

    draw.rounded_rectangle(xy((45, 42, 139, 146)), radius=round(14 * scale), fill=(31, 41, 55, 255))
    draw.polygon([xy((115, 42))[0:2], xy((139, 66))[0:2], xy((125, 74))[0:2], xy((115, 64))[0:2]], fill=(75, 85, 99, 255))
    draw.rounded_rectangle(xy((61, 63, 100, 102)), radius=round(8 * scale), fill=(224, 242, 254, 255))
    draw.ellipse(xy((69, 71, 81, 83)), fill=(14, 165, 233, 255))
    draw.polygon([xy((62, 96))[0:2], xy((76, 84))[0:2], xy((86, 93))[0:2], xy((93, 87))[0:2], xy((101, 96))[0:2], xy((101, 102))[0:2], xy((62, 102))[0:2]], fill=(20, 184, 166, 255))
    draw.rounded_rectangle(xy((61, 113, 122, 121)), radius=round(4 * scale), fill=(100, 116, 139, 255))
    draw.rounded_rectangle(xy((61, 126, 107, 134)), radius=round(4 * scale), fill=(100, 116, 139, 255))

    draw.polygon([xy((136, 117))[0:2], xy((171, 117))[0:2], xy((171, 103))[0:2], xy((205, 134))[0:2], xy((171, 165))[0:2], xy((171, 150))[0:2], xy((136, 150))[0:2]], fill=(255, 255, 255, 245))
    draw.polygon([xy((141, 124))[0:2], xy((178, 124))[0:2], xy((178, 115))[0:2], xy((196, 134))[0:2], xy((178, 153))[0:2], xy((178, 143))[0:2], xy((141, 143))[0:2]], fill=(6, 182, 212, 255))

    return image


def main() -> None:
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    source = draw_icon(1024)
    source.save(PNG_PATH)
    ico_images = [source.resize((size, size), Image.Resampling.LANCZOS) for size in SIZES]
    ico_images[-1].save(ICO_PATH, sizes=[(size, size) for size in SIZES], append_images=ico_images[:-1])
    print(f"Wrote {ICO_PATH}")


if __name__ == "__main__":
    main()
