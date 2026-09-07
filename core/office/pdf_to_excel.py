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


def _table_from_words(page, col_tolerance: float = 6.0, row_band: float = 5.0) -> list[list[str]] | None:
    """Heuristic: build a grid from word positions when no ruled table is found."""
    words = [(word[0], word[1], word[4]) for word in page.get_text("words") if word[4].strip()]
    if len(words) < 4:
        return None
    anchors: list[float] = []
    for x0, _, _ in sorted(words, key=lambda word: word[0]):
        if not anchors or x0 - anchors[-1] > col_tolerance:
            anchors.append(x0)
    if len(anchors) < 2:
        return None
    rows: dict[int, list[tuple[float, str]]] = {}
    for x0, y0, text in words:
        rows.setdefault(round(y0 / row_band), []).append((x0, text))
    grid: list[list[str]] = []
    for key in sorted(rows):
        row = [""] * len(anchors)
        for x0, text in sorted(rows[key], key=lambda word: word[0]):
            index = min(range(len(anchors)), key=lambda i: abs(x0 - anchors[i]))
            row[index] = (row[index] + " " + text).strip()
        grid.append(row)
    return grid if any(any(cell for cell in row) for row in grid[1:]) else None


def _clean_grid(grid: list[list[str]]) -> list[list[str]]:
    """Remove fully-empty rows produced by the detection heuristics."""
    return [row for row in grid if any(str(cell).strip() for cell in row)]


def _extract_page_tables(page) -> list[list[list[str]]]:
    """Return a list of grids (list of rows) found on the page."""
    tables = page.find_tables().tables
    if not tables:
        tables = page.find_tables(strategy="text", text_tolerance=3).tables
    grids: list[list[list[str]]] = []
    for table in tables:
        if not table.col_count or not table.row_count:
            continue
        extracted = table.extract()
        if extracted:
            grids.append(_clean_grid(extracted))
    if not grids:
        fallback = _table_from_words(page)
        if fallback:
            grids.append(fallback)
    return grids


def pdf_to_excel(
    source: str | Path, destination: str | Path, *, text_fallback: bool = True,
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
            grids = _extract_page_tables(page)
            if not grids:
                if text_fallback:
                    lines = [line for line in (block[4].strip() for block in page.get_text("blocks")) if line]
                    if lines:
                        created += 1
                        sheet = workbook.create_sheet(title=f"Page {page_index + 1} Text")
                        for line in lines: sheet.append([line])
                if progress: progress(round((page_index + 1) / pdf.page_count * 95), f"Scanned page {page_index + 1}")
                continue
            for table_index, grid in enumerate(grids, start=1):
                created += 1
                sheet = workbook.create_sheet(title=_sheet_name(page_index + 1, table_index))
                for row_index, row in enumerate(grid):
                    sheet.append([text if text is not None else "" for text in row])
                    if row_index == 0:
                        for cell in sheet[1]:
                            cell.font = HEADER_TEXT; cell.fill = HEADER_FILL
                if progress: progress(round((page_index + 1) / pdf.page_count * 95), f"Page {page_index + 1} · {len(grid)} rows")
    if created == 0:
        raise ValueError("No tables were detected in this PDF. Try PDF to Word instead.")
    with atomic_output(output) as temporary: workbook.save(temporary)
    if progress: progress(100, output.name)
    return output