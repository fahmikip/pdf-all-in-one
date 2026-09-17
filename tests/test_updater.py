import hashlib
import json
from pathlib import Path

import pytest
from core.utils.updater import check_for_update, download_installer, download_release_asset, version_tuple


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


class FakeStream:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = 8192
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


def test_version_tuple_supports_release_tags() -> None:
    assert version_tuple("v1.12.3") > version_tuple("1.9.9")


def test_update_is_returned_for_newer_release(monkeypatch) -> None:
    payload = {
        "tag_name": "v1.1.0",
        "name": "PDF Master 1.1",
        "html_url": "https://example.test/release",
        "published_at": "2026-08-02",
        "body": "Improvements",
    }
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeResponse(payload))
    result = check_for_update("1.0.0")
    assert result and result.version == "1.1.0" and result.release_url == "https://example.test/release"


def test_no_update_for_same_or_older_release(monkeypatch) -> None:
    monkeypatch.setattr(
        "core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeResponse({"tag_name": "v1.0.0"})
    )
    assert check_for_update("1.0.0") is None


def test_installer_asset_selected_and_zip_ignored(monkeypatch) -> None:
    payload = {
        "tag_name": "v2.0.0",
        "name": "PDF Master 2.0",
        "html_url": "https://example.test/release",
        "published_at": "2026-09-01",
        "body": "",
        "assets": [
            {
                "name": "PDF-Master-v2.0.0-Windows-x64.zip",
                "browser_download_url": "https://example.test/pack.zip",
                "size": 10,
            },
            {
                "name": "PDFMaster_Setup_v2.0.0.exe",
                "browser_download_url": "https://example.test/setup.exe",
                "size": 12345,
            },
        ],
    }
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeResponse(payload))
    result = check_for_update("1.0.0")
    assert result and result.installer is not None
    assert result.installer.name == "PDFMaster_Setup_v2.0.0.exe" and result.installer.size == 12345


def test_no_installer_asset_when_missing(monkeypatch) -> None:
    payload = {
        "tag_name": "v2.0.0",
        "assets": [{"name": "pack.zip", "browser_download_url": "https://example.test/pack.zip", "size": 10}],
    }
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeResponse(payload))
    assert check_for_update("1.0.0").installer is None


def test_checksums_asset_is_selected(monkeypatch) -> None:
    payload = {
        "tag_name": "v2.0.0",
        "assets": [
            {
                "name": "PDFMaster_Setup_v2.0.0.exe",
                "browser_download_url": "https://example.test/setup.exe",
                "size": 12345,
            },
            {
                "name": "SHA256SUMS.txt",
                "browser_download_url": "https://example.test/SHA256SUMS.txt",
                "size": 200,
            },
        ],
    }
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeResponse(payload))
    result = check_for_update("1.0.0")
    assert result.installer is not None
    assert result.checksum_asset is not None and result.checksum_asset.name == "SHA256SUMS.txt"


def test_download_release_asset_reports_progress_and_verifies(monkeypatch, tmp_path: Path) -> None:
    content = b"MZ" + b"\x00" * 4094
    asset_payload = {
        "name": "Setup.exe",
        "browser_download_url": "https://example.test/setup.exe",
        "size": len(content),
    }
    from core.utils.updater import ReleaseAsset

    asset = ReleaseAsset(asset_payload["name"], asset_payload["browser_download_url"], asset_payload["size"])
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeStream(content))
    progress: list = []
    target = download_release_asset(
        asset, tmp_path / "setup.exe", progress=lambda value, message: progress.append(value)
    )
    assert target.read_bytes() == content
    assert 100 in progress


def test_download_rejects_tampered_file(monkeypatch, tmp_path: Path) -> None:
    from core.utils.updater import ReleaseAsset

    asset = ReleaseAsset("Setup.exe", "https://example.test/setup.exe", 4096)
    monkeypatch.setattr(
        "core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeStream(b"not-a-pe" + b"\x00" * 16)
    )
    with pytest.raises(RuntimeError):
        download_release_asset(asset, tmp_path / "setup.exe")


def test_download_verifies_sha256_and_rejects_mismatch(monkeypatch, tmp_path: Path) -> None:
    from core.utils.updater import ReleaseAsset

    content = b"MZ" + b"\0" * 2046
    asset = ReleaseAsset("Setup.exe", "https://example.test/setup.exe", len(content))
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeStream(content))
    correct = hashlib.sha256(content).hexdigest()
    assert download_release_asset(asset, tmp_path / "ok.exe", sha256=correct).exists()
    with pytest.raises(RuntimeError):
        download_release_asset(asset, tmp_path / "bad.exe", sha256="0" * 64)
    assert not (tmp_path / "bad.exe").exists()


