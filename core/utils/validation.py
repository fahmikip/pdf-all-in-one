"""Validation for untrusted local PDF input."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz


class ValidationError(ValueError):
    """User-correctable input validation failure."""


@dataclass(frozen=True, slots=True)
class PdfInfo:
    path: Path
    size: int
    pages: int
    encrypted: bool


def validate_pdf(path: str | Path, *, password: str | None = None, allow_encrypted: bool = False) -> PdfInfo:
    source = Path(path).expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise ValidationError("The selected PDF does not exist.")
    if source.suffix.lower() != ".pdf":
        raise ValidationError("Please select a PDF file.")
    try:
        with fitz.open(source) as document:
            encrypted = bool(document.needs_pass)
            if encrypted and password and not document.authenticate(password):
                raise ValidationError("The PDF password is incorrect.")
            if encrypted and not password and not allow_encrypted:
                raise ValidationError("This PDF is password protected.")
            pages = document.page_count
            if pages < 1:
                raise ValidationError("The PDF does not contain any pages.")
    except ValidationError:
        raise
    except (fitz.FileDataError, RuntimeError) as exc:
        raise ValidationError("The PDF is damaged or cannot be read.") from exc
    return PdfInfo(source, source.stat().st_size, pages, encrypted)


def parse_page_ranges(expression: str, page_count: int) -> list[int]:
    """Parse user-facing one-based ranges into unique zero-based indices."""
    if page_count < 1:
        raise ValidationError("The PDF does not contain any pages.")
    pages: list[int] = []
    seen: set[int] = set()
    for raw_part in expression.split(","):
        part = raw_part.strip()
        if not part:
            continue
        try:
            if "-" in part:
                start_text, end_text = part.split("-", 1)
                start, end = int(start_text), int(end_text)
                if start > end:
                    raise ValidationError(f"Invalid descending range: {part}")
                values = range(start, end + 1)
            else:
                values = (int(part),)
        except ValueError as exc:
            raise ValidationError(f"Invalid page range: {part}") from exc
        for value in values:
            if value < 1 or value > page_count:
                raise ValidationError(f"Page {value} is outside the document (1-{page_count}).")
            index = value - 1
            if index not in seen:
                seen.add(index)
                pages.append(index)
    if not pages:
        raise ValidationError("Enter at least one page number.")
    return pages
