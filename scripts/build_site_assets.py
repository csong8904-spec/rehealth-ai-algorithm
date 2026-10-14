"""Copy the official ReHealth logo into the standalone static site."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/assets/rehealth-official-logo.png"
TARGET = ROOT / "site/assets"


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    image = Image.open(SOURCE).convert("RGB")
    image.save(TARGET / "logo.png", optimize=True)

    # The icon occupies the left edge of the whitespace-cropped official mark.
    # Crop around it without redrawing, recoloring, or stretching it.
    icon = image.crop((0, 0, 1240, image.height))
    icon.thumbnail((112, 112), Image.Resampling.LANCZOS)
    favicon = Image.new("RGB", (128, 128), "white")
    favicon.paste(icon, ((128 - icon.width) // 2, (128 - icon.height) // 2))
    favicon.save(TARGET / "favicon.png", optimize=True)
    print("site brand assets ready")


if __name__ == "__main__":
    main()
