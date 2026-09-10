#define MyAppName "PDF Master"
#define MyAppVersion "1.4.0"
#define MyAppPublisher "Fahmikip"
#define MyAppURL "https://github.com/fahmikip"
#define MyAppExeName "PDFMaster.exe"

[Setup]
AppId={{5F50140D-DC3F-4B63-B9B5-8B0939D57F50}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\PDF Master
DefaultGroupName=PDF Master
LicenseFile=..\LICENSE
OutputDir=..\dist\installer
OutputBaseFilename=PDFMaster_Setup_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\assets\logo\logo.ico
WizardImageFile=installer_side.bmp
WizardSmallImageFile=installer_banner.bmp

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\PDF-Master\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PDF Master"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\PDF Master"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch PDF Master"; Flags: nowait postinstall skipifsilent
