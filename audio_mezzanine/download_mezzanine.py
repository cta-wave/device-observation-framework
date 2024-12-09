"""Script used to download mezzanine files and their corresponding json files 
from a remote json file"""

import json
import os
import sys
from urllib.request import urlretrieve


def download_mezzanine() -> bool:
    """download audio mezzanine files"""
    db_json = "mezzanine_database.json"
    db_json_url = "https://raw.githubusercontent.com/cta-wave/mezzanine/v4.0.0/metadata/audio_mezzanine_database.json"
    if os.path.exists(db_json):
        os.remove(db_json)
    urlretrieve(db_json_url, filename=db_json)
    print(f"Download {db_json} complete.")

    try:
        file = open(db_json, encoding="UTF-8")
    except IOError:
        print("ERROR: {DB_JSON} not found!")
        return False

    data_json = json.load(file)

    for pn in data_json["audio"]:
        # delete previous copy of file if it exists
        filename_wav = pn + ".wav"
        filename_json = pn + ".json"
        if os.path.exists(filename_wav):
            os.remove(filename_wav)
        if os.path.exists(filename_json):
            os.remove(filename_json)
        # download the new version of the file
        destination_wav = pn + ".wav"
        destination_json = pn + ".json"
        command1 = data_json["audio"][pn]["path"]
        command2 = data_json["audio"][pn]["json_path"]
        urlretrieve(command1, filename=destination_wav)
        print(f"Downloaded {destination_wav}")
        urlretrieve(command2, filename=destination_json)
        print(f"Downloaded {destination_json}")
    print("Download complete")
    return True


def main() -> int:
    """entry point"""
    if download_mezzanine():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
