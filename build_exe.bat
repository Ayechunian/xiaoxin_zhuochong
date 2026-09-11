@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0packaging\build_exe.ps1"
if errorlevel 1 (
  echo.
  echo 打包失败，请查看上方错误信息。
) else (
  echo.
  echo 打包完成：release\小新桌宠.exe
)
pause
