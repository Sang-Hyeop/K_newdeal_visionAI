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

# conda 등록 목록과 사용자 환경 목록을 읽어 설치 위치에 관계없이 safety를 찾습니다.
function Find-SafetyPython {
    $Prefixes = New-Object 'System.Collections.Generic.List[string]'
    if ($env:CONDA_PREFIX) { $Prefixes.Add($env:CONDA_PREFIX) }
    $EnvironmentList = Join-Path $env:USERPROFILE ".conda\environments.txt"
    if ([IO.File]::Exists($EnvironmentList)) {
        foreach ($Line in [IO.File]::ReadAllLines($EnvironmentList)) { if ($Line.Trim()) { $Prefixes.Add($Line.Trim()) } }
    }
    $CondaExecutables = New-Object 'System.Collections.Generic.List[string]'
    if ($env:CONDA_EXE) { $CondaExecutables.Add($env:CONDA_EXE) }
    $Command = Get-Command conda.exe -ErrorAction SilentlyContinue
    if ($Command) { $CondaExecutables.Add($Command.Source) }
    foreach ($HomePath in @($env:USERPROFILE, $env:LOCALAPPDATA, $env:ProgramData)) {
        foreach ($Distribution in @("anaconda3", "miniconda3", "miniforge3")) {
            $CondaExecutables.Add((Join-Path $HomePath "$Distribution\Scripts\conda.exe"))
            $Prefixes.Add((Join-Path $HomePath "$Distribution\envs\safety"))
        }
    }
    foreach ($Executable in ($CondaExecutables | Select-Object -Unique)) {
        if (-not [IO.File]::Exists($Executable)) { continue }
        $Info = New-Object Diagnostics.ProcessStartInfo
        $Info.FileName = $Executable
        $Info.Arguments = "env list --json"
        $Info.UseShellExecute = $false
        $Info.CreateNoWindow = $true
        $Info.RedirectStandardOutput = $true
        $Process = New-Object Diagnostics.Process
        $Process.StartInfo = $Info
        try {
            [void]$Process.Start()
            $Result = $Process.StandardOutput.ReadToEnd()
            $Process.WaitForExit()
            if ($Process.ExitCode -eq 0) {
                foreach ($Prefix in ($Result | ConvertFrom-Json).envs) { $Prefixes.Add($Prefix) }
            }
        } finally { $Process.Dispose() }
    }
    foreach ($Prefix in ($Prefixes | Select-Object -Unique)) {
        if ((Split-Path $Prefix -Leaf) -ne "safety") { continue }
        $Candidate = Join-Path $Prefix "python.exe"
        if (-not [IO.File]::Exists($Candidate)) { continue }
        Write-Host "safety 환경 검사: $Candidate"
        $Code = Invoke-InstallProcess $Candidate @((Join-Path $Root "scripts\setup_windows.py"), "--probe")
        if ($Code -eq 0 -and [IO.File]::Exists((Join-Path $Prefix "pythonw.exe"))) { return $Candidate }
        Write-Host "기존 safety는 버전 또는 패키지가 달라 보존하고 전용 환경을 준비합니다."
    }
    return $null
}

try {
    $SafetyPython = Find-SafetyPython
    if ($SafetyPython) {
        $Code = Invoke-InstallProcess $SafetyPython @((Join-Path $Root "scripts\setup_windows.py"), "--reuse")
        if ($Code -ne 0) { throw "safety 실행 자료 검증 실패" }
        $SelectedPython = Join-Path (Split-Path $SafetyPython -Parent) "pythonw.exe"
    } else {
    # Python MSI는 대괄호가 포함된 TargetDir을 정상 처리하지 못할 수 있어 사용자 앱 폴더를 씁니다.
    $PythonHome = Join-Path $env:LOCALAPPDATA "Sisun\Python311"
    $Python = Join-Path $PythonHome "python.exe"
    # 기존 Python 3.11 x64도 먼저 확인하여 불필요한 재설치를 피합니다.
    if (-not [IO.File]::Exists($Python)) {
        $Candidates = New-Object 'System.Collections.Generic.List[string]'
        $Existing = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($Existing -and $Existing.Source -notlike "*WindowsApps*") { $Candidates.Add($Existing.Source) }
        foreach ($Key in @("HKCU:\Software\Python\PythonCore\3.11\InstallPath", "HKLM:\Software\Python\PythonCore\3.11\InstallPath")) {
            $Registered = Get-ItemProperty -LiteralPath $Key -ErrorAction SilentlyContinue
            if ($Registered -and $Registered.'(default)') { $Candidates.Add((Join-Path $Registered.'(default)' "python.exe")) }
        }
        foreach ($Candidate in ($Candidates | Select-Object -Unique)) {
            if (-not [IO.File]::Exists($Candidate)) { continue }
            $Code = Invoke-InstallProcess $Candidate @("-c", "import sys; assert sys.version_info[:2] == (3,11) and sys.maxsize > 2**32; import venv")
            if ($Code -eq 0) { $Python = $Candidate; break }
        }
    }
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
    $SelectedPython = Join-Path (Split-Path $Venv -Parent) "pythonw.exe"
    }
    [IO.File]::WriteAllText((Join-Path $State "runtime-pythonw.txt"), $SelectedPython, (New-Object Text.UTF8Encoding($false)))
    Write-Host "선택된 실행 환경: $SelectedPython"
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
