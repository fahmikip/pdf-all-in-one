"""Page imposition: arrange several source pages onto one output sheet, optionally as a folded booklet."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pymupdf

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf

Progress = Callable[[int, str], None]

_GRIDS = {
    1: (1, 1),
    2: (2, 1),
    4: (2, 2),
    6: (3, 2),
    8: (4, 2),
    9: (3, 3),
    16: (4, 4),
}


def _rounded_up_to_four(count: int) -> int:
    return count + ((4 - count % 4) % 4)


def _inset_tile_left(margin: float, tile_width: float, tile_height: float, column: int, row: int) -> pymupdf.Rect:
    left = column * tile_width + margin
    top = row * tile_height + margin
    right = (column + 1) * tile_width - margin
    bottom = (row + 1) * tile_height - margin
    return pymupdf.Rect(left, top, right, bottom)


def impose_pages(
    source: str | Path,
    destination: str | Path,
    *,
    pages_per_sheet: int = 2,
    booklet: bool = False,
    margin: float = 4.0,
    progress: Progress | None = None,
) -> Path:
    """Create a new PDF where every sheet holds several scaled source pages.

    ``booklet=True`` arranges pages two per sheet in centre-fold order so the
    result, printed on both sides and folded once, reads as a booklet.
    """
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".pdf":
        raise ValueError("Imposition output must use .pdf.")
    if margin < 0:
        raise ValueError("Margin must not be negative.")
    if booklet:
        columns, rows = 2, 1
    else:
        if pages_per_sheet not in _GRIDS:
            raise ValueError("Pages per sheet must be one of: 1, 2, 4, 6, 8, 9, 16.")
        columns, rows = _GRIDS[pages_per_sheet]
    with pymupdf.open(info.path) as document, pymupdf.open() as result:
        page_width = document[0].rect.width
        page_height = document[0].rect.height
        sheet_width = page_width * columns
        sheet_height = page_height * rows
        tile_width = page_width
        tile_height = page_height
        if booklet:
            count = _rounded_up_to_four(document.page_count)
            placed = 0
            for sheet_number in range(count // 4):
                result.new_page(width=sheet_width, height=sheet_height)
                result.new_page(width=sheet_width, height=sheet_height)
                front = result[-2]
                back = result[-1]
                front_rects = (
                    _inset_tile_left(margin, tile_width, tile_height, 0, 0),
                    _inset_tile_left(margin, tile_width, tile_height, 1, 0),
                )
                back_rects = (
                    _inset_tile_left(margin, tile_width, tile_height, 1, 0),
                    _inset_tile_left(margin, tile_width, tile_height, 0, 0),
                )
                left_index = 2 * sheet_number
                right_index = count - 2 * sheet_number - 1
                if left_index < document.page_count:
                    front.show_pdf_page(front_rects[0], document, pno=left_index)
                    placed += 1
                if right_index < document.page_count:
                    front.show_pdf_page(front_rects[1], document, pno=right_index)
                    placed += 1
                if left_index + 1 < document.page_count:
                    back.show_pdf_page(back_rects[0], document, pno=left_index + 1, rotate=180)
                if right_index - 1 < document.page_count:
                    back.show_pdf_page(back_rects[1], document, pno=right_index - 1, rotate=180)
                if progress:
                    progress(
                        round(placed / count * 90),
                        f"Sheet {sheet_number + 1} of {count // 4}",
                    )
        else:
            count = document.page_count
            placed = 0
            capacity = columns * rows
            for sheet_number in range((count + capacity - 1) // capacity):
                result.new_page(width=sheet_width, height=sheet_height)
                sheet = result[-1]
                base = sheet_number * capacity
                for slot in range(capacity):
                    source_index = base + slot
                    if source_index >= count:
                        continue
                    column = slot % columns
                    row = slot // columns
                    sheet.show_pdf_page(
                        _inset_tile_left(margin, tile_width, tile_height, column, row),
                        document,
                        pno=source_index,
                    )
                    placed += 1
                    if progress:
                        progress(
                            round(placed / count * 90),
                            f"Sheet {sheet_number + 1}: placing page {source_index + 1}",
                        )
        with atomic_output(output) as temporary:
            result.save(temporary, garbage=3, deflate=True)
    if progress:
        progress(100, output.name)
    return output
