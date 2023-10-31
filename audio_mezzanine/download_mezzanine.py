"""Script used to download mezzanine files and their corresponding json files 
from a remote json file"""

import json
import os
from urllib.request import urlretrieve

f = open('mezzanine_database.json', encoding="UTF-8")
data_json = json.load(f)

for pn in data_json["audio"]:
    #delete previous copy of file if it exists
    filename_wav = pn + ".wav"
    filename_json = pn + ".json"
    if os.path.exists(filename_wav):
        os.remove(filename_wav)
    if os.path.exists(filename_json):
        os.remove(filename_json)
    #download the new version of the file
    destination_wav = pn + ".wav"
    destination_json = pn + ".json"
    command1 =  data_json["audio"][pn]["path"]
    command2 = data_json["audio"][pn]["json_path"]
    urlretrieve(command1,filename=destination_wav)
    print(f"Downloaded {destination_wav}")
    urlretrieve(command2,filename=destination_json)
    print(f"Downloaded {destination_json}")
print("Download complete")
