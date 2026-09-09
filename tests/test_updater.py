import json
from pathlib import Path

from core.utils.updater import check_for_update, download_release_asset, version_tuple


class FakeResponse:
    def __init__(self, payload: dict) -> None: self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self) -> bytes: return json.dumps(self.payload).encode()


class FakeStream:
    def __init__(self, content: bytes) -> None: self.content = content; self.offset = 0
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0: size = 8192
        chunk = self.content[self.offset:self.offset + size]; self.offset += len(chunk)
        return chunk


def test_version_tuple_supports_release_tags() -> None:
    assert version_tuple("v1.12.3") > version_tuple("1.9.9")


def test_update_is_returned_for_newer_release(monkeypatch) -> None:
    payload = {"tag_name": "v1.1.0", "name": "PDF Master 1.1", "html_url": "https://example.test/release", "published_at": "2026-08-02", "body": "Improvements"}
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeResponse(payload))
    result = check_for_update("1.0.0")
    assert result and result.version == "1.1.0" and result.release_url == "https://example.test/release"


def test_no_update_for_same_or_older_release(monkeypatch) -> None:
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeResponse({"tag_name": "v1.0.0"}))
    assert check_for_update("1.0.0") is None


def test_installer_asset_selected_and_zip_ignored(monkeypatch) -> None:
    payload = {
        "tag_name": "v2.0.0", "name": "PDF Master 2.0", "html_url": "https://example.test/release", "published_at": "2026-09-01", "body": "",
        "assets": [
            {"name": "PDF-Master-v2.0.0-Windows-x64.zip", "browser_download_url": "https://example.test/pack.zip", "size": 10},
            {"name": "PDFMaster_Setup_v2.0.0.exe", "browser_download_url": "https://example.test/setup.exe", "size": 12345},
        ],
    }
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeResponse(payload))
    result = check_for_update("1.0.0")
    assert result and result.installer is not None
    assert result.installer.name == "PDFMaster_Setup_v2.0.0.exe" and result.installer.size == 12345


def test_no_installer_asset_when_missing(monkeypatch) -> None:
    payload = {"tag_name": "v2.0.0", "assets": [{"name": "pack.zip", "browser_download_url": "https://example.test/pack.zip", "size": 10}]}
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeResponse(payload))
    assert check_for_update("1.0.0").installer is None


def test_download_release_asset_reports_progress_and_verifies(monkeypatch, tmp_path: Path) -> None:
    content = b"MZ" + b"\x00" * 4094
    asset_payload = {"name": "Setup.exe", "browser_download_url": "https://example.test/setup.exe", "size": len(content)}
    from core.utils.updater import ReleaseAsset
    asset = ReleaseAsset(asset_payload["name"], asset_payload["browser_download_url"], asset_payload["size"])
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeStream(content))
    progress: list = []
    target = download_release_asset(asset, tmp_path / "setup.exe", progress=lambda value, message: progress.append(value))
    assert target.read_bytes() == content
    assert 100 in progress


def test_download_rejects_tampered_file(monkeypatch, tmp_path: Path) -> None:
    from core.utils.updater import ReleaseAsset
    asset = ReleaseAsset("Setup.exe", "https://example.test/setup.exe", 4096)
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeStream(b"not-a-pe" + b"\x00" * 16))
    import pytest
    with pytest.raises(RuntimeError):
        download_release_asset(asset, tmp_path / "setup.exe")
