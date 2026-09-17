# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPEC).resolve().parent
icon = root / "assets" / "logo" / "logo.ico"

a = Analysis(
    [str(root / "app" / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "version.txt"), "."), (str(root / "assets"), "assets")],
    hiddenimports=[],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PDFMaster",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX-packed executables frequently trip antivirus heuristics (false positives).
    # Keep UPX disabled so Defender / other AVs stop flagging the bundled launcher.
    upx=False,
    console=False,
    icon=str(icon) if icon.exists() else None,
    version=str(root / "installer" / "version_info.txt"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PDF-Master")
