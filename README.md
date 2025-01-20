# CTA WAVE Streaming Media Test Suite - Devices: Observation Framework

This repository contains the Observation Framework component of the "WAVE Streaming Media Test Suite - Devices".
The Observation Framework determines pass or fail results, based on observations of screen recordings of tests which are run on a device by the Test Runner.

The test suite implements the tests and observations as defined in the CTA WAVE Device Playback Capabilities specification. For more information:
* [CTA WAVE project](https://CTA.tech/WAVE)
* Latest published [Device Playback Capabilities specification](https://shop.cta.tech/collections/standards/products/web-application-video-ecosystem-device-playback-capabilities)
* [Contact](standards@CTA.tech) the CTA

## First set up the Test Runner

The Device Observation Framework **must** work together with the Test Runner.
The Test Runner should be set up prior to the Device Observation Framework.
Please follow the instructions in the main WAVE Streaming Media Test Suite [dpctf-deploy-readme](https://github.com/cta-wave/dpctf-deploy/blob/master/README.md).

<span style="color:red">**Check that the Test Runner is functioning correctly and able to run tests prior to installing the Observation Framework.**</span>

## Setting up the Device Observation Framework 

* Setting up **inside Docker container**

  The [dpctf-deploy repo](https://github.com/cta-wave/dpctf-deploy) contains scripts to set up Device Observation Framework **inside a Docker container**. It also contains a script to run Device Observation Framework analysis. Instructions can be found here [dpctf-deploy-readme](https://github.com/cta-wave/dpctf-deploy/blob/master/README.md).

* Or setting up **without Docker**

  The Device Observation Framework can also be installed **without Docker**; instructions can be found [here.](https://github.com/cta-wave/device-observation-framework/wiki/Installing-the-Device-Observation-Framework-without-Docker)

## Running the Device Observation Framework

Ahead of running Device Observation Framework the user **MUST** set up the camera and device under test (DUT) carefully to record the tests; instructions can be found [Obtain-recording-files](https://github.com/cta-wave/device-observation-framework/wiki/Obtain-recording-files). Once the camera and DUT set-up is correct then Test Runner sessions can be analysed. See https://web-platform-tests.org/running-tests/ for instructions on how to run a test session. Prior to starting the session, begin the camera recording (ensuring that camera is set to record at around of 120 fps). Record the Test Runner session from beginning to end and then stop the camera recording.

Only one session may be contained in a single recording. A single session may contain multiple tests.

Once the recording is complete, follow the camera manufacturer's instructions to transfer the recorded file to the PC where Observation Framework is installed.

Command to run the Device Observation Framework can be found in [dpctf-deploy](https://github.com/cta-wave/dpctf-deploy/blob/master/README.md).

You **MUST** add the .mp4 extension to the file name.

where **file** specifies the path to the recording to be analysed:

**If the session is recorded to a single file**
then specify the path and recording filename for the **file** parameter.

**If the camera splits a single session's recording into multiple files**
then specify the path to the folder containing the recorded files. Note that:
* a folder must only contain the files for a **single session** recording.
* typically a camera will name the files with some form of ascending number. By default the Observation Framework will 
alphabetically sort the filenames and use this as the recording order. If for a particular camera this is unsuitable
  then in the **config.ini** file, the parameter '*sort_input_files_by*' can be set to *"timestamp"* to instead try sorting by file timestamp. 
  If both these approaches fail, then the user will need to rename the files such that when alphabetically
  sorted they are in the correct order.

The Observation Framework will analyse the recording and post the results to the Test Runner for viewing on Test Runner's results pages. Note that the observation processing may take considerable time, depending on the duration of the session recording.

When a selected test includes an observation *"The presented sample matches the one reported by the currentTime value within the tolerance of the sample duration."*, a CSV file contains observation data will be generated at ```logs/<session-id>/<test-path>_time_diff.csv```. Where is contains current times and calculated time differences between current time and media time.

At the end of the process the Observation Framework will rename the file recording to:
```<file_name>_dpctf_<session-id>.<extension>```

### Additional Options

Observation framework can be run with specific mode enabled by passing some optional arguments.

optional arguments:
```
  --range {id(file_index):start(s):duration(s)}
                        Search QR codes to crop the QR code area for better detection.
                        QR codes area detection includes mezzanine QR codes and Test Status QR code.
  --log debug           Logging level to write to log file.
  --scan intensive      Scan depth for QR code detection.
  --mode debug          System mode is for development purposes only.
  --ignore_corrupted video
                        Specific condition to ignore. To support recording devices that has corrupted video or audio.
  --calibration
                        Camera calibration recording file path.
```

* Where **range** this is optional argument for video only tests. However, when the 1st test is audio only test it is important to set scan range so that the process can find mezzanine QR code area correctly for mixed video and audio tests. Setting the range is also useful to speed up the processing time when observing audio only tests. The range argument requires three digit variables separated by ":", ```{id(file_index):start(s):duration(s)}```.

    For example, ```--range 0:20:2``` states for scan QR code area in 1st recording file starts from 20 seconds and ends the scan at 22 seconds when QR code area not detected.

    * id: file_index normally 0 if one recording file is selected to be observed
    * start: start of the scan in seconds from beginning of the recording file
    * duration: scan duration in seconds

* Where **log** specifies log level. Default value is "info" when not specified. When ```--log debug``` is selected, full QR code detection will be extracted to a CSV file at ```logs/<session-id>/qr_code_list.csv```, and the system displays more information to the terminal as well as to a log file ```logs/<session-id>/session.log```.
This includes information such as decoding of QR codes:
    * Content ID, Media Time, Frame Number, Frame Rate
    * Status, Action, Current Time, Delay

* Where **scan** specifies scan method to be used. Default value is "general" when not specified. ```--scan intensive``` makes the QR code recognition more robust by allowing an additional adaptive threshold scan, however this will increase processing time. This option is to be used where it is difficult to take clear recordings, such as testing on a small screen devices like mobile phones.

* Where **mode** specifies the Observation Framework processing mode, which can be set to debug. In debug system mode the observation process reads the configuration files from configuration folder and save observation results locally instead of import back to the test runner. Running in debug system mode is useful when debugging recording taken by someone else and without test runner, or debugging previous recording where the test id is no longer valid for the current test runner set up. More detailed instructions can be found [here](https://github.com/cta-wave/device-observation-framework/wiki/Debug-Observation-Framework).

* Where is it not recommended, **ignore_corrupted** specifies the special condition to be ignored by observation framework. We have added this feature to work around some cameras produce corrupted capture. When "--ignore_corrupted video" is set, the Observation Framework will ignore the corrupted recording frame and carry on reading the next frames in the recording instead of ending the process early. Impact of using this option for audio testing is to be confirmed, it might cause the audio tests and A/V sync test to fail.

* Where **calibration** specifies the calibration recording file path. After processing the calibration recording file prior to the observation process, the audio and video recording offset will be applied to the Observation Framework.

## Troubleshooting

### Failed to get configuration file from test runner:
Check that Test Runner is installed and running without problems and that it is visible to the Observation Framework.

### Observation results are reporting large number of missing frames:
If a large number of expected frames containing QR codes are missing, then this indicates something is seriously wrong. The Observation Framework will terminate the session analysis with an error result. (the threshold for this can be set in the *"config.ini"* file with the *'missing_frame_threshold'* parameter).

If this occurs, check the quality of the recorded video. Ensure that the camera/device set up instructions described earlier have been followed.

More information about Debugging Observation Failures can be found [here](https://github.com/cta-wave/device-observation-framework/wiki/Debugging-Observation-Failures).

## Adding Support for New Tests to the Observation Framework
Documentation for Adding Support for New Tests to the Observation Framework can be found [here](https://github.com/cta-wave/device-observation-framework/wiki/Adding-Support-for-New-Tests-to-the-Observation-Framework).

## Release Notes for Release v2.0.2

### Implemented:
* Installation and usage instructions (in this README).
* Installation scripts for Linux shells and Windows batch file.
* End-to-end Observation Framework functionality.
* Analysis of multiple tests in one session recording.
* Result reporting to Test Runner.
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

* White noise based audio tests implemented for:
  * 8.2 sequential-track-playback.html
  * 8.3 random-access-to-fragment.html
  * 8.4 random-access-to-time.html
  * 8.6 regular-playback-of-chunked-content.html
  * 8.7 regular-playback-of-chunked-content-non-aligned-append.html
  * 8.8 playback-over-wave-baseline-splice-constraints.html
  * 8.9 out-of-order-loading.html
  * 8.10 overlapping-fragments.html
  * 8.12 playback-of-encrypted-content.html
  * 8.13 restricted-splicing-of-encrypted-content-https.html
  * 8.14 sequential-playback-of-encrypted-and-non-encrypted-baseline-content-https.html
  * 9.2 regular-playback-of-a-cmaf-presentation.html
  * 9.3 random-access-of-a-wave-presentation.html
  * 9.4 splicing-of-wave-program-with-baseline-constraints.html
  * 9.6 long-duration-playback.html

---

**NOTE**
No audio switching for tests 8.8, 8.9, 8.13, 8.14 and 9.4

---
