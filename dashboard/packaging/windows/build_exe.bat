@echo off
REM Windows용 Sisun.exe 빌드 (Windows PC에서 실행)
cd /d "%~dp0..\..\.."

if not exist "dashboard_desktop.py" (
  echo dashboard_desktop.py 가 없습니다. 저장소 루트 기준으로 실행하세요.
  pause
  exit /b 1
)
if not exist "dashboard\app.py" (
  echo dashboard\app.py 가 없습니다.
  pause
  exit /b 1
)

python -m pip install -U pyinstaller
python -m PyInstaller --noconfirm --noconsole --name sisun ^
  --collect-all gradio --collect-all gradio_client ^
  --add-data "dashboard;dashboard" ^
  --icon "dashboard\packaging\icons\sisun.ico" ^
  dashboard_desktop.py

if errorlevel 1 (
  echo PyInstaller 실패
  pause
  exit /b 1
)

if exist "dist\sisun\sisun.exe" (
  copy /Y "dist\sisun\sisun.exe" "Sisun.exe" >nul
  echo 완료: dist\sisun\sisun.exe  / 루트 Sisun.exe
) else (
  echo exe 를 찾지 못했습니다.
)
pause
