#!/bin/sh

# import mezzanine_database.json
wget -O mezzanine_database.json https://raw.githubusercontent.com/cta-wave/mezzanine/master/metadata/audio_mezzanine_database.json

# download audio mezzanine files
python3 download_mezzanine.py