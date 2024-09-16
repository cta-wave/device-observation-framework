echo off
:: Observation Framework installer for use on Windows.
:: This requires python version 3.6 or greater and pip version 3 to be installed and on the execution PATH.
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
:: Install required packages
%PYEXE% -m pip install --upgrade pip
%PYEXE% -m pip install --no-cache-dir numpy==2.0.2
if errorlevel 1 goto numpy
%PYEXE% -m pip install --no-cache-dir opencv-python==4.10.0.84
if errorlevel 1 goto installFail
%PYEXE% -m pip install --no-cache-dir pyzbar==0.1.9
if errorlevel 1 goto installFail
%PYEXE% -m pip install --no-cache-dir isodate
if errorlevel 1 goto installFail
%PYEXE% -m pip install --no-cache-dir configparser
if errorlevel 1 goto installFail
%PYEXE% -m pip install --no-cache-dir requests
if errorlevel 1 goto installFail
%PYEXE% -m pip install --no-cache-dir pyaudio
if errorlevel 1 goto pyaudio
%PYEXE% -m pip install --no-cache-dir sounddevice
if errorlevel 1 goto sounddevice
%PYEXE% -m pip install --no-cache-dir matplotlib
if errorlevel 1 goto matplotlib

:: Check something (anything) is listening on the Test Runner port.
FOR /F "delims=" %%i IN ('netstat -an ^| findstr "8000"  ^| findstr "LISTEN"') DO (set cmdout=%%i)
IF NOT DEFINED cmdout (
    echo.
    echo [WARNING] - The DPCTF Test Runner is not reachable on localhost:8000
    echo Please check that Test Runner is installed correctly and is running. See https://github.com/cta-wave/dpctf-deploy
    echo If DNS is set up for Test Runner or Test Runner uses a different IP address then update the "test_runner_url" entry in the Observation Framework "config.ini" file.
    echo See documentation at https://github.com/cta-wave/device-observation-framework
)

echo.
echo Installation complete.
goto :EOF

:installFail
echo.
echo Error - Package installation failed.
