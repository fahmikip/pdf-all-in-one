"""Font discovery and file resolution for embedding text in exported PDFs."""
from __future__ import annotations

from pathlib import Path

_FONT_DIRS = (Path(r"C:\Windows\Fonts"), Path("/usr/share/fonts"), Path("/Library/Fonts"))

_ALIASES = {
    "arial": "arial.ttf",
    "arial black": "ariblk.ttf",
    "arial narrow": "arialn.ttf",
    "times new roman": "times.ttf",
    "courier new": "cour.ttf",
    "georgia": "georgia.ttf",
    "verdana": "verdana.ttf",
    "tahoma": "tahoma.ttf",
    "comic sans ms": "comic.ttf",
    "palatino linotype": "pala.ttf",
    "book antiqua": "bkant.ttf",
    "trebuchet ms": "trebuc.ttf",
    "segoe ui": "segoeui.ttf",
    "segoe ui light": "segoeuil.ttf",
    "segoe ui semibold": "seguisb.ttf",
    "segoe ui semilight": "segoeuisl.ttf",
    "consolas": "consola.ttf",
    "garamond": "garamond.ttf",
    "impact": "impact.ttf",
    "lucida console": "lucon.ttf",
    "lucida sans unicode": "l_10646.ttf",
    "cambria": "cambria.ttf",
    "calibri": "calibri.ttf",
    "calibri light": "calibril.ttf",
}

_FONT_FALLBACKS = {
    "helvetica": "Arial",
    "helv": "Arial",
    "times": "Times New Roman",
    "courier": "Courier New",
}


def font_directories() -> list[Path]:
    return [directory for directory in _FONT_DIRS if directory.is_dir()]


def resolve_font(family: str) -> Path | None:
    """Return a usable TrueType file path for *family*, or ``None`` to fall back."""
    for candidate in _candidates(family):
        try:
            with candidate.open("rb") as file:
                head = file.read(4)
        except OSError:
            continue
        if head in (b"\x00\x01\x00\x00", b"ttcf"):
            return candidate
    return None


def _candidates(family: str) -> list[Path]:
    key = family.strip().lower()
    if not key:
        return []
    key = _FONT_FALLBACKS.get(key, key)
    files: list[Path] = []
    for directory in font_directories():
        if key in _ALIASES:
            target = directory / _ALIASES[key]
            if target.is_file():
                files.append(target)
        flat = "".join(character for character in key if character.isalnum())
        if flat:
            for pattern in ("*.ttf", "*.ttc"):
                for path in sorted(directory.glob(pattern)):
                    stem = path.stem.lower()
                    if stem == flat or stem.startswith(flat) or flat in stem:
                        files.append(path)
        if files:
            break
    return files