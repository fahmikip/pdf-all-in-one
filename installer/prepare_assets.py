"""Generate deterministic fallback branding assets for Windows builds."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def version_numbers(version: str) -> tuple[int, int, int, int]:
    parts = [int(value) for value in re.findall(r"\d+", version)][:4]
    while len(parts) < 4:
        parts.append(0)
    return parts[0], parts[1], parts[2], parts[3]


def create_version_files() -> None:
    """Keep installer/version.iss and version_info.txt in sync with version.txt."""
    version = (ROOT / "version.txt").read_text(encoding="utf-8").strip()
    major, minor, patch, build = version_numbers(version)
    filevers = f"({major},{minor},{patch},{build})"
    version_info = (
        "VSVersionInfo(\n"
        f"  ffi=FixedFileInfo(filevers={filevers}, prodvers={filevers}, mask=0x3f, flags=0x0, "
        "OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)),\n"
        "  kids=[StringFileInfo([StringTable('040904B0', [\n"
        "    StringStruct('CompanyName', 'Fahmikip'),\n"
        "    StringStruct('FileDescription', 'PDF Master - All-in-One Offline PDF Toolkit'),\n"
        f"    StringStruct('FileVersion', '{version}'),\n"
        "    StringStruct('LegalCopyright', '\\u00a9 2026 Fahmikip'),\n"
        "    StringStruct('ProductName', 'PDF Master'),\n"
        f"    StringStruct('ProductVersion', '{version}'),\n"
        "    StringStruct('Comments', 'https://github.com/fahmikip')])]),\n"
        "    VarFileInfo([VarStruct('Translation', [1033, 1200])])]\n"
        ")\n"
    )
    save_unless_same(ROOT / "installer" / "version_info.txt", version_info.encode())
    save_unless_same(ROOT / "installer" / "version.iss", f'#define MyAppVersion "{version}"\n'.encode())


def font(size: int, bold: bool = False):
    names = ["segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def save_unless_same(target: Path, payload: bytes) -> bool:
    """Write only when the content differs so git stays clean across rebuilds."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() == payload:
        return False
    target.write_bytes(payload)
    return True


def create_icon() -> None:
    target = ROOT / "assets" / "logo" / "logo.ico"
    canvas = Image.new("RGBA", (256, 256), (79, 70, 229, 255))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((45, 24, 211, 232), radius=24, fill="white")
    draw.polygon(((158, 24), (211, 77), (158, 77)), fill=(199, 210, 254, 255))
    draw.rounded_rectangle((75, 112, 181, 128), radius=8, fill=(79, 70, 229, 255))
    draw.rounded_rectangle((75, 148, 165, 164), radius=8, fill=(99, 102, 241, 255))
    icon_buffer = BytesIO()
    canvas.save(
        icon_buffer, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    png_buffer = BytesIO()
    canvas.save(png_buffer, format="PNG")
    save_unless_same(target, icon_buffer.getvalue())
    save_unless_same(ROOT / "assets" / "logo" / "logo.png", png_buffer.getvalue())


def create_developer_placeholder() -> Path:
    target = ROOT / "assets" / "developer" / "developer.jpg"
    image = Image.new("RGB", (600, 600), "#EEF2FF")
    draw = ImageDraw.Draw(image)
    draw.ellipse((100, 75, 500, 475), fill="#6366F1")
    draw.text((230, 175), "F", fill="white", font=font(180, True))
    draw.text((176, 510), "FAHMIKIP", fill="#172033", font=font(42, True))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=92)
    save_unless_same(target, buffer.getvalue())
    return target


def _save_bmp(target: Path, image: Image.Image) -> None:
    buffer = BytesIO()
    image.save(buffer, format="BMP")
    save_unless_same(ROOT / "installer" / target, buffer.getvalue())


def create_installer_images(developer: Path) -> None:
    with Image.open(developer) as source:
        photo = source.convert("RGB")
        photo.thumbnail((150, 150))
        canvas = Image.new("RGB", (164, 314), "#EEF2FF")
        canvas.paste(photo, ((164 - photo.width) // 2, 35))
        draw = ImageDraw.Draw(canvas)
        draw.text((18, 205), "PDF MASTER", fill="#4F46E5", font=font(18, True))
        draw.text((18, 235), "by Fahmikip", fill="#172033", font=font(14))
        _save_bmp("installer_side.bmp", canvas)
        banner = Image.new("RGB", (493, 58), "#EEF2FF")
        banner.paste(photo.resize((52, 52)), (434, 3))
        draw = ImageDraw.Draw(banner)
        draw.text((18, 10), "PDF Master", fill="#4F46E5", font=font(20, True))
        draw.text((18, 34), "Offline PDF Toolkit", fill="#64748B", font=font(11))
        _save_bmp("installer_banner.bmp", banner)
        _save_bmp("developer_installer.bmp", photo.resize((150, 150)))


if __name__ == "__main__":
    create_version_files()
    create_icon()
    developer = create_developer_placeholder()
    create_installer_images(developer)
    print("Installer assets prepared.")
