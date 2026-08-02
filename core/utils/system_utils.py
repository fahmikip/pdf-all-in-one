"""External dependency discovery without downloads or shell execution."""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path


def dependency_status() -> dict[str, str]:
    candidates = {
        "qpdf": [shutil.which("qpdf")],
        "Ghostscript": [shutil.which("gswin64c"), shutil.which("gs")],
        "LibreOffice": [shutil.which("soffice"), r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"],
        "Tesseract OCR": [shutil.which("tesseract"), r"C:\Program Files\Tesseract-OCR\tesseract.exe"],
    }
    result = {"PyMuPDF": "Installed" if importlib.util.find_spec("fitz") else "Not Found", "pikepdf": "Installed" if importlib.util.find_spec("pikepdf") else "Not Found"}
    for name, paths in candidates.items():
        found = next((str(path) for path in paths if path and Path(path).is_file()), None)
        result[name] = found or "Not Found"
    return result
