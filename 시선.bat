@echo off
cd /d "%~dp0"
set "PYW="
for /d %%D in ("%LOCALAPPDATA%\Python\pythoncore-*") do (
  if exist "%%D\pythonw.exe" set "PYW=%%D\pythonw.exe"
)
if defined PYW (
  start "" "%PYW%" team7_desktop.py
  goto :eof
)
py -3 team7_desktop.py
pause
