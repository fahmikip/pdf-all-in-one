"""Best-effort local PDF to Excel (XLSX) content export."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Callable

import fitz
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Alignment, Font

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf

Progress = Callable[[int, str], None]

HEADER_TEXT = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")
COLUMN_WIDTH = 100.0
ROW_HEIGHT_PX = 18.0


def _sheet_name(page_number: int) -> str:
    return f"Page {page_number}"[:31]


def _page_items(page) -> list[tuple[float, str, object]]:
    """Collect (top, kind, payload) items where kind is 'line' or 'image'."""
    items: list[tuple[float, str, object]] = []
    for block in page.get_text("blocks"):
        x0, y0, x1, y1, text = block[0], block[1], block[2], block[3], block[4]
        for line in text.splitlines():
            if line.strip():
                items.append((y0, "line", (x0, line)))
    for info in page.get_image_info(xrefs=True):
        x0, y0 = info["bbox"][:2]
        xref = info.get("xref")
        if xref:
            items.append((y0, "image", (x0, xref, info)))
    items.sort(key=lambda item: (item[0], item[2][0] if item[1] == "line" else 0.0))
    return items


def pdf_to_excel(
    source: str | Path, destination: str | Path, *, progress: Progress | None = None,
) -> Path:
    """Export each page as a worksheet: text lines inline and images embedded."""
    info = validate_pdf(source)
    output = Path(destination).resolve()
    ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".xlsx":
        raise ValueError("PDF to Excel output must use .xlsx.")
    workbook = Workbook(); workbook.remove(workbook.active)
    created = 0
    with fitz.open(info.path) as pdf:
        for page_index, page in enumerate(pdf):
            items = _page_items(page)
            if not items:
                continue
            created += 1
            sheet = workbook.create_sheet(title=_sheet_name(page_index + 1))
            sheet.column_dimensions["A"].width = COLUMN_WIDTH
            row = 1
            for _, kind, payload in items:
                if kind == "line":
                    _, text = payload
                    cell = sheet.cell(row=row, column=1, value=text)
                    cell.font = HEADER_TEXT if row == 1 else None
                    cell.alignment = WRAP
                    row += 1
                    continue
                _, xref, info_dict = payload
                try:
                    data = pdf.extract_image(xref)["image"]
                    canvas = XlImage(BytesIO(data))
                    canvas.width = int(info_dict["width"])
                    canvas.height = int(info_dict["height"])
                    sheet.add_image(canvas, f"A{row}")
                    sheet.row_dimensions[row].height = info_dict["height"]
                    row += max(1, round(info_dict["height"] / ROW_HEIGHT_PX))
                except Exception:
                    continue
            if progress: progress(round((page_index + 1) / pdf.page_count * 95), f"Exported page {page_index + 1}")
    if created == 0:
        raise ValueError("The PDF contains no extractable text or images.")
    with atomic_output(output) as temporary: workbook.save(temporary)
    if progress: progress(100, output.name)
    return output