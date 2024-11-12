echo off
SETLOCAL EnableDelayedExpansion
SETLOCAL ENABLEEXTENSIONS
IF ERRORLEVEL 1 ECHO Unable to enable extensions

:: Check for Python Installation
python --version >nul 2>&1
if not errorlevel 1 goto hasPython
echo.
echo Error - Python installation not found. Python 3.6 or greater must be installed and on the PATH.
goto :EOF

:hasPython
:: Check Python version
set "PYEXE=python"
python -c "import sys; assert sys.version_info >= (3,6)" >nul 2>&1
if not errorlevel 1 goto pythonOK
echo Default python version too low, trying python3...
python3 --version >nul 2>&1
if not errorlevel 1 goto hasPython3
echo.
echo Error - Python 3.6 or greater must be installed and on the PATH. Python found is:
python --version
goto :EOF

:hasPython3
:: Check Python3 version
set "PYEXE=python3"
python3 -c "import sys; assert sys.version_info >= (3,6)" >nul 2>&1
if not errorlevel 1 goto pythonOK
echo.
echo Error - Python 3.6 or greater must be installed and on the PATH. Python found is:
python --version
goto :EOF

:pythonOK
:: download audio mezzanine files
%PYEXE% download_mezzanine.py
if errorlevel 1 goto downloadFail

echo.
echo Import Audio Mezzanine complete.
goto :EOF

:downloadFail
echo.
echo Error: Import Audio Mezzanine failed.
