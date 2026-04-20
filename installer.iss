; Inno Setup script for ANONYMIZER ROSSILBER.
; Packages the PyInstaller one-folder build into a single installer .exe.

#define MyAppName "Anonymizer Rossilber"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Patrushev E."
#define MyAppExeName "Anonymizer.exe"

[Setup]
AppId={{2A9E3B7C-0F11-4F1B-9C7E-0E4A8C2F1E55}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppCopyright=© 2026 Patrushev E. All rights reserved.
DefaultDirName={autopf}\Anonymizer Rossilber
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
OutputDir=dist_installer
OutputBaseFilename=AnonymizerRossilber-Setup-{#MyAppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
LicenseFile=LICENSE

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Pull the entire PyInstaller one-folder output.
Source: "dist\Anonymizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
