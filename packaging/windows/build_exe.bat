@echo off
cd /d "%~dp0..\.."
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --noconsole --name sisun --collect-all gradio --collect-all gradio_client --add-data "team7_app;team7_app" --icon "packaging\icons\sisun.ico" team7_desktop.py
echo exe: dist\sisun\sisun.exe
pause
