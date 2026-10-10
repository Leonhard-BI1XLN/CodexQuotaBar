@echo off
setlocal

if exist "%~dp0CodexQuotaBar.exe" (
    start "" "%~dp0CodexQuotaBar.exe"
    exit /b 0
)

where pythonw.exe >nul 2>&1
if not errorlevel 1 (
    start "" pythonw.exe "%~dp0CodexQuotaBar.pyw"
    exit /b 0
)

where pyw.exe >nul 2>&1
if not errorlevel 1 (
    start "" pyw.exe -3 "%~dp0CodexQuotaBar.pyw"
    exit /b 0
)

echo 找不到 Python。请安装带 Tkinter 的 Python 3.10 或更新版本后重试。
pause
