# PDF Master

**PDF Master** is an offline-first, all-in-one PDF toolkit for Windows, built with Python 3.12 and PySide6. Every document operation runs on your own machine — nothing is uploaded, and no tracking or telemetry is included.

Current version: **v1.1.0**

---

## Features

| Category | Tool | What it does |
| --- | --- | --- |
| PDF Tools | Compress PDF | Reduce file size with Low / Recommended / High / Maximum profiles; aggressive mode, produces no copy when already optimized |
| PDF Tools | Merge PDF | Combine two or more PDFs, drag to reorder |
| PDF Tools | Split PDF | Split every page, every N pages, or extract a specific range (e.g. `1-3, 5`) |
| PDF Tools | Organize PDF | Reorder, rotate, and remove pages |
| PDF Tools | Extract PDF | Export selectable text to `.txt` or embedded images to PNG / JPG / WEBP |
| Convert | Convert Files | Image→PDF, PDF→JPG/PNG/WebP, Word/Excel/PowerPoint→PDF (LibreOffice), PDF→Word, PDF→Excel |
| Edit | Watermark & More | Text/image watermarks, page numbers, headers & footers, metadata editing |
| Security | Protect / Unlock | PDF password protection and authorized unlocking |
| OCR | OCR PDF / Image | Make scanned documents searchable (requires Tesseract) |
| Advanced | Batch Processing | Run the same operation on many files |
| More | History | Local, document-content-free operation history with storage-saved stats |
| More | Settings | Preferences, LibreOffice / Tesseract detection, update checks (notifications only, never auto-download) |
| More | About Developer | Developer branding and version info |

All new edits are written to **new files** — your originals are never modified.

## System requirements

- Windows 10/11 (64-bit)
- Python 3.12 when running from source
- Optional external tools (detected separately, not bundled):
  - **LibreOffice** — Office (Word/Excel/PowerPoint) → PDF conversion
  - **Tesseract** — OCR engine

## Run from source

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app\main.py
```

Run the test suite with `python -m pytest`.

## Quick usage guide

1. **Compress a PDF**
   Choose **Compress PDF** → drag your file into the drop zone → pick a compression level → **Compress PDF** → select a save location. The result opens in Explorer.

2. **Merge PDFs**
   Choose **Merge PDF** → add two or more files → drag them in the list into the order you want → **Merge PDF**.

3. **Split / extract pages**
   Choose **Split PDF** → pick *Every page*, *Every N pages*, or *Page range* (e.g. `1-3, 5`) → run and choose the output folder.

4. **Extract text or images**
   Choose **Extract PDF** → either *Text to .txt* (saves a readable text file with page markers) or *Images to files* (PNG/JPG/WEBP, with an optional minimum size filter).

5. **PDF to Excel**
   Choose **Convert Files** → select *PDF to Excel* → add your PDF → choose where to save the `.xlsx`. Tables are detected automatically — one worksheet per table, with headings highlighted.

6. **PDF to Word**
   Choose **Convert Files** → *PDF to Word* → add a PDF → save as `.docx`. Best-effort conversion: text, paragraphs, and images are prioritized; very complex layouts may not be pixel-perfect.

7. **Protect or unlock**
   Choose **Protect / Unlock** → set a password to encrypt, or provide the correct password to remove protection.

8. **OCR a scan**
   Choose **OCR PDF / Image** → point PDF Master to your Tesseract install if needed, then select a scan to make it searchable.

## Building the portable release

```powershell
build.bat            # runs tests, prepares assets, builds dist\PDF-Master\PDFMaster.exe
installer.bat        # additionally builds the Inno Setup installer (requires Inno Setup 6)
```

## Privacy

PDF Master processes documents **locally**. It contains no telemetry or analytics and does not upload document contents, filenames, or activity. Optional update checks query GitHub for a newer version number only, and downloads never happen without your permission.

## Developer

Developed by **Fahmikip** · https://github.com/fahmikip · © 2026 Fahmikip

Portable Windows builds: see the **Releases** page.