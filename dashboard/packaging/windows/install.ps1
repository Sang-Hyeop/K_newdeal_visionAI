# 역할: 기존 Python·safety를 확인하여 실행 자료와 바로가기를 준비합니다. Python 자체는 설치하지 않습니다.
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
function Invoke-InstallProcess([string]$Executable, [string[]]$ProcessArguments, [int]$TimeoutSeconds = 1800, [switch]$QuietFailure) {
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
    $Errors = $Running.StandardError.ReadToEndAsync()
    $Clock = [Diagnostics.Stopwatch]::StartNew()
    $NextNotice = 10
    try {
        while (-not $Running.WaitForExit(500)) {
            if ($Clock.Elapsed.TotalSeconds -ge $TimeoutSeconds) {
                # 설치기가 시작한 프로세스 트리만 종료합니다.
                & "$env:SystemRoot\System32\taskkill.exe" /PID $Running.Id /T /F | Out-Null
                throw "작업 제한 시간($TimeoutSeconds 초) 초과: $Executable. $Log 확인"
            }
            if ($Clock.Elapsed.TotalSeconds -ge $NextNotice) {
                Write-Host ("작업 진행 중: {0} · {1}초 경과" -f [IO.Path]::GetFileName($Executable), [int]$Clock.Elapsed.TotalSeconds)
                $NextNotice += 10
            }
        }
        $ErrorText = $Errors.GetAwaiter().GetResult()
        [IO.File]::WriteAllText($ErrorLog, $ErrorText, [Text.Encoding]::UTF8)
        if ($ErrorText -and -not $QuietFailure) { Write-Host $ErrorText }
        return $Running.ExitCode
    } finally { $Running.Dispose() }
}

$script:DiscoveredPython = New-Object 'System.Collections.Generic.List[string]'

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
            $OutputTask = $Process.StandardOutput.ReadToEndAsync()
            if (-not $Process.WaitForExit(30000)) {
                & "$env:SystemRoot\System32\taskkill.exe" /PID $Process.Id /T /F | Out-Null
                Write-Host "Conda 환경 목록 응답이 없어 다른 탐색 경로로 진행합니다."
                continue
            }
            $Result = $OutputTask.GetAwaiter().GetResult()
            if ($Process.ExitCode -eq 0) {
                foreach ($Prefix in ($Result | ConvertFrom-Json).envs) { $Prefixes.Add($Prefix) }
            }
        } catch {
            Write-Host "Conda 목록을 읽지 못해 등록 파일과 기본 위치를 확인합니다."
        } finally { $Process.Dispose() }
    }
    foreach ($Prefix in ($Prefixes | Select-Object -Unique)) {
        $script:DiscoveredPython.Add((Join-Path $Prefix "python.exe"))
        if ((Split-Path $Prefix -Leaf) -ne "safety") { continue }
        $Candidate = Join-Path $Prefix "python.exe"
        if (-not [IO.File]::Exists($Candidate)) { continue }
        Write-Host "safety 환경 검사: $Candidate"
        $Code = Invoke-InstallProcess $Candidate @((Join-Path $Root "scripts\setup_windows.py"), "--probe") -TimeoutSeconds 90 -QuietFailure
        if ($Code -eq 0 -and [IO.File]::Exists((Join-Path $Prefix "pythonw.exe"))) { return $Candidate }
        Write-Host "기존 safety는 버전 또는 패키지가 달라 보존하고 전용 환경을 준비합니다."
    }
    return $null
}

try {
    Write-Host "[1/4] 기존 safety 환경과 Python을 확인합니다."
    $SafetyPython = Find-SafetyPython
    if ($SafetyPython) {
        $Code = Invoke-InstallProcess $SafetyPython @((Join-Path $Root "scripts\setup_windows.py"), "--reuse")
        if ($Code -ne 0) { throw "safety 실행 자료 검증 실패" }
        $SelectedPython = Join-Path (Split-Path $SafetyPython -Parent) "pythonw.exe"
    } else {
    # 호환 safety가 없으면 설치되어 있는 Python만 검사합니다. 다운로드하지 않습니다.
    $Candidates = New-Object 'System.Collections.Generic.List[string]'
    foreach ($Candidate in $script:DiscoveredPython) { $Candidates.Add($Candidate) }
    $Candidates.Add((Join-Path $State "venv\Scripts\python.exe"))
    $Candidates.Add((Join-Path $env:LOCALAPPDATA "Sisun\Python311\python.exe"))
    $Existing = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($Existing -and $Existing.Source -notlike "*WindowsApps*") { $Candidates.Add($Existing.Source) }
    foreach ($Key in @("HKCU:\Software\Python\PythonCore\3.11\InstallPath", "HKLM:\Software\Python\PythonCore\3.11\InstallPath")) {
        $Registered = Get-ItemProperty -LiteralPath $Key -ErrorAction SilentlyContinue
        if ($Registered -and $Registered.'(default)') { $Candidates.Add((Join-Path $Registered.'(default)' "python.exe")) }
    }
    $Python = $null
    foreach ($Candidate in ($Candidates | Select-Object -Unique)) {
        if (-not [IO.File]::Exists($Candidate)) { continue }
        Write-Host "기존 Python 검사: $Candidate"
        $Code = Invoke-InstallProcess $Candidate @("-c", "import sys, venv; sys.exit(0 if sys.version_info[:2] == (3,11) and sys.maxsize > 2**32 else 1)") -TimeoutSeconds 30 -QuietFailure
        if ($Code -eq 0) { $Python = $Candidate; break }
        Write-Host "Python 3.11 64비트 조건과 달라 다음 환경을 확인합니다."
    }
    if (-not $Python) {
        throw "Python을 설치해주세요. 이 프로그램에는 Python 3.11 64비트가 필요합니다. 이미 설치했다면 해당 Python이 탐색되도록 PATH 또는 Conda 환경 등록을 확인해주세요. Python은 자동 설치하지 않습니다."
    }
    Write-Host "[2/4] 프로젝트 전용 환경을 준비합니다."
    $Venv = Join-Path $State "venv\Scripts\python.exe"
    $EnvironmentOK = $false
    if (Test-Path -LiteralPath $Venv) {
        $Code = Invoke-InstallProcess $Venv @("-c", "import sys; sys.exit(0 if sys.version_info[:2] == (3,11) and sys.maxsize > 2**32 else 1)") -TimeoutSeconds 30 -QuietFailure
        $EnvironmentOK = ($Code -eq 0)
    }
    if (-not $EnvironmentOK) {
        $Code = Invoke-InstallProcess $Python @("-m", "venv", "--clear", (Join-Path $State "venv"))
        if ($Code -ne 0) { throw "전용 환경 생성 실패" }
    }
    Write-Host "[3/4] 라이브러리·모델·영상을 준비하고 검증합니다."
    $Code = Invoke-InstallProcess $Venv @((Join-Path $Root "scripts\setup_windows.py"))
    if ($Code -ne 0) { throw "라이브러리 또는 실행 자료 설치 실패. $Log 확인" }
    $SelectedPython = Join-Path (Split-Path $Venv -Parent) "pythonw.exe"
    }
    [IO.File]::WriteAllText((Join-Path $State "runtime-pythonw.txt"), $SelectedPython, (New-Object Text.UTF8Encoding($false)))
    Write-Host "선택된 실행 환경: $SelectedPython"
    Write-Host "[4/4] 바탕화면 바로가기를 만듭니다."
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
