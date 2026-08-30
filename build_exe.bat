@echo off
setlocal enabledelayedexpansion
title Brave Tamer Shop Patcher - build exe

rem Builds BraveTamerShopPatcher.pyw into a single standalone .exe,
rem so people you share it with do not need Python installed.
rem Needs an internet connection the first time (to install PyInstaller).
rem NOTE: keep this file ASCII-only - cmd.exe parses .bat in the OEM codepage
rem and multi-byte characters can break rem/for blocks.

cd /d "%~dp0"

set "PY="
for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%ProgramFiles%\Python313\python.exe"
  "%ProgramFiles%\Python312\python.exe"
  "%ProgramFiles%\Python311\python.exe"
) do (
  if not defined PY if exist "%%~P" set "PY=%%~P"
)
if not defined PY (
  where py >nul 2>&1 && set "PY=py"
)
if not defined PY (
  echo [ERROR] Python 3 not found.
  echo         Install it from python.org and enable the tcl/tk option.
  pause
  exit /b 1
)

echo Using Python: %PY%
"%PY%" --version
if errorlevel 1 (
  echo [ERROR] Python cannot run.
  pause
  exit /b 1
)

echo.
echo === Installing / updating PyInstaller ===
"%PY%" -m pip install --upgrade --quiet pyinstaller
if errorlevel 1 (
  echo [ERROR] Failed to install PyInstaller. Check your internet connection.
  pause
  exit /b 1
)

echo.
echo === Building ===
"%PY%" -m PyInstaller --noconfirm --onefile --windowed --name "BraveTamer_ShopPatcher" BraveTamerShopPatcher.pyw
if errorlevel 1 (
  echo [ERROR] Build failed.
  pause
  exit /b 1
)

echo.
echo === Done ===
echo Output: %~dp0dist\BraveTamer_ShopPatcher.exe
echo This exe contains no ROM data and is safe to share.
echo The "build" folder and the .spec file are temporary and can be deleted.
echo.
pause
