from pathlib import Path

import fitz
import pytest


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    document = fitz.open()
    for index in range(3):
        page = document.new_page(width=300, height=400)
        page.insert_text((40, 60), f"Page {index + 1}", fontsize=18)
    document.set_metadata({"title": "Original", "author": "Test"})
    document.save(path)
    document.close()
    return path
