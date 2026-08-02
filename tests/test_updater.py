import json

from core.utils.updater import check_for_update, version_tuple


class FakeResponse:
    def __init__(self, payload: dict) -> None: self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self) -> bytes: return json.dumps(self.payload).encode()


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
