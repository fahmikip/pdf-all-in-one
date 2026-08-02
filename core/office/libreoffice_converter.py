"""Local Office conversion through LibreOffice headless."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from core.utils.file_utils import atomic_output

OFFICE_EXTENSIONS = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}


class LibreOfficeUnavailableError(RuntimeError): pass


def find_libreoffice(manual_path: str | Path | None = None) -> Path | None:
    candidates = [manual_path, shutil.which("soffice"), r"C:\Program Files\LibreOffice\program\soffice.exe", r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]
    return next((Path(value).resolve() for value in candidates if value and Path(value).is_file()), None)


def office_to_pdf(source: str | Path, destination: str | Path, *, executable: str | Path | None = None, progress=None) -> Path:
    libreoffice = find_libreoffice(executable)
    if not libreoffice: raise LibreOfficeUnavailableError("LibreOffice is required for Office conversion. Install it or locate soffice.exe in Settings.")
    document = Path(source).resolve(); output = Path(destination).resolve()
    if not document.is_file() or document.suffix.lower() not in OFFICE_EXTENSIONS: raise ValueError("Select a supported Word, Excel, or PowerPoint file.")
    if output.suffix.lower() != ".pdf": raise ValueError("Office conversion output must use .pdf.")
    if progress: progress(10, "Starting LibreOffice")
    with tempfile.TemporaryDirectory(prefix="pdfmaster-office-") as directory:
        work = Path(directory); profile = (work / "profile").as_uri()
        command = [str(libreoffice), "--headless", "--nologo", "--nodefault", "--nofirststartwizard", f"-env:UserInstallation={profile}", "--convert-to", "pdf", "--outdir", str(work), str(document)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=False, creationflags=subprocess.CREATE_NO_WINDOW)
        generated = work / f"{document.stem}.pdf"
        if result.returncode or not generated.exists(): raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "LibreOffice conversion failed.")
        if progress: progress(90, "Finalizing PDF")
        with atomic_output(output) as temporary: shutil.copyfile(generated, temporary)
    if progress: progress(100, output.name)
    return output
