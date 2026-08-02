"""Offline Tesseract OCR integration."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

import fitz

from core.pdf.merger import merge_pdfs
from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf

Progress = Callable[[int, str], None]


class OcrUnavailableError(RuntimeError): pass


def find_tesseract(manual_path: str | Path | None = None) -> Path | None:
    candidates = [manual_path, shutil.which("tesseract"), r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]
    return next((Path(value).resolve() for value in candidates if value and Path(value).is_file()), None)


def available_languages(executable: str | Path | None = None) -> list[str]:
    command = find_tesseract(executable)
    if not command: return []
    result = subprocess.run([str(command), "--list-langs"], capture_output=True, text=True, timeout=15, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode: return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip() and "available languages" not in line.lower()]


def _command(executable: Path, source: Path, output_base: str, language: str, output_format: str) -> list[str]:
    return [str(executable), str(source), output_base, "-l", language, output_format]


def ocr_image(source: str | Path, destination: str | Path, *, language: str = "eng", output_format: str = "txt", executable: str | Path | None = None, progress: Progress | None = None) -> Path:
    tesseract = find_tesseract(executable)
    if not tesseract: raise OcrUnavailableError("Tesseract OCR was not found. Install Tesseract or locate tesseract.exe in Settings.")
    image = Path(source).resolve()
    if not image.is_file(): raise ValueError("The selected image does not exist.")
    suffix = ".pdf" if output_format == "pdf" else ".txt"
    output = Path(destination).resolve()
    if output.suffix.lower() != suffix: raise ValueError(f"OCR output must use {suffix}.")
    if language not in available_languages(tesseract): raise ValueError(f"Tesseract language '{language}' is not installed.")
    with tempfile.TemporaryDirectory(prefix="pdfmaster-ocr-") as directory:
        base = Path(directory) / "result"
        result = subprocess.run(_command(tesseract, image, str(base), language, output_format), capture_output=True, text=True, timeout=600, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode: raise RuntimeError(result.stderr.strip() or "Tesseract OCR failed.")
        generated = base.with_suffix(suffix)
        with atomic_output(output) as temporary: shutil.copyfile(generated, temporary)
    if progress: progress(100, image.name)
    return output


def ocr_pdf(source: str | Path, destination: str | Path, *, language: str = "eng", output_format: str = "pdf", dpi: int = 200, executable: str | Path | None = None, progress: Progress | None = None) -> Path:
    tesseract = find_tesseract(executable)
    if not tesseract: raise OcrUnavailableError("Tesseract OCR was not found. Install Tesseract or locate tesseract.exe in Settings.")
    info = validate_pdf(source); output = Path(destination).resolve(); ensure_distinct_paths(info.path, output)
    if output_format not in {"pdf", "txt"}: raise ValueError("OCR output format must be PDF or TXT.")
    if language not in available_languages(tesseract): raise ValueError(f"Tesseract language '{language}' is not installed.")
    with tempfile.TemporaryDirectory(prefix="pdfmaster-ocr-") as directory:
        work = Path(directory); generated: list[Path] = []; text_parts: list[str] = []
        with fitz.open(info.path) as document:
            for index, page in enumerate(document):
                image = work / f"page-{index + 1}.png"; page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), colorspace=fitz.csRGB, alpha=False).save(image)
                base = work / f"ocr-{index + 1}"
                result = subprocess.run(_command(tesseract, image, str(base), language, output_format), capture_output=True, text=True, timeout=600, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode: raise RuntimeError(result.stderr.strip() or f"OCR failed on page {index + 1}.")
                if output_format == "pdf": generated.append(base.with_suffix(".pdf"))
                else: text_parts.append(base.with_suffix(".txt").read_text(encoding="utf-8", errors="replace"))
                if progress: progress(round((index + 1) / info.pages * 95), f"OCR page {index + 1} of {info.pages}")
        if output_format == "pdf":
            if len(generated) == 1:
                with atomic_output(output) as temporary: shutil.copyfile(generated[0], temporary)
            else:
                merge_pdfs(generated, output)
        else:
            if output.suffix.lower() != ".txt": raise ValueError("Text output must use .txt.")
            with atomic_output(output) as temporary: temporary.write_text("\n\n".join(text_parts) or "\n", encoding="utf-8")
    if progress: progress(100, output.name)
    return output
