"""Read and safely update standard PDF metadata."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

import fitz

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf

FIELDS = {"title", "author", "subject", "keywords", "creator", "producer"}


def read_metadata(source: str | Path) -> dict[str, str]:
    info = validate_pdf(source)
    with fitz.open(info.path) as document:
        metadata = document.metadata or {}
    return {field: metadata.get(field, "") for field in FIELDS}


def write_metadata(source: str | Path, destination: str | Path, values: Mapping[str, str], clear: bool = False) -> Path:
    info = validate_pdf(source)
    output = Path(destination).expanduser().resolve()
    ensure_distinct_paths(info.path, output)
    with fitz.open(info.path) as document:
        metadata = {} if clear else dict(document.metadata or {})
        for key, value in values.items():
            if key in FIELDS:
                metadata[key] = str(value)
        document.set_metadata(metadata)
        with atomic_output(output) as temporary:
            document.save(temporary, garbage=3, deflate=True)
    return output
