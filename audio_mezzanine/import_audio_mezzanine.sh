#!/bin/sh

# import mezzanine_database.json
wget -O mezzanine_database.json https://raw.githubusercontent.com/cta-wave/mezzanine/v4.0.0/metadata/audio_mezzanine_database.json

# download audio mezzanine files
python download_mezzanine.py
