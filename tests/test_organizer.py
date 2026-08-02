from pathlib import Path

from ui.pages.organizer import render_thumbnails


def test_thumbnail_renderer(sample_pdf: Path) -> None:
    progress: list[int] = []
    images = render_thumbnails(sample_pdf, lambda value, detail: progress.append(value))
    assert len(images) == 3
    assert all(not image.isNull() for image in images)
    assert progress[-1] == 100
