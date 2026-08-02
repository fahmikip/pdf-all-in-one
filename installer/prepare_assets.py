"""Generate deterministic fallback branding assets for Windows builds."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def font(size: int, bold: bool = False):
    names = ["segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf"]
    for name in names:
        try: return ImageFont.truetype(name, size)
        except OSError: continue
    return ImageFont.load_default()


def create_icon() -> None:
    target = ROOT / "assets" / "logo" / "logo.ico"; target.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (256, 256), (79, 70, 229, 255)); draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((45, 24, 211, 232), radius=24, fill="white")
    draw.polygon(((158, 24), (211, 77), (158, 77)), fill=(199, 210, 254, 255))
    draw.rounded_rectangle((75, 112, 181, 128), radius=8, fill=(79, 70, 229, 255))
    draw.rounded_rectangle((75, 148, 165, 164), radius=8, fill=(99, 102, 241, 255))
    canvas.save(target, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    canvas.save(ROOT / "assets" / "logo" / "logo.png")


def create_developer_placeholder() -> Path:
    target = ROOT / "assets" / "developer" / "developer.jpg"
    if target.exists(): return target
    image = Image.new("RGB", (600, 600), "#EEF2FF"); draw = ImageDraw.Draw(image)
    draw.ellipse((100, 75, 500, 475), fill="#6366F1"); draw.text((230, 175), "F", fill="white", font=font(180, True))
    draw.text((176, 510), "FAHMIKIP", fill="#172033", font=font(42, True)); image.save(target, quality=92); return target


def create_installer_images(developer: Path) -> None:
    with Image.open(developer) as source:
        photo = source.convert("RGB"); photo.thumbnail((150, 150))
        canvas = Image.new("RGB", (164, 314), "#EEF2FF"); canvas.paste(photo, ((164 - photo.width) // 2, 35)); draw = ImageDraw.Draw(canvas)
        draw.text((18, 205), "PDF MASTER", fill="#4F46E5", font=font(18, True)); draw.text((18, 235), "by Fahmikip", fill="#172033", font=font(14)); canvas.save(ROOT / "installer" / "installer_side.bmp")
        banner = Image.new("RGB", (493, 58), "#EEF2FF"); banner.paste(photo.resize((52, 52)), (434, 3)); draw = ImageDraw.Draw(banner); draw.text((18, 10), "PDF Master", fill="#4F46E5", font=font(20, True)); draw.text((18, 34), "Offline PDF Toolkit", fill="#64748B", font=font(11)); banner.save(ROOT / "installer" / "installer_banner.bmp")
        photo.resize((150, 150)).save(ROOT / "installer" / "developer_installer.bmp")


if __name__ == "__main__":
    create_icon(); developer = create_developer_placeholder(); create_installer_images(developer); print("Installer assets prepared.")
