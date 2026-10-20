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
$Lnk = Join-Path $Desktop "시선.lnk"

$Vbs = Join-Path $Root "시선.vbs"
$ExeRoot = Join-Path $Root "Sisun.exe"
$ExeDist = Join-Path $Root "dist\sisun\sisun.exe"
$DesktopPy = Join-Path $Root "dashboard_desktop.py"

if (-not (Test-Path -LiteralPath $DesktopPy)) {
    Write-Error "dashboard_desktop.py 없음: $Root"
}

$Target = $null
if (Test-Path -LiteralPath $ExeDist) { $Target = $ExeDist }
elseif (Test-Path -LiteralPath $ExeRoot) { $Target = $ExeRoot }
elseif (Test-Path -LiteralPath $Vbs) { $Target = $Vbs }
else {
    Write-Error "실행 대상 없음. 루트에 시선.vbs 가 필요합니다: $Root"
}

$W = New-Object -ComObject WScript.Shell
if (Test-Path -LiteralPath $Lnk) { Remove-Item -LiteralPath $Lnk -Force }
$S = $W.CreateShortcut($Lnk)
Write-Host "Shortcut target:" $Target "Type:" $Target.GetType().FullName
$S.TargetPath = [string]$Target
$S.WorkingDirectory = $Root
$S.WindowStyle = 7
$S.Description = "시선 안전관제"
$S.IconLocation = $IconLocation
$S.Save()
Write-Host "바로가기:" $Lnk
Write-Host "대상:" $Target
Write-Host "아이콘:" $IconLocation
