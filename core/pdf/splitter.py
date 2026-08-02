"""PDF split and extraction operations."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import fitz

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import parse_page_ranges, validate_pdf


def extract_pages(source: str | Path, destination: str | Path, pages: Iterable[int]) -> Path:
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    indices = list(dict.fromkeys(pages))
    if not indices:
        raise ValueError("Select at least one page to extract.")
    if any(index < 0 or index >= info.pages for index in indices):
        raise ValueError("One or more selected pages are outside the document.")
    with fitz.open(info.path) as document, fitz.open() as extracted:
        for index in indices:
            extracted.insert_pdf(document, from_page=index, to_page=index)
        with atomic_output(output) as temporary:
            extracted.save(temporary, garbage=3, deflate=True)
    return output


def extract_range(source: str | Path, destination: str | Path, expression: str) -> Path:
    info = validate_pdf(source)
    return extract_pages(info.path, destination, parse_page_ranges(expression, info.pages))


def split_every_n(source: str | Path, output_dir: str | Path, pages_per_file: int = 1) -> list[Path]:
    info = validate_pdf(source)
    if pages_per_file < 1:
        raise ValueError("Pages per file must be at least 1.")
    folder = Path(output_dir).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for start in range(0, info.pages, pages_per_file):
        end = min(start + pages_per_file, info.pages)
        suffix = f"page_{start + 1}" if end - start == 1 else f"pages_{start + 1}-{end}"
        destination = folder / f"{info.path.stem}_{suffix}.pdf"
        extract_pages(info.path, destination, range(start, end))
        outputs.append(destination)
    return outputs
