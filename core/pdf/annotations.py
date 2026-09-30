"""Simple permanent PDF highlight and note annotations."""

from __future__ import annotations

from pathlib import Path

import pymupdf

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf


def annotate_pdf(
    source: str | Path,
    destination: str | Path,
    *,
    query: str = "",
    note: str = "",
) -> Path:
    """Highlight every matching text fragment and/or add a note to page one."""
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    if not query.strip() and not note.strip():
        raise ValueError("Masukkan teks untuk disorot atau catatan.")
    with pymupdf.open(info.path) as document:
        if query.strip():
            found = 0
            for page in document:
                for quad in page.search_for(query.strip(), quads=True):
                    annot = page.add_highlight_annot(quad)
                    annot.set_colors(stroke=(1, 0.8, 0.1))
                    annot.update()
                    found += 1
            if not found:
                raise ValueError("Teks untuk disorot tidak ditemukan.")
        if note.strip():
            document[0].add_text_annot(pymupdf.Point(36, 36), note.strip()).update()
        with atomic_output(output) as temporary:
            document.save(temporary, garbage=3, deflate=True)
    return output
