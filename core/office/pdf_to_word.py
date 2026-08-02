"""Best-effort local PDF to DOCX conversion."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import fitz
from docx import Document
from docx.shared import Inches

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf


def pdf_to_word(source: str | Path, destination: str | Path, *, include_images: bool = True, progress=None) -> Path:
    info = validate_pdf(source); output = Path(destination).resolve(); ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".docx": raise ValueError("PDF to Word output must use .docx.")
    word = Document(); word.core_properties.title = info.path.stem
    with fitz.open(info.path) as pdf:
        for page_index, page in enumerate(pdf):
            blocks = sorted(page.get_text("blocks"), key=lambda block: (round(block[1], 1), block[0]))
            for block in blocks:
                text = block[4].strip()
                if text: word.add_paragraph(text)
            if include_images:
                seen: set[int] = set()
                for image in page.get_images(full=True):
                    xref = image[0]
                    if xref in seen: continue
                    seen.add(xref)
                    try:
                        extracted = pdf.extract_image(xref); stream = BytesIO(extracted["image"])
                        word.add_picture(stream, width=Inches(5.5))
                    except Exception:
                        continue
            if page_index < pdf.page_count - 1: word.add_page_break()
            if progress: progress(round((page_index + 1) / pdf.page_count * 95), f"Converting page {page_index + 1} of {pdf.page_count}")
    with atomic_output(output) as temporary: word.save(temporary)
    if progress: progress(100, output.name)
    return output
