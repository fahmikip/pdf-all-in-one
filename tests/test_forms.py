from pathlib import Path

import fitz
import pytest

from core.pdf.forms import fill_pdf_form, list_form_fields, sign_pdf


def _form_pdf(path: Path) -> Path:
    document = fitz.open()
    page = document.new_page(width=300, height=400)
    entry = fitz.Widget(); entry.rect = fitz.Rect(50, 50, 200, 80); entry.field_name = "Name"; entry.field_type = fitz.PDF_WIDGET_TYPE_TEXT; page.add_widget(entry)
    entry = fitz.Widget(); entry.rect = fitz.Rect(50, 100, 200, 115); entry.field_name = "Agree"; entry.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX; entry.button_name = "Agree"; page.add_widget(entry)
    document.save(path)
    document.close()
    return path


def _signature_image(path: Path) -> Path:
    from PIL import Image
    Image.new("RGB", (90, 45), (10, 20, 30)).save(path)
    return path


def test_list_form_fields_reports_fields(tmp_path: Path) -> None:
    fields = list_form_fields(_form_pdf(tmp_path / "form.pdf"))
    by_name = {field["name"]: field for field in fields}
    assert set(by_name) == {"Name", "Agree"}
    assert by_name["Name"]["type"] == "Text" and by_name["Name"]["page"] == 1
    assert by_name["Agree"]["type"] == "CheckBox"


def test_fill_pdf_form_sets_values(tmp_path: Path) -> None:
    pdf = _form_pdf(tmp_path / "form.pdf")
    output = fill_pdf_form(pdf, tmp_path / "filled.pdf", {"Name": "Budi", "Agree": True})
    assert output.exists() and output.stat().st_size > 0
    with fitz.open(output) as doc:
        values = {widget.field_name: widget.field_value for widget in doc[0].widgets()}
    assert values["Name"] == "Budi" and values["Agree"] == "Yes"


def test_fill_pdf_form_no_match_raises(tmp_path: Path) -> None:
    pdf = _form_pdf(tmp_path / "form.pdf")
    with pytest.raises(ValueError):
        fill_pdf_form(pdf, tmp_path / "filled.pdf", {"Missing": "x"})


def test_fill_pdf_form_rejects_non_pdf(sample_pdf: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        fill_pdf_form(sample_pdf, tmp_path / "out.xlsx", {"X": "1"})


def test_sign_pdf_overlays_image_and_name(tmp_path: Path) -> None:
    pdf = _form_pdf(tmp_path / "base.pdf")
    image = _signature_image(tmp_path / "sig.png")
    output = sign_pdf(pdf, tmp_path / "signed.pdf", image_path=image, page_number=1, rect=(40, 200, 140, 245), name="Budi", role="Manager")
    assert output.exists() and output.stat().st_size > 0
    with fitz.open(output) as doc:
        drawings = list(doc[0].get_drawings())
        images = doc[0].get_images(full=True)
        text = doc[0].get_text()
    assert images and "Budi" in text and "Manager" in text


def test_sign_pdf_requires_content(tmp_path: Path) -> None:
    pdf = _form_pdf(tmp_path / "base.pdf")
    with pytest.raises(ValueError):
        sign_pdf(pdf, tmp_path / "out.pdf")
    with pytest.raises(ValueError):
        sign_pdf(pdf, tmp_path / "out.pdf", name="Budi", page_number=1, rect=(0, 0, 0, 0))
    with pytest.raises(ValueError):
        sign_pdf(pdf, tmp_path / "out.pdf", name="Budi", page_number=99, rect=(40, 200, 140, 245))