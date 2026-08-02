import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.bootstrap import create_application


def test_main_window_starts() -> None:
    app, window = create_application(["pdf-master-test"])
    assert window.windowTitle().startswith("PDF Master")
    assert window.minimumWidth() == 1024
    assert window.pages["compress"].__class__.__name__ == "CompressPage"
    assert window.pages["merge"].__class__.__name__ == "MergePage"
    assert window.pages["split"].__class__.__name__ == "SplitPage"
    assert window.pages["organize"].__class__.__name__ == "OrganizerPage"
    assert window.pages["convert"].__class__.__name__ == "ConverterPage"
    assert window.pages["edit"].__class__.__name__ == "EditPage"
    assert window.pages["security"].__class__.__name__ == "SecurityPage"
    assert window.pages["history"].__class__.__name__ == "HistoryPage"
    assert window.pages["settings"].__class__.__name__ == "SettingsPage"
    assert window.pages["ocr"].__class__.__name__ == "OcrPage"
    window.close()
    app.quit()
