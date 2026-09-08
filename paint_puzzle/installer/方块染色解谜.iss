; 方块染色解谜 安装脚本(Inno Setup 6)
; 编译:ISCC.exe installer\方块染色解谜.iss
; 产物:installer_out\方块染色解谜-Setup.exe(标准安装向导,可选择安装目录)
; 卸载:由 Inno 生成 unins000.exe(GUI),自动注册到 HKCU 卸载表,
;       出现在 "设置 → 应用 → 已安装的应用",点"卸载"即启动卸载向导。

#define MyAppName "方块染色解谜"
#define MyAppVersion "2.2"
#define MyAppPublisher "PaintPuzzle"

[Setup]
AppId=PaintPuzzle
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
; 按用户安装,免管理员,默认装到 %LOCALAPPDATA%\Programs\方块染色解谜
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=yes
; 安装包图标与程序一致
SetupIconFile=..\icon.ico
; 卸载项在"设置→应用"中显示的图标 = 游戏 exe
UninstallDisplayIcon={app}\方块染色解谜.exe
OutputDir=D:\Mini programme\paint_puzzle\installer_out
OutputBaseFilename={#MyAppName}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
VersionInfoVersion=2.2.0.0

[Languages]
Name: "chinesesimp"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked

[Files]
Source: "..\dist\方块染色解谜.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\方块染色解谜.exe"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\方块染色解谜.exe"; Tasks: desktopicon
