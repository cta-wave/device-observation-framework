#!/bin/sh

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

# download audio mezzanine files
if ! $PYEXE download_mezzanine.py; then
        echo
        echo Error - Package installation failed.
        exit 1
    fi
