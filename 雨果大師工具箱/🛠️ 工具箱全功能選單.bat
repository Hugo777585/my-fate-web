@echo off
title 雨果大師工具箱 v1.0
:menu
cls
echo ========================================
echo       🔮 雨果大師專屬工具箱 v1.0
echo ========================================
echo.
echo    [1] 🚀 執行系統自動備份
echo    [2] ⏪ 執行系統版本還原
echo    [3] 📂 打開專案根目錄
echo    [4] 🚪 退出工具箱
echo.
echo ========================================
set /p choice=請輸入選項 (1-4): 

if "%choice%"=="1" goto backup
if "%choice%"=="2" goto restore
if "%choice%"=="3" goto openfolder
if "%choice%"=="4" exit
goto menu

:backup
cls
echo 🚀 啟動自動備份程式...
cd /d "%~dp0"
python "系統備份程式.py"
pause
goto menu

:restore
cls
echo ⏪ 啟動系統還原程式...
cd /d "%~dp0"
python "系統還原程式.py"
pause
goto menu

:openfolder
explorer "%~dp0.."
goto menu
