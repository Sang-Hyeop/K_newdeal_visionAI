# Windows 공용: 바탕화면에 시선 바로가기 생성 (프로젝트 상대 경로만 사용)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$Ico = Join-Path $Root "dashboard\packaging\icons\sisun.ico"
if (-not (Test-Path $Ico)) {
    Write-Error "아이콘 없음: $Ico"
}
$Desktop = [Environment]::GetFolderPath("Desktop")
$Lnk = Join-Path $Desktop "시선.lnk"

$Vbs = Join-Path $Root "시선.vbs"
$ExeRoot = Join-Path $Root "Sisun.exe"
$ExeDist = Join-Path $Root "dist\sisun\sisun.exe"
$DesktopPy = Join-Path $Root "dashboard_desktop.py"

if (-not (Test-Path $DesktopPy)) {
    Write-Error "dashboard_desktop.py 없음: $Root"
}

$Target = $null
if (Test-Path $ExeDist) { $Target = $ExeDist }
elseif (Test-Path $ExeRoot) { $Target = $ExeRoot }
elseif (Test-Path $Vbs) { $Target = $Vbs }
else {
    Write-Error "실행 대상 없음. 루트에 시선.vbs 가 필요합니다: $Root"
}

$W = New-Object -ComObject WScript.Shell
if (Test-Path $Lnk) { Remove-Item $Lnk -Force }
$S = $W.CreateShortcut($Lnk)
$S.TargetPath = $Target
$S.WorkingDirectory = $Root
$S.WindowStyle = 7
$S.Description = "시선 안전관제"
$S.IconLocation = ($Ico + ",0")
$S.Save()
Write-Host "바로가기:" $Lnk
Write-Host "대상:" $Target
Write-Host "아이콘:" $Ico
