@echo off
setlocal
chcp 65001 >nul
REM cfms 자동 반응 워처 실행.  사용법: cfms-watch.bat [프로젝트폴더]
REM 생략 시 현재 폴더를 프로젝트로 사용. (해당 폴더에 .cfms-sync.json 필요)
set "PROJ=%~1"
if "%PROJ%"=="" set "PROJ=%CD%"
echo ================================================
echo   cfms-watch  (자동 반응 워처)
echo   project : %PROJ%
echo   중지하려면 이 창에서 Ctrl+C
echo ================================================
node "%USERPROFILE%\.claude\hooks\cfms-watch.mjs" "%PROJ%"
pause
