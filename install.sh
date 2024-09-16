#!/bin/sh
#
# Observation Framework installer shell script for use on Linux and macOS.
# This requires python version 3.6 or greater and pip version 3 to be installed and on the execution PATH.

install_package()
{
    if ! $PYEXE -m pip install --no-cache-dir $1; then
        echo
        echo Error - Package installation failed.
        exit 1
    fi
}

# Check for Python Installation
if ! python --version >/dev/null 2>&1; then
    echo
    echo Error - Python installation not found. Python 3.6 or greater must be installed and on the PATH.
    exit 1
fi

# Check Python version
if python -c 'import sys; assert sys.version_info >= (3,6)' >/dev/null 2>&1; then
    PYEXE=python
else
    echo Default python version too low, trying python3...
    # default version is too low, see if python3 is available
    if python3 --version >/dev/null 2>&1; then
        # is that a better version?
        if python3 -c 'import sys; assert sys.version_info >= (3,6)' >/dev/null 2>&1; then
            PYEXE=python3
        fi
    fi
fi

if [ -z $PYEXE ]; then
    echo
    echo Error - Python 3.6 or greater must be installed and on the PATH. Python version found is
    python -c 'import sys; print(sys.version_info)'
    exit 1
fi

# Install required packages
$PYEXE -m pip install --upgrade pip
install_package numpy==2.0.2
install_package opencv-python==4.10.0.84
install_package pyzbar==0.1.9
install_package isodate
install_package configparser
install_package requests
install_package pyaudio
install_package sounddevice
install_package matplotlib

# scan for something listening on the expected Test Runner port
if ! nc -z localhost 8000; then
    echo
    echo "[WARNING] - The DPCTF Test Runner is not reachable on localhost:8000"
    echo "Please check that Test Runner is installed correctly and is running. See https://github.com/cta-wave/dpctf-deploy"
    echo "If DNS is set up for Test Runner or Test Runner uses a different IP address then update the \"test_runner_url\" entry in the Observation Framework \"config.ini\" file."
    echo "See documentation at https://github.com/cta-wave/device-observation-framework"
fi

echo
echo Installation complete.

