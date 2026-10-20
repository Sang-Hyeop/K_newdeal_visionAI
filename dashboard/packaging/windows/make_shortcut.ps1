# Windows 공용: 바탕화면에 시선 바로가기 생성 (프로젝트 상대 경로만 사용)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..")).ProviderPath
$Ico = Join-Path $Root "dashboard\packaging\icons\sisun.ico"
$IconLocation = Join-Path $env:SystemRoot "System32\shell32.dll"
$IconLocation += ",0"
if (Test-Path -LiteralPath $Ico -PathType Leaf) {
    $IconLocation = $Ico + ",0"
} else {
    Write-Warning "시선 아이콘이 없어 Windows 기본 아이콘을 사용합니다: $Ico"
}
$Desktop = [Environment]::GetFolderPath("Desktop")
if (-not (Test-Path -LiteralPath $Desktop -PathType Container)) {
    [void][System.IO.Directory]::CreateDirectory($Desktop)
}
$Lnk = Join-Path $Desktop "시선.lnk"

$Vbs = Join-Path $Root "시선.vbs"
$ExeRoot = Join-Path $Root "Sisun.exe"
$ExeDist = Join-Path $Root "dist\sisun\sisun.exe"
$DesktopPy = Join-Path $Root "dashboard_desktop.py"

if (-not (Test-Path -LiteralPath $DesktopPy)) {
    Write-Error "dashboard_desktop.py 없음: $Root"
}

$Target = $null
$Arguments = ""
if (Test-Path -LiteralPath $Vbs) {
    $Target = Join-Path $env:SystemRoot "System32\wscript.exe"
    $Arguments = '"' + $Vbs + '"'
}
elseif (Test-Path -LiteralPath $ExeDist) { $Target = $ExeDist }
elseif (Test-Path -LiteralPath $ExeRoot) { $Target = $ExeRoot }
else {
    Write-Error "실행 대상 없음. 루트에 시선.vbs 가 필요합니다: $Root"
}

# Unicode 전용 ShellLinkW로 시스템 코드페이지와 무관하게 한글 경로를 저장합니다.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
[ComImport, Guid("00021401-0000-0000-C000-000000000046")]
class SisunShellLink { }
[ComImport, Guid("000214F9-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface ISisunShellLinkW {
    void GetPath(IntPtr file, int count, IntPtr data, uint flags);
    void GetIDList(out IntPtr id);
    void SetIDList(IntPtr id);
    void GetDescription(IntPtr text, int count);
    void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string text);
    void GetWorkingDirectory(IntPtr text, int count);
    void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string path);
    void GetArguments(IntPtr text, int count);
    void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string text);
    void GetHotkey(out short key);
    void SetHotkey(short key);
    void GetShowCmd(out int command);
    void SetShowCmd(int command);
    void GetIconLocation(IntPtr path, int count, out int index);
    void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string path, int index);
    void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string path, uint reserved);
    void Resolve(IntPtr window, uint flags);
    void SetPath([MarshalAs(UnmanagedType.LPWStr)] string path);
}
public static class SisunShortcutWriter {
    public static void Verify(string link, string root, string args) {
        object instance = new SisunShellLink();
        IntPtr buffer = Marshal.AllocHGlobal(65536);
        try {
            ((IPersistFile)instance).Load(link, 0);
            var shortcut = (ISisunShellLinkW)instance;
            shortcut.GetWorkingDirectory(buffer, 32768);
            if (Marshal.PtrToStringUni(buffer) != root) throw new InvalidOperationException("Wrong working directory");
            shortcut.GetArguments(buffer, 32768);
            if (Marshal.PtrToStringUni(buffer) != args) throw new InvalidOperationException("Wrong launcher arguments");
        } finally { Marshal.FreeHGlobal(buffer); Marshal.FinalReleaseComObject(instance); }
    }
    public static void Save(string link, string target, string args, string root, string icon, string description) {
        object instance = new SisunShellLink();
        try {
            var shortcut = (ISisunShellLinkW)instance;
            shortcut.SetPath(target);
            shortcut.SetArguments(args);
            shortcut.SetWorkingDirectory(root);
            shortcut.SetDescription(description);
            shortcut.SetShowCmd(7);
            shortcut.SetIconLocation(icon, 0);
            ((IPersistFile)instance).Save(link, true);
        } finally { Marshal.FinalReleaseComObject(instance); }
    }
}
'@
$IconPath = $IconLocation.Substring(0, $IconLocation.LastIndexOf(','))
[SisunShortcutWriter]::Save($Lnk, $Target, $Arguments, $Root, $IconPath, "시선 안전관제")
Write-Host "바로가기:" $Lnk
Write-Host "대상:" $Target
Write-Host "아이콘:" $IconLocation
