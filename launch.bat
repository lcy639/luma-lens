@echo off
setlocal
if exist "%~dp0.venv\Scripts\python.exe" goto venv
where py.exe >nul 2>nul
if not errorlevel 1 goto launcher
where python.exe >nul 2>nul
if not errorlevel 1 goto python
echo Python 3.10 or later is required. See README.md.
pause
exit /b 1

:venv
"%~dp0.venv\Scripts\python.exe" "%~dp0magnifier.py"
goto done

:launcher
py -3 "%~dp0magnifier.py"
goto done

:python
python "%~dp0magnifier.py"

:done
if errorlevel 1 (
    echo Luma Lens could not start. See README.md for installation.
    pause
    exit /b 1
)
