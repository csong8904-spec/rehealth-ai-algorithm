"""Generate the exact-text GitHub social preview image."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/assets/social-preview.png"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def main() -> None:
    width, height = 1280, 640
    image = Image.new("RGB", (width, height), "#071b33")
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            blend = (x / width) * 0.65 + (y / height) * 0.35
            pixels[x, y] = (
                int(7 + 4 * blend),
                int(27 + 66 * blend),
                int(51 + 55 * blend),
            )
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((930, -210, 1390, 250), fill=(73, 230, 195, 18))
    draw.ellipse((1010, 310, 1450, 750), fill=(131, 184, 255, 18))
    points = [(75, 330), (180, 330), (215, 255), (270, 420), (320, 300), (365, 330), (510, 330)]
    draw.line(points, fill="#49e6c3", width=14, joint="curve")
    draw.ellipse((66, 321, 84, 339), fill="#49e6c3")
    draw.ellipse((501, 321, 519, 339), fill="#83b8ff")
    draw.text((590, 190), "ReHealth AI", font=font(78, True), fill="#ffffff")
    draw.text((594, 294), "FAIL-CLOSED HEALTH INTELLIGENCE", font=font(27, True), fill="#69e8cf")
    draw.text((594, 350), "Wearable signals → grounded reports", font=font(30), fill="#d8e9ff")
    draw.rounded_rectangle((594, 430, 1060, 486), radius=18, fill=(20, 75, 91, 210), outline="#49e6c3", width=2)
    draw.text((624, 441), "OPEN · AUDITABLE · HONEST", font=font(21, True), fill="#ffffff")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    main()
