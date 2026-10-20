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
    $Info = New-Object System.Diagnostics.ProcessStartInfo
    $Info.FileName = $Executable
    $Info.Arguments = $Quoted
    $Info.UseShellExecute = $false
    $Info.CreateNoWindow = $true
    $Info.RedirectStandardError = $true
    $Info.StandardErrorEncoding = [Text.Encoding]::UTF8
    $Running = New-Object System.Diagnostics.Process
    $Running.StartInfo = $Info
    [void]$Running.Start()
    $ErrorText = $Running.StandardError.ReadToEnd()
    $Running.WaitForExit()
    [IO.File]::WriteAllText($ErrorLog, $ErrorText, [Text.Encoding]::UTF8)
    if ($ErrorText) { Write-Host $ErrorText }
    $Code = $Running.ExitCode
    $Running.Dispose()
    return $Code
}

try {
    # Python MSI는 대괄호가 포함된 TargetDir을 정상 처리하지 못할 수 있어 사용자 앱 폴더를 씁니다.
    $PythonHome = Join-Path $env:LOCALAPPDATA "Sisun\Python311"
    $Python = Join-Path $PythonHome "python.exe"
    if (-not (Test-Path -LiteralPath $Python)) {
        # 시스템 PATH를 바꾸지 않고 사용자 전용 런타임을 준비합니다.
        $Installer = Join-Path $State "python-3.11.9-amd64.exe"
        $Expected = "5ee42c4eee1e6b4464bb23722f90b45303f79442df63083f05322f1785f5fdde"
        if (-not (Test-Path -LiteralPath $Installer) -or (Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLower() -ne $Expected) {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            $Download = New-Object System.Net.WebClient
            try { $Download.DownloadFile("https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe", $Installer) }
            finally { $Download.Dispose() }
        }
        if ((Get-FileHash -LiteralPath $Installer -Algorithm SHA256).Hash.ToLower() -ne $Expected) { throw "Python 설치 파일 해시가 다릅니다." }
        $Target = $PythonHome
        $Arguments = '/quiet InstallAllUsers=0 Include_pip=1 Include_launcher=0 Include_test=0 Include_doc=0 AssociateFiles=0 Shortcuts=0 PrependPath=0 TargetDir="' + $Target + '"'
        $Process = Start-Process -FilePath $Installer -ArgumentList $Arguments -Wait -PassThru
        if ($Process.ExitCode -notin @(0, 3010)) { throw "Python 설치 실패: $($Process.ExitCode)" }
        if (-not [IO.File]::Exists($Python)) {
            # 같은 버전이 이미 등록된 PC에서는 설치기가 기존 위치를 유지할 수 있습니다.
            foreach ($Key in @("HKCU:\Software\Python\PythonCore\3.11\InstallPath", "HKLM:\Software\Python\PythonCore\3.11\InstallPath")) {
                $Registered = Get-ItemProperty -LiteralPath $Key -ErrorAction SilentlyContinue
                if ($Registered -and $Registered.'(default)') {
                    $Candidate = Join-Path $Registered.'(default)' "python.exe"
                    if ([IO.File]::Exists($Candidate)) { $Python = $Candidate; break }
                }
            }
        }
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
