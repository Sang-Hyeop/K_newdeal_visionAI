@echo off
REM 작은 Sisun.exe 래퍼 (시선.vbs 호출)
cd /d "%~dp0"
set "CSC="
if exist "%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe" set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not defined CSC if exist "%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not defined CSC (
  echo csc.exe 없음. 대신 루트 시선.vbs 를 사용하세요.
  pause
  exit /b 1
)
set "ICO=%~dp0..\icons\sisun.ico"
if not exist "%ICO%" set "ICO=%~dp0..\..\icons\sisun.ico"
if exist "%ICO%" (
  "%CSC%" /nologo /target:winexe /win32icon:"%ICO%" /r:System.Windows.Forms.dll /out:"%~dp0..\..\..\Sisun.exe" Sisun.cs
) else (
  "%CSC%" /nologo /target:winexe /r:System.Windows.Forms.dll /out:"%~dp0..\..\..\Sisun.exe" Sisun.cs
)
if errorlevel 1 ( echo 빌드 실패 & pause & exit /b 1 )
echo 완료: 저장소 루트\Sisun.exe
pause
