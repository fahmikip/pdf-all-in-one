"""Fill interactive PDF form fields and add visual signatures to documents."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import fitz

from core.utils.file_utils import atomic_output, ensure_distinct_paths
from core.utils.validation import validate_pdf

Progress = Callable[[int, str], None]

WIDGET_TYPES = {0: "Unknown", 1: "Button", 2: "CheckBox", 3: "ComboBox", 4: "ListBox", 5: "Radio Button", 6: "Signature", 7: "Text"}


def _widget_type_name(widget) -> str:
    try:
        return WIDGET_TYPES.get(int(widget.field_type), str(widget.field_type))
    except Exception:
        return "Unknown"


def _widget_value(widget) -> str:
    value = widget.field_value
    if value is None: return ""
    if isinstance(value, bool): return "Yes" if value else "Off"
    return str(value)


def list_form_fields(source: str | Path) -> list[dict[str, object]]:
    info = validate_pdf(source)
    if info.encrypted:
        raise ValueError("Form fields cannot be read from an encrypted PDF. Unlock it first.")
    fields: list[dict[str, object]] = []
    with fitz.open(info.path) as doc:
        for page_number, page in enumerate(doc):
            for widget in page.widgets():
                name = widget.field_name
                if not name: continue
                fields.append({"page": page_number + 1, "name": name, "type": _widget_type_name(widget), "value": _widget_value(widget)})
    return fields


def fill_pdf_form(source: str | Path, destination: str | Path, updates: dict[str, object], *, progress: Progress | None = None) -> Path:
    """Fill matching fields by name and save a new copy."""
    info = validate_pdf(source)
    if info.encrypted:
        raise ValueError("The PDF is encrypted. Unlock it before filling its form.")
    output = Path(destination).resolve()
    ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".pdf":
        raise ValueError("Fill form output must use .pdf.")
    updates = {name: value for name, value in updates.items() if name}
    errors: list[str] = []
    with fitz.open(info.path) as doc:
        applied = 0
        for page_number, page in enumerate(doc):
            for widget in page.widgets():
                name = widget.field_name
                if not name or name not in updates: continue
                try:
                    widget.field_value = updates[name]
                    widget.update()
                    applied += 1
                except Exception:
                    errors.append(name)
            if progress: progress(round((page_number + 1) / doc.page_count * 95), f"Filled page {page_number + 1}")
        if applied == 0 and not errors:
            raise ValueError("No form fields matched the provided values.")
        with atomic_output(output) as temporary:
            doc.save(temporary)
    if progress: progress(100, output.name)
    return output


def sign_pdf(
    source: str | Path,
    destination: str | Path,
    *,
    image_path: str | Path | None = None,
    page_number: int = 1,
    rect: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
    name: str = "",
    role: str = "",
    progress: Progress | None = None,
) -> Path:
    """Overlay a signature image and optional caption onto one page."""
    info = validate_pdf(source)
    if info.encrypted:
        raise ValueError("The PDF is encrypted. Unlock it before signing.")
    output = Path(destination).resolve()
    ensure_distinct_paths(info.path, output)
    if output.suffix.lower() != ".pdf":
        raise ValueError("Sign output must use .pdf.")
    if not image_path and not name:
        raise ValueError("Provide a signature image, a signer name, or both.")
    image = Path(image_path).resolve() if image_path else None
    if image is not None and not image.is_file():
        raise ValueError(f"Signature image not found: {image.name}")
    if page_number < 1:
        raise ValueError("Page number must be at least 1.")
    if rect[0] == 0.0 and rect[1] == 0.0 and rect[2] == 0.0 and rect[3] == 0.0:
        raise ValueError("Choose a position for the signature.")
    with fitz.open(info.path) as doc:
        if page_number > doc.page_count:
            raise ValueError(f"The PDF only has {doc.page_count} page(s).")
        page = doc[page_number - 1]
        left, top, right, bottom = rect
        box = fitz.Rect(left, top, right, bottom)
        if image is not None:
            page.insert_image(box, filename=str(image))
        if name:
            caption_y = bottom + 6
            page.insert_text((left, caption_y), name, fontsize=10, fontname="helv")
            if role:
                page.insert_text((left, caption_y + 13), role, fontsize=8, fontname="helv")
        if progress: progress(90, "Signed page " + str(page_number))
        with atomic_output(output) as temporary:
            doc.save(temporary)
    if progress: progress(100, output.name)
    return output