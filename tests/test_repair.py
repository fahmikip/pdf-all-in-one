import shutil
import subprocess
from pathlib import Path

import pikepdf
import pymupdf
import pytest
from core.pdf.repair import linearize_pdf, repair_pdf
from core.utils.validation import ValidationError


def _damaged_pdf(sample_pdf: Path, tmp_path: Path) -> Path:
    damaged = tmp_path / "damaged.pdf"
    damaged.write_bytes(sample_pdf.read_bytes() + b"\x00CORRUPTED-TAIL" * 200)
    return damaged


def test_linearize_pdf(sample_pdf: Path, tmp_path: Path) -> None:
    result = linearize_pdf(sample_pdf, tmp_path / "web.pdf")
    assert result.exists()
    with pymupdf.open(result) as document:
        assert document.page_count == 3


def test_linearize_progress(sample_pdf: Path, tmp_path: Path) -> None:
    progress: list[int] = []
    linearize_pdf(sample_pdf, tmp_path / "web.pdf", progress=lambda value, _detail: progress.append(value))
    assert progress[-1] == 100


def test_repair_appended_garbage(sample_pdf: Path, tmp_path: Path) -> None:
    damaged = _damaged_pdf(sample_pdf, tmp_path)
    result = repair_pdf(damaged, tmp_path / "fixed.pdf")
    with pymupdf.open(result) as document:
        assert document.page_count == 3


def test_repair_truncated_file(sample_pdf: Path, tmp_path: Path) -> None:
    truncated = tmp_path / "truncated.pdf"
    truncated.write_bytes(sample_pdf.read_bytes()[:-400])
    result = repair_pdf(truncated, tmp_path / "fixed.pdf")
    with pymupdf.open(result) as document:
        assert document.page_count >= 1


def test_repair_missing_source_raises(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        repair_pdf(tmp_path / "missing.pdf", tmp_path / "out.pdf")


def test_repair_output_must_be_new_file(sample_pdf: Path) -> None:
    copy = sample_pdf.with_name("copy.pdf")
    copy.write_bytes(sample_pdf.read_bytes())
    with pytest.raises(ValueError):
        repair_pdf(copy, copy)


def test_repair_via_qpdf_binary(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "qpdf" if name == "qpdf" else None)

    def fake_run(args, **_kwargs):
        shutil.copyfile(args[1], args[2])
        return type("Result", (), {"returncode": 0, "stderr": ""})

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = repair_pdf(sample_pdf, tmp_path / "fixed.pdf")
    with pymupdf.open(result) as document:
        assert document.page_count == 3


def test_repair_qpdf_failure(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "qpdf" if name == "qpdf" else None)

    def fake_run(args, **_kwargs):
        return type("Result", (), {"returncode": 1, "stderr": "boom"})

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        repair_pdf(sample_pdf, tmp_path / "fixed.pdf")


def test_repair_pymupdf_fallback(sample_pdf: Path, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)

    def failing_open(*_args, **_kwargs):
        raise pikepdf.PdfError("recovery refused")

    monkeypatch.setattr(pikepdf, "open", failing_open)
    result = repair_pdf(sample_pdf, tmp_path / "fixed.pdf")
    with pymupdf.open(result) as document:
        assert document.page_count == 3