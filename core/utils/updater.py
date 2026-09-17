"""Privacy-conscious metadata-only GitHub release checker and installer downloader."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

API_URL = "https://api.github.com/repos/fahmikip/pdf-all-in-one/releases/latest"
USER_AGENT = "PDFMaster/{version}"
CHUNK_SIZE = 1 << 16

Progress = Callable[[int, str], None]


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    url: str
    size: int


@dataclass(frozen=True, slots=True)
class UpdateInfo:
    version: str
    name: str
    release_url: str
    published_at: str
    notes: str
    installer: ReleaseAsset | None = None
    checksum_asset: ReleaseAsset | None = None


def version_tuple(value: str) -> tuple[int, ...]:
    match = re.search(r"\d+(?:\.\d+)*", value)
    if not match:
        raise ValueError(f"Invalid version: {value}")
    return tuple(int(part) for part in match.group().split("."))


def _select_installer(assets: list[dict]) -> ReleaseAsset | None:
    for asset in assets:
        name = str(asset.get("name") or "")
        if name.lower().endswith(".exe") and "setup" in name.lower():
            return ReleaseAsset(name, str(asset.get("browser_download_url") or ""), int(asset.get("size") or 0))
    return None


def _select_checksums(assets: list[dict]) -> ReleaseAsset | None:
    for asset in assets:
        name = str(asset.get("name") or "")
        if name.upper() == "SHA256SUMS.TXT":
            return ReleaseAsset(name, str(asset.get("browser_download_url") or ""), int(asset.get("size") or 0))
    return None


def fetch_checksums(asset: ReleaseAsset, *, timeout: float = 15.0) -> dict[str, str]:
    """Download a SHA256SUMS.txt asset and map each filename to its hex digest."""
    request = urllib.request.Request(
        asset.url, headers={"Accept": "application/octet-stream", "User-Agent": USER_AGENT.format(version="updater")}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content = response.read().decode("utf-8-sig", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Could not download the release checksums.") from exc
    checksums: dict[str, str] = {}
    for line in content.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and len(parts[0]) == 64:
            checksums[parts[1].lstrip("*")] = parts[0].lower()
    return checksums


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_for_update(current_version: str, *, timeout: float = 8.0) -> UpdateInfo | None:
    request = urllib.request.Request(
        API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT.format(version=current_version),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError("GitHub update service is temporarily unavailable.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Could not connect to GitHub to check for updates.") from exc
    tag = str(payload.get("tag_name", ""))
    latest = version_tuple(tag)
    if latest <= version_tuple(current_version):
        return None
    installer = _select_installer(payload.get("assets") or [])
    return UpdateInfo(
        ".".join(str(part) for part in latest),
        str(payload.get("name") or tag),
        str(payload.get("html_url") or "https://github.com/fahmikip/pdf-all-in-one/releases"),
        str(payload.get("published_at") or ""),
        str(payload.get("body") or "")[:1500],
        installer,
        _select_checksums(payload.get("assets") or []),
    )


def _human_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def download_release_asset(
    asset: ReleaseAsset,
    destination: str | Path,
    *,
    sha256: str | None = None,
    progress: Progress | None = None,
    timeout: float = 180.0,
) -> Path:
    target = Path(destination).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        asset.url, headers={"Accept": "application/octet-stream", "User-Agent": USER_AGENT.format(version="updater")}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, target.open("wb") as stream:
            downloaded = 0
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                stream.write(chunk)
                downloaded += len(chunk)
                if asset.size and progress:
                    progress(
                        min(99, int(downloaded / asset.size * 100)),
                        f"Downloading {asset.name} ({_human_size(downloaded)} / {_human_size(asset.size)})",
                    )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        target.unlink(missing_ok=True)
        raise RuntimeError("Could not download the update installer.") from exc
    if asset.size and target.stat().st_size != asset.size:
        target.unlink(missing_ok=True)
        raise RuntimeError("The downloaded installer is incomplete or corrupted.")
    if sha256 is not None and _sha256(target) != sha256.lower():
        target.unlink(missing_ok=True)
        raise RuntimeError(
            "The downloaded installer failed SHA-256 verification. The file was deleted and nothing was run."
        )
    with target.open("rb") as handle:
        if handle.read(2) != b"MZ":
            target.unlink(missing_ok=True)
            raise RuntimeError("The downloaded file is not a valid Windows installer.")
    if progress:
        progress(100, target.name)
    return target


def download_installer(
    update: UpdateInfo,
    destination: str | Path,
    *,
    progress: Progress | None = None,
    timeout: float = 180.0,
) -> Path:
    """Download and verify the release installer against its published SHA-256 checksum."""
    if update.installer is None:
        raise RuntimeError("No installer is available for this release.")
    sha256: str | None = None
    if update.checksum_asset is not None:
        checksums = fetch_checksums(update.checksum_asset, timeout=timeout)
        sha256 = checksums.get(update.installer.name)
        if sha256 is None:
            raise RuntimeError(f"The release checksum for {update.installer.name} is missing.")
    return download_release_asset(update.installer, destination, sha256=sha256, progress=progress, timeout=timeout)
