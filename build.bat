@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python -m pytest
if errorlevel 1 exit /b 1
if exist "build\PDFMaster" rmdir /s /q "build\PDFMaster"
if exist "dist\PDF-Master" rmdir /s /q "dist\PDF-Master"
pyinstaller --noconfirm PDFMaster.spec
if errorlevel 1 exit /b 1
echo Build complete: dist\PDF-Master\PDFMaster.exe
