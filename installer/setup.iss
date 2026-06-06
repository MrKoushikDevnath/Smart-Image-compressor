[Setup]
AppName=Smart Image Compressor Pro
AppVersion=1.0
AppPublisher=Mr. Koushik Devnath
AppPublisherURL=https://github.com/
VersionInfoCompany=Mr. Koushik Devnath
VersionInfoDescription=Smart Image Compressor Pro made by Mr. Koushik Devnath
VersionInfoProductName=Smart Image Compressor Pro
DefaultDirName={autopf}\Smart Image Compressor Pro
DefaultGroupName=Smart Image Compressor Pro
OutputDir=..\
OutputBaseFilename=SmartImageCompressorPro_Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=yes

[Files]
Source: "..\dist\SmartImageCompressorPro.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Smart Image Compressor Pro"; Filename: "{app}\SmartImageCompressorPro.exe"
Name: "{group}\{cm:UninstallProgram,Smart Image Compressor Pro}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Smart Image Compressor Pro"; Filename: "{app}\SmartImageCompressorPro.exe"

[Run]
Filename: "{app}\SmartImageCompressorPro.exe"; Description: "{cm:LaunchProgram,Smart Image Compressor Pro}"; Flags: nowait postinstall skipifsilent
