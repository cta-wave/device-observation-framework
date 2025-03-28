# -*- coding: utf-8 -*-
"""DPCTF Device Observation Framework.

Entry point to the Device Observation Framework.

The Software is provided to you by the Licensor under the License, as
defined below, subject to the following condition.

Without limiting other conditions in the License, the grant of rights under
the License will not include, and the License does not grant to you, the
right to Sell the Software.

For purposes of the foregoing, “Sell” means practicing any or all of the
rights granted to you under the License to provide to third parties, for a
fee or other consideration (including without limitation fees for hosting
or consulting/ support services related to the Software), a product or
service whose value derives, entirely or substantially, from the
functionality of the Software. Any license notice or attribution required
by the License must also include this Commons Clause License Condition
notice.

Software: WAVE Observation Framework
License: Apache 2.0 https://www.apache.org/licenses/LICENSE-2.0.txt
Licensor: Consumer Technology Association
Contributor: Resillion UK Limited
"""
import argparse
import errno
import logging
import math
import os
import shutil
import sys
import traceback
from pathlib import Path
from typing import List, Tuple

import cv2

from dpctf_qr_decoder import (
    DPCTFQrDecoder,
    MezzanineDecodedQr,
    PreTestDecodedQr,
    TestStatusDecodedQr,
)
from exceptions import ConfigError, ObsFrameError, ObsFrameTerminate
from global_configurations import GlobalConfigurations
from log_handler import LogManager
from observation_framework_processor import ObservationFrameworkProcessor
from qr_recognition.qr_recognition import FrameAnalysis
from camera_calibration_helper import calibrate_camera

MAJOR = 2
MINOR = 0
PATCH = 2
BETA = ""
VERSION = f"{MAJOR}.{MINOR}.{PATCH}{BETA}"

QR_CODE_AREA_RATIO_TO_SIZE = 1.9
"""To detect whether full QR code area is found.
There are 4 mezzanine QR codes, left-top, right-top, left-down, right-down
QR code AREA (height and width) is 2 times bigger than its size
camera might not be possible to be angles exact 90 degree to screen 
this ratio set to slightly lower than 2"""


def rename_input_file(
    logger: logging.Logger,
    input_video_path_str: str,
    input_video_path: Path,
    session_token: str,
) -> None:
    """Rename the input file to session token
    <filename>_dpctf_<sessionID>
    """
    if session_token:
        file_name, file_extension = os.path.splitext(input_video_path_str)
        if session_token not in file_name:
            new_file_name = file_name + "_dpctf_" + session_token
            new_file_path = os.path.join(
                input_video_path.parent, new_file_name + file_extension
            )
            os.rename(input_video_path_str, new_file_path)

            # rename generated audio file as well
            audio_file_extension = ".wav"
            input_audio_path_str = file_name + audio_file_extension
            if os.path.exists(input_audio_path_str):
                new_audio_file_name = file_name + "_dpctf_" + session_token
                new_audio_file_path = os.path.join(
                    input_video_path.parent, new_audio_file_name + audio_file_extension
                )
                os.rename(input_audio_path_str, new_audio_file_path)
            logger.info("Recorded file renamed to '%s'.", new_file_path)


