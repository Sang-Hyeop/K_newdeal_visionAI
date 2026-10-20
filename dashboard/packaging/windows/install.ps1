# 역할: Python이 없는 Windows에서도 전용 환경·라이브러리·실행 자료·바로가기를 설치합니다.
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$OutputEncoding = [Console]::OutputEncoding
$Root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..")).ProviderPath
$State = Join-Path $Root ".sisun"
[void][IO.Directory]::CreateDirectory($State)
$Log = Join-Path $State "install.log"
if (-not [IO.File]::Exists($Log)) { [IO.File]::WriteAllBytes($Log, [byte[]](0xEF, 0xBB, 0xBF)) }
Start-Transcript -LiteralPath $Log -Append | Out-Null
# 파일 경로에 대괄호가 있어도 PowerShell의 명령 검색으로 해석하지 않습니다.
function Invoke-InstallProcess([string]$Executable, [string[]]$ProcessArguments) {
    if (-not [IO.File]::Exists($Executable)) { throw "실행 파일이 없습니다: $Executable" }
    $Quoted = ($ProcessArguments | ForEach-Object { '"' + $_.Replace('"', '\"') + '"' }) -join ' '
    $ErrorLog = Join-Path $State "process-error.log"
    $Running = Start-Process -FilePath $Executable -ArgumentList $Quoted -NoNewWindow -Wait -PassThru -RedirectStandardError $ErrorLog
    if ([IO.File]::Exists($ErrorLog)) {
        Get-Content -LiteralPath $ErrorLog -Encoding UTF8 | ForEach-Object { Write-Host $_ }
    }
    return $Running.ExitCode
}

try {
    $Python = Join-Path $State "python\python.exe"
    if (-not (Test-Path -LiteralPath $Python)) {
        # 사용자 PC의 기존 Python을 변경하지 않고 프로젝트 안에 설치합니다.
        $Installer = Join-Path $State "python-3.11.9-amd64.exe"
        $Expected = "5ee42c4eee1e6b4464bb23722f90b45303f79442df63083f05322f1785f5fdde"
        if (-not (Test-Path -LiteralPath $Installer) -or (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLower() -ne $Expected) {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $Download = New-Object System.Net.WebClient
            try { $Download.DownloadFile("https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe", $Installer) }
            finally { $Download.Dispose() }
        }
        if ((Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLower() -ne $Expected) { throw "Python 설치 파일 해시가 다릅니다." }
        $Target = Join-Path $State "python"
        $Arguments = '/quiet InstallAllUsers=0 Include_pip=1 Include_launcher=0 Include_test=0 Include_doc=0 AssociateFiles=0 Shortcuts=0 PrependPath=0 TargetDir="' + $Target + '"'
        $Process = Start-Process -FilePath $Installer -ArgumentList $Arguments -Wait -PassThru
        if ($Process.ExitCode -notin @(0, 3010)) { throw "Python 설치 실패: $($Process.ExitCode)" }
    }
    $Venv = Join-Path $State "venv\Scripts\python.exe"
    $EnvironmentOK = $false
    if (Test-Path -LiteralPath $Venv) {
        $Code = Invoke-InstallProcess $Venv @("-c", "import sys; assert sys.version_info[:2] == (3,11)")
        $EnvironmentOK = ($Code -eq 0)
    }
    if (-not $EnvironmentOK) {
        $Code = Invoke-InstallProcess $Python @("-m", "venv", "--clear", (Join-Path $State "venv"))
        if ($Code -ne 0) { throw "전용 환경 생성 실패" }
    }
    $Code = Invoke-InstallProcess $Venv @((Join-Path $Root "scripts\setup_windows.py"))
    if ($Code -ne 0) { throw "라이브러리 또는 실행 자료 설치 실패. $Log 확인" }
    $PowerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $Code = Invoke-InstallProcess $PowerShell @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "make_shortcut.ps1"))
    if ($Code -ne 0) { throw "바로가기 생성 실패" }
    Write-Host "설치 완료. 바탕화면 시선을 실행하세요."
} catch {
    Write-Host "설치 실패:" $_ -ForegroundColor Red
    Write-Host "로그:" $Log
    exit 1
} finally {
    Stop-Transcript | Out-Null
}
