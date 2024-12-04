# Setting up the Device Observation Framework without Docker

The Device Observation Framework can also be installed **without Docker** as follows.

## Installation

The Observation Framework **must** be installed on same machine as the Test Runner is deployed.
Test Runner is deployed as a service running inside a Docker container.
The Observation Framework **must** be installed outside of Docker or Docker Desktop and run outside of the Docker from the Windows command line.
Make sure that the command line or PowerShell that is used for running the Observation Framework is not inside the Docker or Docker Desktop.

⚠️ This Observation Framework release has been tested on Ubuntu 18.04 LTS and Windows 10. However, as per the Test Runner, it is highly recommended to use Linux for production purposes.

## Updating System Environment for Windows

There are a number of points in these instructions that will direct you to add the necessary path(s) to Windows System Variables under the PATH entry. You will need to add the Path(s) to the folder(s) that will contain the WAVE Test Suite files you will create, Python, Docker Desktop, ZBar and any others as noted in these instructions. This is so the system knows where to find them. There may be additional Paths required. When a command returns an error such as "file not found" check to see if the Path is in the Environment System Variables under "PATH". If not, add the missing Path. 

To add to or modify the System Environment Variables. 
1.	Follow the instructions in the various ReadMe files for Windows, not Unix/Linux or Mac OS X.
2.	Run all commands using Windows PowerShell/Terminal. Do not run them using Bash in a Linux terminal. 
3.	If a command in Windows PowerShell/Terminal stalls or hangs up, use <Control + C> to gracefully exit. 

* Search for "Edit System Environmental Variables" in the search bar. 
* Select "Environment Variables"
* Under "System variables" (lower box), select "Path"
* Then select Edit
* Select "New" and enter the desired Path.
* Select "New" again for each new Path you wish to add. 
* When done, close the Environment Variables screens AND the Windows PowerShell/Terminal to ensure the Paths are updated.

## Installing Required Libraries

The Observation Framework requires the `zbar` barcode reader library to be installed. On Linux this will require a user
with `sudo` privilege, and on Windows with Administrator privilege.

**For Windows** download and run the Windows installer from:
```
https://sourceforge.net/projects/zbar/files/zbar/0.10/zbar-0.10-setup.exe/download
```
⚠️ If you see an `ImportError` when importing zbar on Windows you will most likely need the [Visual C++ Redistributable Packages for Visual Studio 2013](https://www.microsoft.com/en-US/download/details.aspx?id=40784). Install `vcredist_x64.exe` if using 64-bit Python, `vcredist_x86.exe` if using 32-bit Python.

After installation of zbar, add the PATH to the system environment variables.
Also install ffmpeg and add the PATH to the system environment variables.
For adding PATH to the system environment variables see above "Updating System Environment for Windows".

**For Mac OS X**:
```
brew install zbar
brew install netcat
brew install ffmpeg
brew install portaudio
```

**For Linux** a typical installation is:
```
sudo apt-get install libzbar0
sudo apt-get install netcat
sudo apt-get install ffmpeg
sudo apt-get install portaudio19-dev python3-pyaudio
```

**For Unix** exact installations may vary for different Unix variants, see http://zbar.sourceforge.net/.

## Obtaining the Observation Framework

Clone [this](https://github.com/cta-wave/device-observation-framework) GitHub repository to the same machine/VM as the Test Runner installation.

OR 

Download the [zip file](https://github.com/cta-wave/device-observation-framework/archive/refs/heads/main.zip) and extract to your target folder.

Both can also be found by clicking on the "Code" tab at the top of the Device Observation Framework GitHub repository. 

## Installing the required Python packages

⚠️ Prior to running the install script, **Python version 3.10 or later** and **pip version 3** must be installed and on the execution PATH.
On Windows, add the Paths to Python to the system environment variables if they were not added during the installation. 

**On Linux and Mac OS** systems, prior to each user using the Observation Framework for the first time, run:

```shell
cd <full path to device-observation-framework>
./install.sh
```

**On Windows** systems, prior to each user using the Observation Framework for the first time, run:

```shell
cd <full path to device-observation-framework>
install_win.bat
```
⚠️ Ensure you use Windows PowerShell is for the above commands.
The device-observation-framework folder may also be named device-observation-framework-main

## Downloading Audio Mezzanine content 

It is important to download the correct Audio Mezzanine content. 

The Observation Framework requires the Audio Mezzanine files to compare with the recorded audio. The Audio Mezzanine content is not part of the repository and must be downloaded prior to running any audio observations.

The script always downloads the latest release of the Audio Mezzanine; if the user wants to download a previous release, then mezzanine_database.json can be modified manually to point to the required location.

**Downloading the latest mezzanine content**

Navigate to the audio_mezzanine folder and run:
```
shell
sudo ./import_audio_mezzanine.sh
```
The shell script creates a local copy of mezzanine_database.json. This json file contains the location of the mezzanine content that is then downloaded using download_mezzanine.py.

**Downloading a previous mezzanine release**

Edit mezzanine_database.json to point to the desired mezzanine location. The Python script can then be run directly to download the content:
```
shell
python3 download_mezzanine.py
```

## Configuring the Observation Framework

The "config.ini" file defines internal configurations for the Observation Framework.
The configuration can be adjusted based on different set up and requirements, e.g. user configurable timeouts and thresholds.

## Running the Observation Framework
To run Device Observation Framework enter:

⚠️ On Windows, ensure that Windows PowerShell is used.

```
shell
cd device-observation-framework
python observation_framework.py --input <file>
```
OR
```
python3 observation_framework.py --input <file>
```
(N.B. Python version must be 3.10 or greater)

e.g:
```
shell
python observation_framework.py --input D:\device-observation-framework-main\recording_file_name.mp4
```

Further information about running the Observation Framework can be found [here](README.md#running-the-device-observation-framework).
