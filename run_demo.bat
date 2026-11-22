@echo off
REM Camouflage detection demo. Usage: run_demo.bat [yolo^|baseline] [seed] [true^|false = autostart mission]
set MODE=%1
if "%MODE%"=="" set MODE=yolo
set SEED=%2
if "%SEED%"=="" set SEED=42
set AUTO=%3
if "%AUTO%"=="" set AUTO=true
wsl -d Ubuntu -- bash /mnt/c/Users/admin/Desktop/padhai/Es-proj/scripts/run_demo.sh %MODE% %SEED% %AUTO%
