"""Derive repository visuals from the unmodified official ReHealth logo."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/brand/rehealth-official-logo-source.png"
ASSETS = ROOT / "docs/assets"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def fitted(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    copy = image.copy()
    copy.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    return copy


def centered(canvas: Image.Image, item: Image.Image, y: int) -> None:
    canvas.alpha_composite(item, ((canvas.width - item.width) // 2, y))


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGBA")
    white = Image.new("RGBA", source.size, "white")
    box = ImageChops.difference(source.convert("RGB"), white.convert("RGB")).getbbox()
    if box is None:
        raise RuntimeError("official logo image contains no visible mark")
    left, top, right, bottom = box
    padding = 90
    logo = source.crop((max(0, left - padding), max(0, top - padding), min(source.width, right + padding), min(source.height, bottom + padding)))
    logo.save(ASSETS / "rehealth-official-logo.png", optimize=True)

    hero = Image.new("RGBA", (1600, 640), "white")
    draw = ImageDraw.Draw(hero, "RGBA")
    for x in range(hero.width):
        draw.line((x, 0, x, hero.height), fill=(22, 177, 220, int(16 * x / hero.width)))
    draw.ellipse((-170, 390, 280, 840), fill=(155, 239, 0, 22))
    draw.ellipse((1330, -210, 1780, 240), fill=(18, 83, 165, 18))
    centered(hero, fitted(logo, 1080, 300), 105)
    tagline = "FAIL-CLOSED HEALTH INTELLIGENCE FOR WEARABLE TIME SERIES"
    tagline_font = font(26, True)
    box2 = draw.textbbox((0, 0), tagline, font=tagline_font)
    draw.text(((hero.width - box2[2]) // 2, 452), tagline, font=tagline_font, fill="#14539a")
    sub = "Open · Auditable · Evidence-first"
    sub_font = font(22)
    box3 = draw.textbbox((0, 0), sub, font=sub_font)
    draw.text(((hero.width - box3[2]) // 2, 507), sub, font=sub_font, fill="#555555")
    hero.convert("RGB").save(ASSETS / "brand-hero.png", optimize=True)

    social = Image.new("RGBA", (1280, 640), "white")
    sdraw = ImageDraw.Draw(social, "RGBA")
    sdraw.rounded_rectangle((34, 34, 1246, 606), radius=42, fill=(247, 251, 255, 255), outline="#d8e8f3", width=3)
    sdraw.ellipse((-120, 370, 260, 750), fill=(155, 239, 0, 25))
    sdraw.ellipse((1030, -180, 1390, 180), fill=(20, 174, 218, 24))
    centered(social, fitted(logo, 900, 270), 120)
    social_tagline = "FAIL-CLOSED HEALTH INTELLIGENCE"
    social_font = font(27, True)
    box4 = sdraw.textbbox((0, 0), social_tagline, font=social_font)
    sdraw.text(((social.width - box4[2]) // 2, 440), social_tagline, font=social_font, fill="#14539a")
    social_sub = "Wearable signals → grounded, auditable reports"
    social_sub_font = font(23)
    box5 = sdraw.textbbox((0, 0), social_sub, font=social_sub_font)
    sdraw.text(((social.width - box5[2]) // 2, 493), social_sub, font=social_sub_font, fill="#555555")
    social.convert("RGB").save(ASSETS / "social-preview.png", optimize=True)
    print("generated official-logo, brand-hero, and social-preview assets")


if __name__ == "__main__":
    main()
