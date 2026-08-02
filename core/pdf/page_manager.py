"""Non-destructive page removal, reordering, duplication and rotation."""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Iterable, Sequence

import fitz

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf


@dataclass(frozen=True, slots=True)
class PageSpec:
    """A page in an organizer working copy."""

    source_index: int
    rotation: int = 0


def organize_pages(source: str | Path, destination: str | Path, pages: Sequence[PageSpec]) -> Path:
    """Create a new PDF from an arbitrary page order, including duplicates."""
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    if not pages:
        raise ValueError("The output PDF must contain at least one page.")
    _validate_indices((page.source_index for page in pages), info.pages)
    if any(page.rotation % 90 for page in pages):
        raise ValueError("Page rotations must be multiples of 90 degrees.")
    with fitz.open(info.path) as document, fitz.open() as result:
        for specification in pages:
            result.insert_pdf(document, from_page=specification.source_index, to_page=specification.source_index)
            output_page = result[-1]
            source_rotation = document[specification.source_index].rotation
            output_page.set_rotation((source_rotation + specification.rotation) % 360)
        with atomic_output(output) as temporary:
            result.save(temporary, garbage=3, deflate=True)
    return output


def _validate_indices(indices: Iterable[int], page_count: int) -> list[int]:
    result = list(indices)
    if any(index < 0 or index >= page_count for index in result):
        raise ValueError("One or more selected pages are outside the document.")
    return result


def reorder_pages(source: str | Path, destination: str | Path, order: Sequence[int]) -> Path:
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    indices = _validate_indices(order, info.pages)
    if not indices:
        raise ValueError("The output PDF must contain at least one page.")
    with fitz.open(info.path) as document, fitz.open() as result:
        for index in indices:
            result.insert_pdf(document, from_page=index, to_page=index)
        with atomic_output(output) as temporary:
            result.save(temporary, garbage=3, deflate=True)
    return output


def remove_pages(source: str | Path, destination: str | Path, pages: Iterable[int]) -> Path:
    info = validate_pdf(source)
    removed = set(_validate_indices(pages, info.pages))
    remaining = [index for index in range(info.pages) if index not in removed]
    if not remaining:
        raise ValueError("Cannot remove every page from a PDF.")
    return reorder_pages(info.path, destination, remaining)


def rotate_pages(source: str | Path, destination: str | Path, pages: Iterable[int], degrees: int) -> Path:
    if degrees not in (-90, 90, 180, 270):
        raise ValueError("Rotation must be 90, 180, 270, or -90 degrees.")
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    selected = set(_validate_indices(pages, info.pages))
    if not selected:
        raise ValueError("Select at least one page to rotate.")
    with fitz.open(info.path) as document:
        for index in selected:
            page = document[index]
            page.set_rotation((page.rotation + degrees) % 360)
        with atomic_output(output) as temporary:
            document.save(temporary, garbage=3, deflate=True)
    return output
