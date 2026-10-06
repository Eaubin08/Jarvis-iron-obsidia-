@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch_jarjar_windows.ps1"
echo.
echo Jarjar termine. Appuyez sur une touche pour fermer.
pause >nul
