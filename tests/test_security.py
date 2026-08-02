from pathlib import Path

import fitz
import pytest

from core.pdf.security import password_strength, protect_pdf, unlock_pdf
from core.utils.validation import ValidationError, validate_pdf


def test_protect_and_unlock_pdf(sample_pdf: Path, tmp_path: Path) -> None:
    protected = protect_pdf(sample_pdf, tmp_path / "protected.pdf", "Strong-Pass-42", allow_copying=False, allow_editing=False)
    assert validate_pdf(protected, allow_encrypted=True).encrypted
    with pytest.raises(ValidationError):
        validate_pdf(protected)
    unlocked = unlock_pdf(protected, tmp_path / "unlocked.pdf", "Strong-Pass-42")
    info = validate_pdf(unlocked)
    assert info.pages == 3 and not info.encrypted
    with fitz.open(unlocked) as document:
        assert "Page 1" in document[0].get_text()


def test_wrong_password_is_rejected(sample_pdf: Path, tmp_path: Path) -> None:
    protected = protect_pdf(sample_pdf, tmp_path / "protected.pdf", "correct-password")
    with pytest.raises(ValidationError):
        unlock_pdf(protected, tmp_path / "wrong.pdf", "incorrect-password")
    assert not (tmp_path / "wrong.pdf").exists()


def test_password_strength() -> None:
    assert password_strength("abc")[1] == "Weak"
    assert password_strength("Long-Strong-Password-42")[1] == "Strong"
