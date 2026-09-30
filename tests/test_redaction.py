from pathlib import Path

import pymupdf
import pytest
from core.pdf.annotations import annotate_pdf
from core.pdf.redaction import find_text, redact_text, replace_text


def _text_pdf(path: Path) -> Path:
    document = pymupdf.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((30, 60), "Account: 123456 Confidential")
    document.save(path)
    document.close()
    return path


def test_redact_text_removes_match_from_output_and_keeps_source(tmp_path: Path) -> None:
    source = _text_pdf(tmp_path / "source.pdf")
    original = source.read_bytes()
    output = redact_text(source, tmp_path / "redacted.pdf", "123456")
    with pymupdf.open(output) as document:
        assert "123456" not in document[0].get_text()
    assert source.read_bytes() == original


def test_redact_text_requires_a_match(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="tidak ditemukan"):
        redact_text(_text_pdf(tmp_path / "source.pdf"), tmp_path / "out.pdf", "missing")


def test_find_text_rejects_empty_query(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Masukkan teks"):
        find_text(_text_pdf(tmp_path / "source.pdf"), "  ")


def test_replace_text_removes_original_and_inserts_replacement(tmp_path: Path) -> None:
    output = replace_text(_text_pdf(tmp_path / "source.pdf"), tmp_path / "replaced.pdf", "123456", "REDACTED")
    with pymupdf.open(output) as document:
        text = document[0].get_text()
    assert "123456" not in text
    assert "REDACTED" in text


def test_replace_text_can_remove_without_replacement(tmp_path: Path) -> None:
    output = replace_text(_text_pdf(tmp_path / "source.pdf"), tmp_path / "removed.pdf", "123456", "")
    with pymupdf.open(output) as document:
        assert "123456" not in document[0].get_text()


def test_replace_text_rejects_empty_query(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Masukkan teks"):
        replace_text(_text_pdf(tmp_path / "source.pdf"), tmp_path / "out.pdf", " ", "new")


def test_annotate_pdf_adds_highlight_and_note(tmp_path: Path) -> None:
    output = annotate_pdf(
        _text_pdf(tmp_path / "source.pdf"),
        tmp_path / "annotated.pdf",
        query="Confidential",
        note="Review this page",
    )
    with pymupdf.open(output) as document:
        annotation_types = {annotation.type[1] for annotation in document[0].annots()}
    assert annotation_types == {"Highlight", "Text"}


def test_annotate_pdf_note_only(tmp_path: Path) -> None:
    output = annotate_pdf(_text_pdf(tmp_path / "source.pdf"), tmp_path / "note.pdf", note="Check")
    with pymupdf.open(output) as document:
        annotation_types = [annotation.type[1] for annotation in document[0].annots()]
    assert annotation_types == ["Text"]


def test_annotate_pdf_rejects_empty_input(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Masukkan teks"):
        annotate_pdf(_text_pdf(tmp_path / "source.pdf"), tmp_path / "out.pdf")


def test_annotate_pdf_rejects_unmatched_highlight(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="tidak ditemukan"):
        annotate_pdf(_text_pdf(tmp_path / "source.pdf"), tmp_path / "out.pdf", query="missing")
