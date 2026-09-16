"""Extend OCR engine coverage with a scripted fake Tesseract."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from core.ocr.ocr_engine import OcrUnavailableError, available_languages, find_tesseract, ocr_image, ocr_pdf


class FakeRun:
    """Replicates Tesseract: --list-langs or an OCR command that writes output."""

    def __init__(self) -> None:
        self.lang_stdout = "Available languages for the following:\neng\nosd\n"
        self.returncode = 0
        self.ocr_returncode = 0
        self.stderr = ""
        self.commands: list[list[str]] = []

    def __call__(
        self, command: list[str], *, capture_output=True, text=True, timeout=600, check=False, creationflags=0
    ):
        self.commands.append(command)
        if "--list-langs" in command:
            return type(
                "Result", (), {"returncode": self.returncode, "stdout": self.lang_stdout, "stderr": self.stderr}
            )()
        result = type("Result", (), {"returncode": self.ocr_returncode, "stdout": "", "stderr": self.stderr})()
        if self.ocr_returncode != 0:
            return result
        output_format = command[-1]
        if output_format == "pdf":
            document = pymupdf.open()
            page = document.new_page()
            page.insert_image(pymupdf.Rect(0, 0, page.rect.width, page.rect.height), filename=str(command[1]))
            document.save(str(Path(command[2]).with_suffix(".pdf")))
            document.close()
        else:
            Path(command[2] + ".txt").write_text("recognized", encoding="utf-8")
        return result


@pytest.fixture
def fake_tesseract(tmp_path: Path, monkeypatch) -> tuple[Path, FakeRun]:
    executable = tmp_path / "tesseract.exe"
    executable.write_bytes(b"MZ")
    runner = FakeRun()
    monkeypatch.setattr("core.ocr.ocr_engine.subprocess.run", runner)
    return executable, runner


def _png(path: Path) -> Path:
    from PIL import Image

    Image.new("RGB", (80, 60), (120, 40, 40)).save(path)
    return path


def test_find_tesseract_uses_manual_path(fake_tesseract) -> None:
    executable, _ = fake_tesseract
    assert find_tesseract(executable) == executable.resolve()


def test_available_languages_parses_output(fake_tesseract) -> None:
    executable, _ = fake_tesseract
    assert available_languages(executable) == ["eng", "osd"]


def test_available_languages_empty_on_error(fake_tesseract) -> None:
    executable, runner = fake_tesseract
    runner.returncode = 1
    assert available_languages(executable) == []


def test_ocr_image_rejects_missing_file(fake_tesseract, tmp_path: Path) -> None:
    executable, _ = fake_tesseract
    with pytest.raises(ValueError):
        ocr_image(tmp_path / "missing.png", tmp_path / "out.txt", executable=executable)


def test_ocr_image_rejects_wrong_suffix(fake_tesseract, tmp_path: Path) -> None:
    executable, _ = fake_tesseract
    source = _png(tmp_path / "photo.png")
    with pytest.raises(ValueError):
        ocr_image(source, tmp_path / "out.pdf", executable=executable)


def test_ocr_image_rejects_missing_language(fake_tesseract, tmp_path: Path, monkeypatch) -> None:
    executable, runner = fake_tesseract
    runner.lang_stdout = ""
    source = _png(tmp_path / "photo.png")
    with pytest.raises(ValueError):
        ocr_image(source, tmp_path / "out.txt", language="eng", executable=executable)


def test_ocr_image_writes_txt_on_success(fake_tesseract, tmp_path: Path) -> None:
    executable, runner = fake_tesseract
    source = _png(tmp_path / "photo.png")
    destination = tmp_path / "out.txt"
    progress: list[tuple[int, str]] = []
    result = ocr_image(source, destination, executable=executable, progress=lambda v, d: progress.append((v, d)))
    assert result == destination.resolve()
    assert destination.read_text(encoding="utf-8") == "recognized"
    assert len(runner.commands) == 2
    assert progress and progress[-1] == (100, source.name)


def test_ocr_image_writes_pdf_with_pdf_format(fake_tesseract, tmp_path: Path) -> None:
    executable, _ = fake_tesseract
    source = _png(tmp_path / "photo.png")
    destination = tmp_path / "out.pdf"
    result = ocr_image(source, destination, output_format="pdf", executable=executable)
    assert result == destination.resolve()
    with pymupdf.open(destination) as document:
        assert document.page_count == 1


def test_ocr_image_raises_when_tesseract_fails(fake_tesseract, tmp_path: Path) -> None:
    executable, runner = fake_tesseract
    runner.ocr_returncode = 1
    runner.stderr = "boom"
    source = _png(tmp_path / "photo.png")
    with pytest.raises(RuntimeError, match="boom"):
        ocr_image(source, tmp_path / "out.txt", executable=executable)


def test_ocr_pdf_rejects_invalid_format(fake_tesseract, sample_pdf: Path, tmp_path: Path) -> None:
    executable, _ = fake_tesseract
    with pytest.raises(ValueError):
        ocr_pdf(sample_pdf, tmp_path / "out.pdf", output_format="html", executable=executable)


def test_ocr_pdf_rejects_overwrite(fake_tesseract, sample_pdf: Path, tmp_path: Path) -> None:
    executable, _ = fake_tesseract
    with pytest.raises(ValueError):
        ocr_pdf(sample_pdf, sample_pdf, executable=executable)


def test_ocr_pdf_txt_output(fake_tesseract, sample_pdf: Path, tmp_path: Path) -> None:
    destination = tmp_path / "text.txt"
    progress: list[tuple[int, str]] = []
    result = ocr_pdf(
        sample_pdf,
        destination,
        output_format="txt",
        executable=fake_tesseract[0],
        progress=lambda v, d: progress.append((v, d)),
    )
    assert result == destination.resolve()
    assert destination.read_text(encoding="utf-8").count("recognized") == 3
    assert progress[-1] == (100, destination.name)


def test_ocr_pdf_txt_rejects_non_txt_destination(fake_tesseract, sample_pdf: Path, tmp_path: Path) -> None:
    executable, _ = fake_tesseract
    with pytest.raises(ValueError):
        ocr_pdf(sample_pdf, tmp_path / "out.html", output_format="txt", executable=executable)


def test_ocr_pdf_pdf_single_page(fake_tesseract, tmp_path: Path) -> None:
    one_page = tmp_path / "one.pdf"
    document = pymupdf.open()
    document.new_page(width=300, height=400)
    document.save(one_page)
    document.close()
    destination = tmp_path / "out.pdf"
    result = ocr_pdf(one_page, destination, executable=fake_tesseract[0])
    assert result == destination.resolve()
    with pymupdf.open(destination) as merged:
        assert merged.page_count == 1


def test_ocr_pdf_pdf_multi_page_merges(fake_tesseract, sample_pdf: Path, tmp_path: Path) -> None:
    destination = tmp_path / "merged.pdf"
    result = ocr_pdf(sample_pdf, destination, executable=fake_tesseract[0])
    assert result == destination.resolve()
    with pymupdf.open(destination) as merged:
        assert merged.page_count == 3


def test_ocr_unavailable_without_manual_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("core.ocr.ocr_engine.shutil.which", lambda name: None)
    monkeypatch.setattr("core.ocr.ocr_engine.Path.is_file", lambda self: False)
    with pytest.raises(OcrUnavailableError):
        ocr_image(tmp_path / "photo.png", tmp_path / "out.txt")
    with pytest.raises(OcrUnavailableError):
        ocr_pdf(tmp_path / "in.pdf", tmp_path / "out.pdf")


def test_ocr_pdf_raises_when_tesseract_fails(fake_tesseract, sample_pdf: Path, tmp_path: Path) -> None:
    executable, runner = fake_tesseract
    runner.ocr_returncode = 1
    runner.stderr = "page failed"
    with pytest.raises(RuntimeError, match="page failed"):
        ocr_pdf(sample_pdf, tmp_path / "out.pdf", executable=executable)
