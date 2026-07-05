@echo off
setlocal
chcp 65001 >nul
echo ================================================
echo   Claude Code Hooks Installer  (global install)
echo ================================================
echo.

set "SRC=%~dp0"
set "DEST=%USERPROFILE%\.claude"
set "HOOKDEST=%DEST%\hooks"

echo Install target : %DEST%
echo.

REM 1) hooks 폴더 생성
if not exist "%HOOKDEST%" (
  mkdir "%HOOKDEST%"
  echo   created : %HOOKDEST%
) else (
  echo   exists  : %HOOKDEST%
)

REM 2) 훅 스크립트 복사
copy /Y "%SRC%texdoc-gen.mjs" "%HOOKDEST%\" >nul
if errorlevel 1 ( echo   [ERROR] texdoc-gen.mjs copy failed & goto :fail )
echo   + texdoc-gen.mjs

copy /Y "%SRC%graphify-autoinstall.mjs" "%HOOKDEST%\" >nul
if errorlevel 1 ( echo   [ERROR] graphify-autoinstall.mjs copy failed & goto :fail )
echo   + graphify-autoinstall.mjs

copy /Y "%SRC%uv-venv-setup.mjs" "%HOOKDEST%\" >nul
if errorlevel 1 ( echo   [ERROR] uv-venv-setup.mjs copy failed & goto :fail )
echo   + uv-venv-setup.mjs

copy /Y "%SRC%cfms-sync.mjs" "%HOOKDEST%\" >nul
if errorlevel 1 ( echo   [ERROR] cfms-sync.mjs copy failed & goto :fail )
echo   + cfms-sync.mjs

copy /Y "%SRC%qt-build-check.mjs" "%HOOKDEST%\" >nul
if errorlevel 1 ( echo   [ERROR] qt-build-check.mjs copy failed & goto :fail )
echo   + qt-build-check.mjs

copy /Y "%SRC%cfms-watch.mjs" "%HOOKDEST%\" >nul
if errorlevel 1 ( echo   [ERROR] cfms-watch.mjs copy failed & goto :fail )
echo   + cfms-watch.mjs

copy /Y "%SRC%cfms-watch.bat" "%HOOKDEST%\" >nul
if errorlevel 1 ( echo   [ERROR] cfms-watch.bat copy failed & goto :fail )
echo   + cfms-watch.bat

echo.
echo Merging settings.json ...
REM 3) settings.json 병합 (PowerShell)
powershell -NoProfile -ExecutionPolicy Bypass -File "%SRC%merge-settings.ps1" -SrcSettings "%SRC%settings.json" -DestSettings "%DEST%\settings.json"
if errorlevel 1 ( echo   [ERROR] settings.json merge failed & goto :fail )

echo.
echo ================================================
echo   Done.  Restart Claude Code / VSCode to apply.
echo ================================================
echo.
pause
exit /b 0

:fail
echo.
echo Installation aborted.
pause
exit /b 1
