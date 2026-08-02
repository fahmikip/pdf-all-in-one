@echo off
setlocal
cd /d "%~dp0"
if not exist "dist\PDF-Master\PDFMaster.exe" call build.bat
if errorlevel 1 exit /b 1
call .venv\Scripts\activate.bat
python installer\prepare_assets.py
if errorlevel 1 exit /b 1
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo Inno Setup 6 was not found. Install it, then run installer.bat again.
  exit /b 1
)
"%ISCC%" installer\setup.iss
