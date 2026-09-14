@echo off

cd /d "%~dp0"

echo.
echo ========================================
echo   Worker Detection Tool
echo ========================================
echo.
echo 1. Start worker detection
echo 2. Show worker timeline
echo 3. Show worker position scatter
echo 4. Merge video files
echo 0. Exit
echo.

set /p choice=Select program: 

if "%choice%"=="1" goto detect
if "%choice%"=="2" goto timeline
if "%choice%"=="3" goto scatter
if "%choice%"=="4" goto merge
if "%choice%"=="0" goto end

echo.
echo Invalid selection.
pause
goto end


:detect
"..\.venv\Scripts\python.exe" detect_worker.py
goto end


:timeline
"..\.venv\Scripts\python.exe" create_worker_timeline.py
goto end


:scatter
"..\.venv\Scripts\python.exe" worker_position_scatter.py
goto end


:merge
"..\.venv\Scripts\python.exe" merge_videos.py
goto end


:end
echo.
pause