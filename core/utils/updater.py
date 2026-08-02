"""Privacy-conscious metadata-only GitHub release checker."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

API_URL = "https://api.github.com/repos/fahmikip/pdf-all-in-one/releases/latest"


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    version: str
    name: str
    release_url: str
    published_at: str
    notes: str


def version_tuple(value: str) -> tuple[int, ...]:
    match = re.search(r"\d+(?:\.\d+)*", value)
    if not match: raise ValueError(f"Invalid version: {value}")
    return tuple(int(part) for part in match.group().split("."))


def check_for_update(current_version: str, *, timeout: float = 8.0) -> UpdateInfo | None:
    request = urllib.request.Request(API_URL, headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": f"PDFMaster/{current_version}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404: return None
        raise RuntimeError("GitHub update service is temporarily unavailable.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Could not connect to GitHub to check for updates.") from exc
    tag = str(payload.get("tag_name", "")); latest = version_tuple(tag)
    if latest <= version_tuple(current_version): return None
    return UpdateInfo(".".join(str(part) for part in latest), str(payload.get("name") or tag), str(payload.get("html_url") or "https://github.com/fahmikip/pdf-all-in-one/releases"), str(payload.get("published_at") or ""), str(payload.get("body") or "")[:1500])
