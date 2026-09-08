@echo off
rem Launch Paint Puzzle (double-click me)
pushd "%~dp0"
"D:\Mini programme\.venv\Scripts\python.exe" "src\main.py"
if errorlevel 1 pause