def iter_to_get_qr_area(
    vid_cap,
    camera_frame_rate: float,
    width: int,
    height: int,
    end_iter_frame_num: int,
    do_adaptive_threshold_scan: bool,
    global_configurations: GlobalConfigurations,
    starting_point_s: int,
    print_processed_frame: bool,
) -> Tuple:
    """Iterate video frame by frame and detect mezzanine QR codes area.

    Args:
        vid_cap: VideoCapture instance for the current file.
        camera_frame_rate: recording camera frame rate
        width: recording image width
        height: recording image height
        end_iter_frame_num: frame number where system stops search qr areas
        global_configurations: to get configuration from

    Returns:
        first_pre_test_qr_time: first pre test qr code detection time in ms
        qr_code_areas: qr_code_areas to crop when detecting qr code
    """
    logger = global_configurations.get_logger()
    test_status_found = False
    mezzanine_found = False
    first_pre_test_found = False
    first_pre_test_qr_time = 0
    qr_code_areas = [[], []]
    corrupted_frame_num = 0
    vid_cap.set(cv2.CAP_PROP_POS_MSEC, starting_point_s * 1000)
    len_frames = int(vid_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    starting_frame = math.floor(starting_point_s * camera_frame_rate)
    capture_frame_num = starting_frame

    while (len_frames + corrupted_frame_num) > capture_frame_num:
        got_frame, image = vid_cap.read()
        if not got_frame:
            if "video" in global_configurations.get_ignore_corrupted():
                # work around for camera has corrupted frame e.g.:GoPro
                corrupted_frame_num += 1
                capture_frame_num += 1
                continue
            else:
                logger.warning("Recording frame %d is corrupted.", capture_frame_num)
                break

        # print out where the processing is currently
        if print_processed_frame:
            if capture_frame_num % 50 == 0:
                print(f"Checking frame {capture_frame_num}...")

        analysis = FrameAnalysis(
            capture_frame_num, DPCTFQrDecoder(), max_qr_code_num_in_frame=3
        )

        rough_qr_code_areas = [[], []]
        # left half for mezzanine
        rough_qr_code_areas[0] = [0, 0, int(width / 2), height]
        # right half for test status
        rough_qr_code_areas[1] = [int(width / 2), 0, width, height]

        analysis.full_scan(image, rough_qr_code_areas, do_adaptive_threshold_scan)
        detected_qr_codes = analysis.all_codes()

        for detected_code in detected_qr_codes:
            if (
                isinstance(detected_code, PreTestDecodedQr)
                and not first_pre_test_found
                and starting_frame == 0
            ):
                first_pre_test_qr_time = capture_frame_num / camera_frame_rate * 1000
                first_pre_test_found = True
                logger.debug(
                    "First pre-test QR code is detected at time %f.",
                    first_pre_test_qr_time,
                )
            elif isinstance(detected_code, MezzanineDecodedQr) and not mezzanine_found:
                logger.debug(
                    "Frame Number=%d Location=%s",
                    detected_code.frame_number,
                    detected_code.location,
                )
                new_qr_code_area = [
                    detected_code.location[0],
                    detected_code.location[1],
                    detected_code.location[0] + detected_code.location[2],
                    detected_code.location[1] + detected_code.location[3],
                ]
                if not qr_code_areas[0]:
                    qr_code_areas[0] = new_qr_code_area
                else:
                    if new_qr_code_area[0] < qr_code_areas[0][0]:
                        qr_code_areas[0][0] = new_qr_code_area[0]
                    if new_qr_code_area[1] < qr_code_areas[0][1]:
                        qr_code_areas[0][1] = new_qr_code_area[1]
                    if new_qr_code_area[2] > qr_code_areas[0][2]:
                        qr_code_areas[0][2] = new_qr_code_area[2]
                    if new_qr_code_area[3] > qr_code_areas[0][3]:
                        qr_code_areas[0][3] = new_qr_code_area[3]

                if (
                    (qr_code_areas[0][2] - qr_code_areas[0][0])
                    > QR_CODE_AREA_RATIO_TO_SIZE * detected_code.location[2]
                ) and (
                    (qr_code_areas[0][3] - qr_code_areas[0][1])
                    > QR_CODE_AREA_RATIO_TO_SIZE * detected_code.location[3]
                ):
                    mezzanine_found = True
                    logger.debug(
                        "Mezzanine QR code area is detected successfully at: %s.",
                        qr_code_areas[0],
                    )

            elif (
                isinstance(detected_code, TestStatusDecodedQr) and not test_status_found
            ):
                logger.debug(
                    "Status=%s Location=%s",
                    detected_code.status,
                    detected_code.location,
                )
                qr_code_areas[1] = [
                    detected_code.location[0],
                    detected_code.location[1],
                    detected_code.location[0] + detected_code.location[2],
                    detected_code.location[1] + detected_code.location[3],
                ]
                test_status_found = True
                logger.debug(
                    "Test status QR code area is detected successfully at: %s.",
                    qr_code_areas[1],
                )
            else:
                continue

        capture_frame_num += 1

        # finish when both mezzanine and test status area found
        if test_status_found and mezzanine_found:
            return first_pre_test_qr_time, qr_code_areas

        # finish when end_iter_frame_num reached
        if capture_frame_num > end_iter_frame_num:
            logger.debug(
                "End of configured search is reached, search until frame number %d.",
                end_iter_frame_num,
            )
            # if not full area found set to unknown
            if not mezzanine_found:
                qr_code_areas[0] = []
                logger.info("Mezzanine QR code areas not detected successfully.")
            if not test_status_found:
                logger.info("Test Runner QR code areas not detected successfully.")
            return first_pre_test_qr_time, qr_code_areas

    # if not full area found set to unknown
    logger.debug("End of recording is reached.")

    if not mezzanine_found:
        qr_code_areas[0] = []
        logger.debug("Mezzanine QR code areas not detected successfully.")
    if not test_status_found:
        logger.debug("Test Runner QR code areas not detected successfully.")
    return first_pre_test_qr_time, qr_code_areas


def get_qr_code_area(
    input_video_path_str: str,
    global_configurations: GlobalConfigurations,
    do_adaptive_threshold_scan: bool,
    print_processed_frame: bool,
) -> Tuple:
    """get mezzanine qr code area from recording
    this will used used for intensive scan to crop the QR code area

    Args:
        input_video_path_str: input recording file
        global_configurations: to get configuration from

    Returns:
        first_pre_test_qr_time: first pre test qr code detection time in ms
        qr_code_areas: qr_code_areas to crop when detecting qr code
        pre_test_qr_code_area: qr_code_area to crop for pre test qr code
    """
    logger = global_configurations.get_logger()
    logger.info("Search '%s' to get QR code location...", input_video_path_str)

    qr_code_areas = [[], []]
    first_pre_test_qr_time = 0

    # default start search from 0s and finished at configuration from config.ini
    starting_point_s = 0
    search_qr_area_to = global_configurations.get_search_qr_area_to()
    # read user input range parameter
    qr_search_range = global_configurations.get_qr_search_range()

    input_video_path = Path(input_video_path_str).resolve()
    if not input_video_path.is_file():
        raise Exception(f"Recorded file '{input_video_path}' not found")

    vid_cap = cv2.VideoCapture(input_video_path_str)
    fps: float = vid_cap.get(cv2.CAP_PROP_FPS)
    width: int = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height: int = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = int(vid_cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps

    # if user input range parameter defined then update defaults
    if qr_search_range:
        starting_point_s = qr_search_range[1]
        qr_code_search_duration = qr_search_range[2]
        if starting_point_s > duration:
            raise ValueError("Starting point larger than recording duration.")
        search_qr_area_to = starting_point_s + qr_code_search_duration

    if fps < 1 or width <= 0 or height <= 0:
        vid_cap.release()
        open(input_video_path_str, "rb")
        # File is readable but invalid.
        raise OSError(errno.EINVAL, "Video is invalid")

    if search_qr_area_to != 0:
        try:
            first_pre_test_qr_time, qr_code_areas = iter_to_get_qr_area(
                vid_cap,
                fps,
                width,
                height,
                int(fps * search_qr_area_to),
                do_adaptive_threshold_scan,
                global_configurations,
                starting_point_s,
                print_processed_frame,
            )
        finally:
            vid_cap.release()
    else:
        vid_cap.release()

    # check qr_code_area
    # if not defined we just crop left half for mezzanine
    # right half for the test runner status
    qr_area_margin = global_configurations.get_qr_area_margin()
    for i in range(0, len(qr_code_areas)):
        if qr_code_areas[i]:
            qr_code_areas[i][0] -= qr_area_margin
            qr_code_areas[i][1] -= qr_area_margin
            qr_code_areas[i][2] += qr_area_margin
            qr_code_areas[i][3] += qr_area_margin
            if qr_code_areas[i][0] < 0:
                qr_code_areas[i][0] = 0
            if qr_code_areas[i][1] < 0:
                qr_code_areas[i][1] = 0
            if qr_code_areas[i][2] > width:
                qr_code_areas[i][2] = width
            if qr_code_areas[i][3] > height:
                qr_code_areas[i][2] = height
        else:
            # when qr_code_areas can not be detected
            if i == 0:
                # left half for mezzanine
                qr_code_areas[i] = [0, 0, int(width / 2), height]
                logger.info(
                    "QR code area for full scan is set to "
                    "left half of image for mezzanine QR code."
                )
            else:
                # right half for test status
                qr_code_areas[i] = [int(width / 2), 0, width, height]
                logger.info(
                    "QR code area for full scan is set to "
                    "right half of image for test status QR code."
                )

    pre_test_qr_code_area = [int(width / 4), 0, int((width / 4) * 3), height]

    return first_pre_test_qr_time, qr_code_areas, pre_test_qr_code_area


def run(
    input_video_files: List[str],
    global_configurations: GlobalConfigurations,
    do_adaptive_threshold_scan: bool,
    print_processed_frame: bool,
    log_manager: LogManager,
):
    """
    Calibrate camera and set camera calibration offset when calibration_file_path is given.
    Runs the observation framework process.
    """
    logger = global_configurations.get_logger()
    logger.info("Device Observation Framework (V%s) analysis started!", VERSION)
    calibration_offset = 0
    calibration_file_path = global_configurations.get_calibration_file_path()
    if calibration_file_path:
        logger.info("Camera calibration started, please wait.")
        calibration_offset = calibrate_camera(
            calibration_file_path, global_configurations, print_processed_frame
        )
        logger.info(
            "Camera calibration offset %.2fms is applied to the observations.",
            calibration_offset,
        )

    observation_framework = None
    file_index = 0
    qr_search_range = global_configurations.get_qr_search_range()
    if qr_search_range:
        file_index = qr_search_range[0]
    starting_camera_frame_number = 0

    if (global_configurations.get_system_mode()) == "debug":
        logger.info(
            "Device Observation Framework is running in 'debug' mode, "
            "it reads local configuration file from the 'configuration' folder "
            "and will not post results back to the Test Runner. "
            "The results will be saved locally. "
        )
    if do_adaptive_threshold_scan:
        logger.info("Intensive QR code scanning with an additional adaptiveThreshold.")

    (
        _first_pre_test_qr_time,
        qr_code_areas,
        pre_test_qr_code_area,
    ) = get_qr_code_area(
        input_video_files[file_index],
        global_configurations,
        do_adaptive_threshold_scan,
        print_processed_frame,
    )
    logger.info(
        "QR code area for full scan is set to %s for mezzanine QR code, and %s "
        "for test status QR code.",
        qr_code_areas[0],
        qr_code_areas[1],
    )

    # add pre-test qr code area
    # this removes the first and last vertical quarter of image
    if global_configurations.get_enable_cropped_scan_for_pre_test_qr():
        qr_code_areas.append(pre_test_qr_code_area)
        logger.info(
            "Additional QR code scan with roughly cropped area "
            "%s for pre-test QR code is enabled.",
            qr_code_areas[2],
        )
    for i in range(0, len(input_video_files)):
        input_video_path_str = input_video_files[i]
        logger.info("Analysing recording '%s'.", input_video_path_str)

        input_video_path = Path(input_video_path_str).resolve()
        if not input_video_path.is_file():
            raise Exception(f"Recorded file '{input_video_path}' not found")

        vid_cap = cv2.VideoCapture(input_video_path_str)
        fps: float = vid_cap.get(cv2.CAP_PROP_FPS)
        width: int = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height: int = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if fps < 1 or width <= 0 or height <= 0:
            vid_cap.release()
            open(input_video_path_str, "rb")
            # File is readable but invalid.
            raise OSError(errno.EINVAL, "Video is invalid")

        try:
            if observation_framework is None:
                observation_framework = ObservationFrameworkProcessor(
                    calibration_offset,
                    log_manager,
                    logger,
                    global_configurations,
                    fps,
                    do_adaptive_threshold_scan,
                )

            observation_framework.extract_audio(
                input_video_path_str, starting_camera_frame_number
            )

            last_camera_frame_number = observation_framework.iter_qr_codes_in_video(
                vid_cap,
                starting_camera_frame_number,
                qr_code_areas,
                print_processed_frame,
            )
            starting_camera_frame_number += last_camera_frame_number
        finally:
            vid_cap.release()

    if observation_framework:
        for input_video_path_str in input_video_files:
            rename_input_file(
                logger,
                input_video_path_str,
                input_video_path,
                observation_framework.pre_test_qr_code.session_token,
            )

    logger.info("The Device Observation Framework analysis has ended.")
    clear_up(global_configurations)


def clear_path(
    logger: logging.Logger, file_path: str, threshold: int, is_file_path: bool
) -> None:
    """
    file_path is either log, result path to clear
        log path: list of session log files and event files
        result path: list of session folders contain result file
    if number of logs or results exceeded configured threshold
    delete some file to release the disk space
    """
    if os.path.isdir(file_path):
        # Choose the function based on whether we want folders or files
        check_func = os.path.isfile if is_file_path else os.path.isdir
        full_path = [
            os.path.join(file_path, f)
            for f in os.listdir(file_path)
            if check_func(os.path.join(file_path, f))
        ]
        num_session = len(full_path)

        num_of_session_to_delete = num_session - threshold
        if num_of_session_to_delete > 0:
            remove_func = os.remove if is_file_path else shutil.rmtree
            oldest = sorted(full_path, key=os.path.getctime)[0:num_of_session_to_delete]
            logger.info(
                "Removing oldest %d file(s): %s!", num_of_session_to_delete, oldest
            )
            for oldest_session in oldest:
                remove_func(oldest_session)


def clear_up(global_configurations: GlobalConfigurations) -> None:
    """check log and result path to release the disk space
    global_configurations: to get threshold and path to clear
    """
    threshold = global_configurations.get_session_log_threshold()
    logger = global_configurations.get_logger()
    # both log and result path contain folders
    clear_path(logger, global_configurations.get_log_file_path(), threshold, False)
    clear_path(logger, global_configurations.get_result_file_path(), threshold, False)


def check_python_version(logger: logging.Logger) -> bool:
    """Check minimum Python version is being used.
    Returns:
        True if version is OK.
    """
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        return True
    logger.critical(
        "Aborting! Python version 3.9 or greater is required.\nCurrent Python version is %d.%d.",
        sys.version_info.major,
        sys.version_info.minor,
    )
    return False


def process_input_video_files(
    input_str: str, global_configurations: GlobalConfigurations
) -> list:
    """
    process input video files from input file string
    and return input video file path in a list
    """
    input_video_files = []
    input_video_path = Path(input_str).resolve()

    if not os.path.isabs(input_video_path):
        input_video_path = os.path.abspath(input_video_path)

    if input_video_path.is_dir():
        input_files = os.listdir(input_video_path)
        for input_file in input_files:
            # skip audio files
            if ".wav" in input_file:
                continue
            full_path = os.path.join(input_video_path, input_file)
            if Path(full_path).resolve().is_file():
                input_video_files.append(full_path)
            else:
                global_configurations.get_logger().warning(
                    "%s is not a file, skipped!", full_path
                )
    else:
        input_video_files.append(str(input_video_path))

    # sort input files based on the configuration
    sort_input_files_by = global_configurations.get_sort_input_files_by()
    if sort_input_files_by == "filename":
        sorted(input_video_files)
    else:
        input_video_files.sort(key=os.path.getmtime)
    return input_video_files


def process_run(
    input_str: str,
    log_manager: LogManager,
    global_configurations: GlobalConfigurations,
    do_adaptive_threshold_scan: bool,
):
    """process run and handel exceptions"""
    logger = global_configurations.get_logger()
    input_video_files = process_input_video_files(input_str, global_configurations)
    try:
        run(
            input_video_files,
            global_configurations,
            do_adaptive_threshold_scan,
            True,  # print out processed frame
            log_manager,
        )
    except ObsFrameTerminate as e:
        logger.exception(
            "Serious error is detected!\n%s\nSystem is terminating!", e, exc_info=False
        )
        clear_up(global_configurations)
        sys.exit(1)
    except ConfigError as e:
        logger.exception("Serious error detected!\n%s", e, exc_info=False)
        clear_up(global_configurations)
        sys.exit(1)
    except ObsFrameError as e:
        logger.exception("Serious error detected!\n%s", e, exc_info=False)
        clear_up(global_configurations)
        sys.exit(1)
    except Exception as e:
        logger.exception(
            "Serious error is detected!\n%s: %s", e, traceback.format_exc()
        )
        clear_up(global_configurations)
        sys.exit(1)

    logger.info(
        "The Device Observation Framework has completed the analysis of all selected recordings, "
        "The Device Observation Framework is exiting."
    )


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"DPCTF Device Observation Framework (v{VERSION})"
    )
    parser.add_argument(
        "--input", required=True, help="Input recording file / path to analyse."
    )
    parser.add_argument(
        "--log",
        nargs="+",  # Allow 1 or 2 values
        help="Logging levels for log file writing and console output.",
        default=["info", "info"],
        choices=["info", "debug"],
    )
    parser.add_argument(
        "--scan",
        help="Scan depth for QR code detection.",
        default="general",
        choices=["general", "intensive"],
    )
    parser.add_argument(
        "--mode",
        help="System mode is for development purposes only.",
        default="",
        choices=["", "debug"],
    )
    parser.add_argument(
        "--ignore_corrupted", help="Specific condition to ignore.", default=""
    )
    parser.add_argument(
        "--range",
        help="Search QR codes to crop the QR code area for better detection. "
        "QR codes area detection includes mezzanine QR codes and Test Status QR code.",
        default="",
        metavar="id(file_index):start(s):duration(s)",
    )
    parser.add_argument(
        "--calibration", help="Camera calibration recording file path.", default=""
    )

    args = parser.parse_args()
    do_adaptive_threshold_scan = False
    if args.scan == "intensive":
        do_adaptive_threshold_scan = True

    global_configurations = GlobalConfigurations()
    global_configurations.set_ignore_corrupted(args.ignore_corrupted)
    global_configurations.set_system_mode(args.mode)
    global_configurations.set_qr_search_range(args.range)
    global_configurations.set_calibration_file_path(args.calibration)

    log_file_path = global_configurations.get_log_file_path()
    log_file = log_file_path + "/events.log"
    if len(args.log) == 1:
        args.log = [args.log[0], args.log[0]]
    log_manager = LogManager(log_file, args.log[0], args.log[1])

    if not check_python_version(global_configurations.get_logger()):
        sys.exit(1)

    process_run(
        args.input,
        log_manager,
        global_configurations,
        do_adaptive_threshold_scan,
    )


if __name__ == "__main__":
    main()