def test_download_installer_fetches_checksums_and_applies_hash(monkeypatch, tmp_path: Path) -> None:
    from core.utils.updater import ReleaseAsset, UpdateInfo

    content = b"MZ" + b"\0" * 2046
    digest = hashlib.sha256(content).hexdigest()
    checksums = f"{digest} *Setup.exe\n"
    responses = {
        "https://example.test/setup.exe": FakeStream(content),
        "https://example.test/SHA256SUMS.txt": FakeStream(checksums.encode()),
    }

    def fake_open(request, timeout):
        return responses.get(request.full_url, FakeStream(b""))

    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", fake_open)
    installer = ReleaseAsset("Setup.exe", "https://example.test/setup.exe", len(content))
    checksum_asset = ReleaseAsset("SHA256SUMS.txt", "https://example.test/SHA256SUMS.txt", len(checksums))
    update = UpdateInfo("2.0.0", "PDF Master 2.0", "https://example.test", "2026-09-01", "", installer, checksum_asset)
    target = download_installer(update, tmp_path / "verified.exe")
    assert target.read_bytes() == content


def test_download_installer_rejects_missing_checksum(monkeypatch, tmp_path: Path) -> None:
    from core.utils.updater import ReleaseAsset, UpdateInfo

    content = b"MZ" + b"\0" * 2046
    responses = {
        "https://example.test/setup.exe": FakeStream(content),
        "https://example.test/SHA256SUMS.txt": FakeStream(b""),
    }

    def fake_open(request, timeout):
        return responses.get(request.full_url, FakeStream(b""))

    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", fake_open)
    installer = ReleaseAsset("Setup.exe", "https://example.test/setup.exe", len(content))
    checksum_asset = ReleaseAsset("SHA256SUMS.txt", "https://example.test/SHA256SUMS.txt", 0)
    update = UpdateInfo("2.0.0", "PDF Master 2.0", "https://example.test", "2026-09-01", "", installer, checksum_asset)
    with pytest.raises(RuntimeError):
        download_installer(update, tmp_path / "never.exe")
    assert not (tmp_path / "never.exe").exists()


def test_version_tuple_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        version_tuple("no-digits-here")


def test_fetch_checksums_parses_and_normalizes(monkeypatch) -> None:
    from core.utils.updater import ReleaseAsset, fetch_checksums

    digest = "a" * 64
    content = f"{digest.upper()}  Setup.exe\n{digest} *pack.zip\nnot-a-checksum\n"
    monkeypatch.setattr(
        "core.utils.updater.urllib.request.urlopen", lambda request, timeout: FakeStream(content.encode())
    )
    asset = ReleaseAsset("SHA256SUMS.txt", "https://example.test/SHA256SUMS.txt", len(content))
    checksums = fetch_checksums(asset)
    assert checksums["Setup.exe"] == digest
    assert checksums["pack.zip"] == digest
    assert "not-a-checksum" not in checksums


def test_fetch_checksums_network_error(monkeypatch) -> None:
    import urllib.error

    from core.utils.updater import ReleaseAsset, fetch_checksums

    def fail(request, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", fail)
    with pytest.raises(RuntimeError):
        fetch_checksums(ReleaseAsset("SHA256SUMS.txt", "https://example.test/x", 0))


def test_check_for_update_handles_http_errors(monkeypatch) -> None:
    import urllib.error

    def not_found(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    def server_error(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 500, "Server Error", {}, None)

    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", not_found)
    assert check_for_update("1.0.0") is None
    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", server_error)
    with pytest.raises(RuntimeError):
        check_for_update("1.0.0")


def test_check_for_update_handles_network_failure(monkeypatch) -> None:
    import urllib.error

    def offline(request, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", offline)
    with pytest.raises(RuntimeError):
        check_for_update("1.0.0")


def test_download_installer_without_asset_raises(tmp_path: Path) -> None:
    from core.utils.updater import UpdateInfo

    update = UpdateInfo("2.0.0", "PDF Master 2.0", "https://example.test", "2026-09-01", "")
    with pytest.raises(RuntimeError):
        download_installer(update, tmp_path / "none.exe")


def test_download_release_asset_network_error(monkeypatch, tmp_path: Path) -> None:
    import urllib.error

    from core.utils.updater import ReleaseAsset

    def offline(request, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("core.utils.updater.urllib.request.urlopen", offline)
    asset = ReleaseAsset("Setup.exe", "https://example.test/setup.exe", 10)
    with pytest.raises(RuntimeError):
        download_release_asset(asset, tmp_path / "failed.exe")
    assert not (tmp_path / "failed.exe").exists()
