"""Best-effort local PDF to Excel (XLSX) table conversion."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import fitz
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf

Progress = Callable[[int, str], None]

HEADER_FILL = PatternFill("solid", fgColor="1E293B")
HEADER_TEXT = Font(bold=True, color="FFFFFF")


def _sheet_name(page_number: int, table_number: int) -> str:
    name = f"Page {page_number}" + (f"-{table_number}" if table_number > 1 else "")
    return name[:31]


def pdf_to_excel(
    source: str | Path, destination: str | Path, *, text_fallback: bool = False,
    progress: Progress | None = None,
) -> Path:
    """Detect tables on each page and write them to an XLSX workbook."""
    info = validate_pdf(source)
    output = Path(destination).resolve()
    ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".xlsx":
        raise ValueError("PDF to Excel output must use .xlsx.")
    workbook = Workbook(); workbook.remove(workbook.active)
    created = 0
    with fitz.open(info.path) as pdf:
        for page_index, page in enumerate(pdf):
            tables = page.find_tables().tables
            if not tables:
                if text_fallback:
                    lines = [line for line in (block[4].strip() for block in page.get_text("blocks")) if line]
                    if lines:
                        created += 1
                        sheet = workbook.create_sheet(title=f"Page {page_index + 1} Text")
                        for line in lines: sheet.append([line])
                if progress: progress(round((page_index + 1) / pdf.page_count * 95), f"Scanned page {page_index + 1}")
                continue
            for table_index, table in enumerate(tables, start=1):
                columns, rows = table.col_count, table.row_count
                extracted = table.extract() if columns and rows else None
                if not extracted: continue
                created += 1
                sheet = workbook.create_sheet(title=_sheet_name(page_index + 1, table_index))
                for row_index, row in enumerate(extracted):
                    sheet.append([text if text is not None else "" for text in row])
                    if row_index == 0:
                        for cell in sheet[1]:
                            cell.font = HEADER_TEXT; cell.fill = HEADER_FILL
                if progress: progress(round((page_index + 1) / pdf.page_count * 95), f"Page {page_index + 1} · {len(extracted)} rows")
    if created == 0:
        raise ValueError("No tables were found in this PDF. Try PDF to Word instead.")
    with atomic_output(output) as temporary: workbook.save(temporary)
    if progress: progress(100, output.name)
    return output