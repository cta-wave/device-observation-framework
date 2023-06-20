# CTA WAVE DPCTF Device Observation Framework

This repository contains the Device Observation Framework.
The DPCTF Device Observation Framework determines pass or fail results, based on observations of screen recordings of tests which are run on a device by the DPCTF Test Runner.

DPCTF is the Device Playback Compatibility Task Force of the CTA WAVE Project (see https://CTA.tech/WAVE and standards@CTA.tech for more info).

## First set up the DPCTF Test Runner

DPCTF Device Observation Framework **must** work together with the DPCTF Test Runner.
The DPCTF Test Runner should be set up prior to the DPCTF Device Observation Framework.
Please follow the instructions at https://github.com/cta-wave/dpctf-deploy.

<span style="color:red">**Check that the Test Runner is functioning correctly and able to run tests prior to installing the Observation Framework.**</span>

## Setting up the Device Observation Framework

### Installation
The Observation Framework **must** be installed on same machine as the Test Runner is deployed.

Test Runner is deployed as a service running inside a Docker container.
The Observation Framework **must** be installed outside of Docker or Docker Desktop and run outside of the docker from the windows command line.
Make sure that the command line or PowerShell that is used for running OF is not inside the docker or docker desktop.

⚠️ This Observation Framework release has been tested on Ubuntu 18.04 LTS and Windows 10. However, as per the Test Runner, it is highly recommended to use Linux for production purposes.

### Updating System Environment for Windows 
There are a number of points in these instructions that will direct you to add the necessary path(s) to Windows System Variables under the PATH entry. You will need to add the Path(s) to the folder(s) that will contain the WAVE Test Suite files you will create, Python, Docker Desktop, ZBar and any others as noted in these instructions. This is so the system knows where to find them. There may be additional Paths necessary. When a command returns an error such as “file not found” check to see if the Path is in the Environment System Variables under “PATH”. If not, add the missing Path. 
To add to or modify the System Environment Variables. 
1.	Follow the instructions in the various ReadMe files for Windows, not Unix/Linux or Mac OS X.
2.	Run all commands using Windows Terminal/PowerShell. Do not run them using Bash in a Linux terminal. 
3.	If a command in Windows PowerShell/Terminal stalls or hangs up, use <Control + C> to gracefully exit. 

* Search for “Edit System Environmental Variables” in the search bar. Click on it in the popup. 
* Select “Environment Variables”
* Under “System variables” (lower box), select “Path”
* Then select Edit
* Select “New” and enter the desired Path.
* Select “New” again for each new path you wish to add. 
* When done, close the Environment Variables screens AND the Windows PowerShell/Terminal, if you have it open, to ensure the Paths are updated.

### Required Libraries
The Observation Framework requires the 'zbar' bar code reader library to be installed. On Linux this will require a user
with 'sudo' privilege, and on Windows with Administrator privilege.

**For Windows** download and run the Windows installer from:
```
https://sourceforge.net/projects/zbar/files/zbar/0.10/zbar-0.10-setup.exe/download
```
After installation of zbar, add the PATH to the system environment variables. See above "Updating System Environment for Windows".

**For Mac OS X**:
```
brew install zbar
brew install netcat
```

**For Unix** exact installations may vary for different Unix variants, see http://zbar.sourceforge.net/.

**For Linux** a typical installation is:
```
sudo apt-get install libzbar0
sudo apt-get install netcat
```

### Obtain the Observation Framework

Clone this github (i.e. https://github.com/cta-wave/device-observation-framework ) to the same machine/VM as the DPCTF Test Runner installation.
OR 
Download the Zip file https://github.com/cta-wave/device-observation-framework/archive/refs/heads/main.zip and extract to your target folder.
Both can also be found by clicking on the Code tab at the top of the Device Observation Framework landing page. 

### Installing the required Python packages
Prior to running the install script, **python version 3.6 to 3.9** and **pip version 3** must be installed and on the execution PATH.

On windows, add the Paths to Python to the system environment variables if they were not added during the installation. 

Note: If your system uses python version 3.10 or greater you will have to downgrade to one of the supported versions mentioned above. Some of the python packages required by the observation framework are not supported in python version 3.10 or greater.

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
Note: Makes sure that the WindowsPowerShell is used for the above commands.
The device-observation-framework folder may also be named device-observation-framework-main

### Observation Framework Configuration

The "config.ini" file defines internal configurations for the Observation Framework.
The configuration can be adjusted based on different set up and requirements, e.g. user configurable timeouts and thresholds.

## Obtain recording files

The Observation Framework operates on camera recordings of the device's screen whilst running tests under the DPCTF Test Runner. These test materials contain QR codes which must be accurately captured for the Observation Framework to interpret.

### Camera requirements
For the Phase 1 Observation Framework a variety of cameras should be suitable. (**NOTE:** this will **not** be the case for Phase 2 which will likely require very specific camera model(s)... TBD.)

The camera's requirements are:
* produces an output recording file in a format compatible with the OpenCV library (typically a .mp4 or .mov format). Domestic cameras from Sony, Canon, GoPro have been tried and all produced OpenCV compatible output.
* support recordings at a minimum of 119 frames per second at full HD.
* sufficient quality lens/sensor to allow sharp QR code capture at low resolutions on the smallest screen device to be tested. Note that small screen devices such as mobile phones will be more demanding than a e.g. a large screen TV device.

### Recording environment set up
The set up needs to be in a light-controlled environment and the camera configured to record high quality footage to allow consistent QR code detection. **It is highly unlikely that simply setting up the equipment on a desk in a standard office environment will produce satisfactory results!**

**More detailed guidance, and example videos are contained in "how_to_take_clear_recordings.pptx", available to download from https://dash-large-files.akamaized.net/WAVE/assets/YanJiang-how_to_take_clear_recordings.pptx.zip .**

For the camera/device set up:
* The device needs to be in a light-controlled environment with no bright surrounding lights, and no glare or reflections on the device screen.
* The device needs to be mounted on a stable stand/support. The camera needs mounting on a stable tripod with lens pointing directly at the device screen at a 90 degree angle.
* The camera should be zoomed in to capture the display as large as possible whilst still containing all the screen image including the red edge markers. For longer screens try only include just the aera including the red edge markers but not the device. It is important to make is playback eara as big as possible to capture clear QR code. For smaller and loger devices it is recommended to zoom in as closly as possible and exclude part of the device edge to make the QR code bigger.
* The camera should be manually focused on the device screen to produce a sharp image.
* The camera must be set to record at a minimum of 119 frames per second in full HD.
* The device's screen brightness needs to be adjusted to be neither too bright nor too dim. Too dim and the QR code cannot be discerned. But too bright and the white will "bleed" and prevent the QR code being recognised. See below for some examples.
* Depending on the device and sofware being used to run the tests, some device/software specific configuration may be required. For e.g. by default some browsers may add menu footers or headers that could partially obscure the QR codes. These will need to be set into e.g. a "full screen" mode. If any part of a QR code is obscured then the Observation Framework cannot operate.

Once the camera/device are set up, **DO NOT** change or alter settings during the recording. If changes are necessary then a new recording shall be taken. 

Note: Minimizing time between the start of recording and when the pre-test QR code shows up 
helps Device Observation Framework to process faster and give test results quicker.

### **Clear capture example:**

![image](images/good_capture_example.png)

### **Examples of good and bad captures**
The QR codes outlined in GREEN were successfully decoded. Those outlined in RED failed to be decoded:

![image](images/good_and_bad_capture_example.png)

### How to verify the camera setup
For the initial set up, we recommand a user try to run a sequential track playback test.

From Test Runner select and run the "*/<selected_tests_group>/sequential-track-playback__stream__.html*" test. (See Test Runner documentation for how to run tests: https://github.com/cta-wave/dpctf-test-runner and https://web-platform-tests.org/running-tests/ ). 

Once the recording is taken, the following steps should be followed to verify the camera setup and the recording:
* Try playing back the recording to check that the full duration of the test session is recorded. 
* The recording captured full clear QR codes. Nothing obscured the screen, there is no blur in the QR codes and they are not too dim or too bright. The focus is stable for the whole duration of the recording.
* Try to run the OF with the recording, and there shall be no exceptions or error raised by OF. When the camera/device set up does not meet the requirement, which makes it unable to capture clear QR codes, the following exceptions will be raised by OF. 

```shell
At camera frame N there were X consecutive camera frames where no mezzanine qr codes were detected. Device Observation Framework is exiting, and the remaining tests are not observed.
```
* Check the observation result. If there are a lot of missing frames reported, we recommend user to look at the recording manually to observe whether the reported missing frames are actually missing from the recording. This can be done by jumping to any of the previous frames, which are close to the target frame, then go frame by frame. If the reported missing frame is present in the recording, the set up can be improved slightly to get a better recording.

Above steps can be repeated if necessary in order to find the best set up for the selected device and the camera. For a small screen devices, such as a mobile phone, it is more difficult to find the good set up. A better camera or a better lense, such as a micro lens which can capture small detailes, might required for testing on a smaller screen devices. 

## Using the DPCTF Device Observation Framework
Once the device and camera setup is correct then Test Runner sessions can be analysed. See https://web-platform-tests.org/running-tests/ for instructions on how to run a test session. Prior to starting the session, begin the camera recording (ensuring that camera is set to record at minimum of 119 fps). Record the Test Runner session from begining to end and then stop the camera recording.

Only one session may be contained in a single recording. A single session may contain multiple tests.

Once the recording is complete, follow the camera manufacturer's instructions to transfer the recorded file to the PC where Observation Framework is installed.

To run DPCTF Device Observation Framework enter:

```shell
cd device-observation-framework

python observation_framework.py --input <file> --log <info|debug> --scan <general|intensive>

OR

python3 observation_framework.py --input <file> --log <info|debug> --scan <general|intensive>

(n.b. Python version must be 3.6 or greater)
```

e.g:
```shell
python observation_framework.py --input D:\device-observation-framework-main\recording_file_name.mp4
```
IMPORTANT: Make sure Makes sure that the WindowsPowerShell is used for the above commands on windows.
You **MUST** add the .mp4 extension to the file name.


where **log** (optional) specifies log level. Default value is "info" when not specified. See "Additional Options" section below for more details.

where **scan** (optional) specifies scan method to be used. Default value is "general" when not specified. See "Additional Options" section below for more details.

where **file** specifies the path to the recording to be analysed:

**If the session is recorded to a single file**
then specify the path and recording filename for the **file** parameter.

**If the camera splits a single session's recording into multiple files**
then specify the path to the folder containing the recorded files. Note that:
* a folder must only contain the files for a **single session** recording.
* typically a camera will name the files with some form of ascending number. By default the Observation Framework will 
alphabetically sort the filenames and use this as the recording order. If for a particular camera this is unsuitable
  then in the **config.ini** file, the parameter '*sort_input_files_by*' can be set to *"timestamp"* to instead try sorting by file timestamp. 
  If both these approaches fail then the user will need to rename the files such that when alphabetically
  sorted they are in the correct order.

The Observation Framework will analyse the recording and post the results to the Test Runner for viewing on Test Runner's results pages. Note that the observation processing may take considerable time, depending on the duration of the session recording.

When a selected test includes an observation *"The presented sample matches the one reported by the currentTime value within the tolerance of the sample duration."*, a CSV file contains observation data will be generated at ```logs/<session-id>/<test-path>_time_diff.csv```. Where is contains current times and calculated time differences between current time and media time.

At the end of the process the Observation Framework will rename the file recording to:
```<file_name>_dpctf_<session-id>.<extension>```

**Additional Options:**
* When ```--log debug``` is selected, full QR code detection will be extracted to a CSV file at ```logs/<session-id>/qr_code_list.csv```, and the system displays more information to the terminal as well as to a log file ```logs/<session-id>/session.log```.
This includes information such as decoding of QR codes:
    * Content ID, Media Time, Frame Number, Frame Rate
    * Status, Action, Current Time, Delay

* ```--scan intensive``` makes the QR code recognition more robust by allowing an additional adaptive thresholded scan, however this will increase prossing time. This option is to be used where it is difficult to take clear repcordings, such as testing on a small screen devices like mobile phones.

## Troubleshooting

### Http connection exception raised:
Check that Test Runner is installed and running without problems and that it is visible to the Observation Framework.

### Observation results are reporting large number of missing frames:
If a large number of expected frames containing QR codes are missing then this indicates something is seriously wrong. The Observation Framework will terminate the session analysis with an error result. (the threshold for this can be set in the *"config.ini"* file with the *'missing_frame_threshold'* parameter).

If this occurs, check the quality of the recorded video. Ensure that the camera/device set up instructions described earlier have been followed.

# Adding Support for New Tests to the Observation Framework
When new tests are added to the **dcptf-tests** repository, support for these will also need adding to the Observation Framework.
The scale of changes required will depend on how much the new tests diverge from existing tests.
## a) When test and observations are the same as an existing test
For example, the '*playback-of-encrypted-content*' test uses the same Observation Framework test code and observations as the (unencrypted) '*sequential_track_playback*' test.
To add such a test simply requires adding a new testname mapping to the existing test module and class name in the *"of_testname_map.json"* file. For example:

    "playback-of-encrypted-content.html": [
        "sequential_track_playback",
        "SequentialTrackPlayback"
    ],

## b) When correct observations exist but new test requires different combination of observations
For example, the '*regular-playback-of-a-cmaf-presentation*' test uses the same test logic as the '*sequential_track_playback*' test.
However, it requires a different list of observations.
Create a new test code module containing a new test class derived from an existing test.
Then override the method to provide the correct list of observations, for example:

    class RegularPlaybackOfACmafPresentation(SequentialTrackPlayback):
        def _init_observations(self) -> None:
            self.observations = [...]

Add the new test name, python module, and class name to the *"of_testname_map.json"* file.

## c) When correct observations exist within an existing test but require different parameters
For example, the '*random-access-to-time*' test uses the same observations as the '*sequential_track_playback*' test. However, it requires different parameters to be passed.
Create a new test code module containing a new test class derived from an existing test with the same observations.
Then override the appropriate methods to provide the correct parameters for the observations, for example:

    class RandomAccessToTime(SequentialTrackPlayback):
        def _init_parameters(self) -> None:
            [...]

        def _get_first_frame_num(self, frame_rate: Fraction) -> int:
            [...]

        def _get_expected_track_duration(self) -> float:
            [...]

Add the new test name, python module, and class name to the *"of_testname_map.json"* file.

## d) When brand new observations are required
Create new observation class(es) either derived from an existing observation if an appropriate one exists, or derived from the '_Observation_' base class.
Override methods as needed and provide a *make_observation()* method. For example,

    class EverySampleRendered(Observation):
        def __init__(self, global_configurations: GlobalConfigurations, name: str = None):
            [...]

        def make_observation( self, test_type, mezzanine_qr_codes: List[MezzanineDecodedQr],
                            _unused, parameters_dict: dict ) -> Dict[str, str]:
            [...]

Create a new test code module and class as described in (c) above. Implement a *make_observations()* method that calls the required observations, and returns a list of pass/fail results.
For example:

    def make_observations(
        self,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        test_status_qr_codes: List[TestStatusDecodedQr],
    ) -> List[dict]:
        [...]

Add the new test name, python module, and class name to the *"of_testname_map.json"* file.

# Release Notes for Release V1.1.0

## Implemented:
* Installation and usage instructions (in this README).
* Installation scripts for Linux shells and Windows batch file.
* End-to-end Observation Framework functionality.
* Analysis of multiple tests in one session recording.
* Result reporting to DPCTF Test Runner.
* QR code based video tests implemented for:
  * 8.2 sequential-track-playback.html
  * 8.3 random-access-to-fragment.html
  * 8.4 random-access-to-time.html
  * 8.5 switching-set-playback.html
  * 8.6 regular-playback-of-chunked-content.html
  * 8.7 regular-playback-of-chunked-content-non-aligned-append.html
  * 8.8 playback-over-wave-baseline-splice-constraints.html
  * 8.9 out-of-order-loading.html
  * 8.10 overlapping-fragments.html
  * 8.11 fullscreen-playback-of-switching-sets.html
  * 8.12 playback-of-encrypted-content.html
  * 8.13 restricted-splicing-of-encrypted-content-https.html
  * 8.14 sequential-playback-of-encrypted-and-non-encrypted-baseline-content-https.html
  * 8.15 source-buffer-re-initialization-without-changetype.html
  * 8.16 source-buffer-re-initialization-with-changetype.html
  * 8.17 buffer-underrun-and-recovery.html
  * 8.18 truncated-playback-and-restart.html
  * 8.19 low-latency-initialization.html
  * 8.20 low-latency-playback-over-gaps.html
  * 8.21 mse-appendwindow.html
  * 8.22 low-latency-short-buffer-playback.html
  * 8.23 random-access-from-one-place-in-a-stream-to-a-different-place-in-the-same-stream.html
  * 9.2 regular-playback-of-a-cmaf-presentation.html
  * 9.3 random-access-of-a-wave-presentation.html
  * 9.4 splicing-of-wave-program-with-baseline-constraints.html
  * 9.6 long-duration-playback.html

## Not yet implemented:
* Audio observations - audio has been added to the required tests and you will hear white noise (pseudo noise) without any obvious gaps throughout the playback of these tests. Audio observations will be available in a future release.
