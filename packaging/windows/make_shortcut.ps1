$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Exe = Join-Path $Root "Sisun.exe"
$Ico = Join-Path $Root "packaging\icons\sisun.ico"
$Desktop = [Environment]::GetFolderPath("Desktop")
$DeskExe = Join-Path $Desktop "Sisun.exe"
$Lnk = Join-Path $Desktop "Sisun.lnk"
if (Test-Path $Exe) { Copy-Item $Exe $DeskExe -Force }
$Target = if (Test-Path $DeskExe) { $DeskExe } elseif (Test-Path $Exe) { $Exe } else { Join-Path $Root "sisun.vbs" }
$W = New-Object -ComObject WScript.Shell
if (Test-Path $Lnk) { Remove-Item $Lnk -Force }
$S = $W.CreateShortcut($Lnk)
$S.TargetPath = $Target
$S.WorkingDirectory = $Root
$S.WindowStyle = 7
$S.Description = "Sisun safety control"
if (Test-Path $Ico) { $S.IconLocation = ($Ico + ",0") }
$S.Save()
Write-Host $Lnk
Write-Host $Target
