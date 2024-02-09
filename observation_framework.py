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
Contributor: Eurofins Digital Product Testing UK Limited
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

from dpctf_qr_decoder import (DPCTFQrDecoder, MezzanineDecodedQr,
                              PreTestDecodedQr, TestStatusDecodedQr)
from exceptions import ConfigError, ObsFrameTerminate
from global_configurations import GlobalConfigurations
from log_handler import LogManager
from observation_framework_processor import ObservationFrameworkProcessor
from qr_recognition.qr_recognition import FrameAnalysis

MAJOR = 2
MINOR = 0
PATCH = 0
BETA = ""
VERSION = f"{MAJOR}.{MINOR}.{PATCH}{BETA}"

logger = logging.getLogger(__name__)

QR_CODE_AREA_RATIO_TO_SIZE = 1.9
"""To detect whether full QR code area is found.
There are 4 mezzanine QR codes, left-top, right-top, left-down, right-down
QR code AREA (height and width) is 2 times bigger than its size
camera might not be possible to be angles exact 90 degree to screen 
this ratio set to slightly lower than 2"""


def rename_input_file(
    input_video_path_str: str, input_video_path: Path, session_token: str
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
            logger.info(f"Recorded file renamed to '{new_file_path}'.")


def iter_to_get_qr_area(
    vidcap,
    camera_frame_rate: float,
    width: int,
    height: int,
    end_iter_frame_num: int,
    do_adaptive_threshold_scan: bool,
    global_configurations: GlobalConfigurations,
    starting_point_s: int,
) -> Tuple:
    """Iterate video frame by frame and detect mezzanine QR codes area.

    Args:
        vidcap: VideoCapture instance for the current file.
        camera_frame_rate: recording camera frame rate
        width: recording image width
        height: recording image height
        end_iter_frame_num: frame number where system stops search qr areas
        global_configurations: to get configuration from

    Returns:
        first_pre_test_qr_time: first pre test qr code detection time in ms
        qr_code_areas: qr_code_areas to crop when detecting qr code
    """
    test_status_found = False
    mezzanine_found = False
    first_pre_test_found = False
    first_pre_test_qr_time = 0
    qr_code_areas = [[], []]
    corrupted_frame_num = 0
    vidcap.set(cv2.CAP_PROP_POS_MSEC, starting_point_s*1000)
    len_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    starting_frame = math.floor(starting_point_s * camera_frame_rate)
    capture_frame_num = starting_frame

    while (len_frames + corrupted_frame_num) > capture_frame_num:
        got_frame, image = vidcap.read()
        if not got_frame:
            if "video" in global_configurations.get_ignore_corrupted():
                # work around for gopro
                corrupted_frame_num += 1
                capture_frame_num += 1
                continue
            else:
                logger.warning(
                    f"Recording frame {capture_frame_num} is corrupted."
                )
                break

        # print out where the processing is currently
        if capture_frame_num % 10 == 0:
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
                and starting_frame==0
            ):
                first_pre_test_qr_time = capture_frame_num / camera_frame_rate * 1000
                first_pre_test_found = True
                logger.debug(
                    f"First pre-test QR code is detected at time {first_pre_test_qr_time}."
                )
            elif isinstance(detected_code, MezzanineDecodedQr) and not mezzanine_found:
                logger.debug(
                    f"Frame Number={detected_code.frame_number} Location={detected_code.location}"
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
                        f"Mezzanine QR code area is detected successfully at: "
                        f"{qr_code_areas[0]}."
                    )

            elif (
                isinstance(detected_code, TestStatusDecodedQr) and not test_status_found
            ):
                logger.debug(
                    f"Status={detected_code.status} Location={detected_code.location}"
                )
                qr_code_areas[1] = [
                    detected_code.location[0],
                    detected_code.location[1],
                    detected_code.location[0] + detected_code.location[2],
                    detected_code.location[1] + detected_code.location[3],
                ]
                test_status_found = True
                logger.debug(
                    f"Test status QR code area is detected successfully at: "
                    f"{qr_code_areas[1]}."
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
                f"End of configured search is reached, "
                f"search untill frame number {end_iter_frame_num}."
            )
            # if not full area found set to unknown
            if not mezzanine_found:
                qr_code_areas[0] = []
                logger.info(f"Mezzanine QR code areas not detected successfully.")
            if not test_status_found:
                logger.info(f"Test Runner QR code areas not detected successfully.")
            return first_pre_test_qr_time, qr_code_areas

    # if not full area found set to unknown
    logger.debug(f"End of recording is reached.")

    if not mezzanine_found:
        qr_code_areas[0] = []
        logger.debug(f"Mezzanine QR code areas not detected successfully.")
    if not test_status_found:
        logger.debug(f"Test Runner QR code areas not detected successfully.")
    return first_pre_test_qr_time, qr_code_areas


def get_qr_code_area(
    input_video_path_str: str,
    global_configurations: GlobalConfigurations,
    do_adaptive_threshold_scan: bool,
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
    logger.info(f"Search '{input_video_path_str}' to get QR code location...")

    qr_code_areas = [[], []]
    first_pre_test_qr_time = 0

    # default sart seach from 0s and finised at configuration from config.ini
    starting_point_s = 0
    search_qr_area_to = global_configurations.get_search_qr_area_to()
    # read user input range parameter
    qr_search_range = global_configurations.get_qr_search_range()

    input_video_path = Path(input_video_path_str).resolve()
    if not input_video_path.is_file():
        raise Exception(f"Recorded file '{input_video_path}' not found")

    vidcap = cv2.VideoCapture(input_video_path_str)
    fps: float = vidcap.get(cv2.CAP_PROP_FPS)
    width: int = int(vidcap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height: int = int(vidcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))/fps

    # if user input range parameter defined then update defaults
    if qr_search_range:
        starting_point_s = qr_search_range[1]
        qr_code_search_duration = qr_search_range[2]
        if starting_point_s > duration:
            raise ValueError("Starting point larger than recording duration.")
        search_qr_area_to = starting_point_s + qr_code_search_duration

    if fps < 1 or width <= 0 or height <= 0:
        vidcap.release()
        open(input_video_path_str, "rb")
        # File is readable but invalid.
        raise OSError(errno.EINVAL, "Video is invalid")

    if search_qr_area_to != 0:
        try:
            first_pre_test_qr_time, qr_code_areas = iter_to_get_qr_area(
                vidcap,
                fps,
                width,
                height,
                int(fps * search_qr_area_to),
                do_adaptive_threshold_scan,
                global_configurations,
                starting_point_s,
            )
        finally:
            vidcap.release()
    else:
        vidcap.release()

    """check qr_code_area
    if not defined we just crop left half for mezzanine
    right half for the test runner status
    """
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
                    f"QR code area for full scan is set to "
                    f"left half of image for mezzanine QR code."
                )
            else:
                # right half for test satus
                qr_code_areas[i] = [int(width / 2), 0, width, height]
                logger.info(
                    f"QR code area for full scan is set to "
                    f"right half of image for test status QR code."
                )

    pre_test_qr_code_area = [
    	int(width / 4), 0, int((width / 4) * 3), height
    ]

    return first_pre_test_qr_time, qr_code_areas, pre_test_qr_code_area


def run(
    input_video_files: List[str],
    log_manager: LogManager,
    global_configurations: GlobalConfigurations,
    do_adaptive_threshold_scan: bool,
):
    """Runs the observation framework, loads configuration from Test Runner
    and reads the recorded video file
    """
    observation_framework = None

    file_index = 0
    qr_search_range = global_configurations.get_qr_search_range()
    if qr_search_range:
        file_index  = qr_search_range[0]
    starting_camera_frame_number = 0

    logger.info(f"Device Observation Framework (V{VERSION}) analysis started!")
    if (global_configurations.get_system_mode()) == "debug":
        logger.info(
            f"Device Observation Framework is running in debug mode, "
            f'reads local configuration file from "configuration" folder '
            f"and will not post results back to the Test Runner."
        )
    if do_adaptive_threshold_scan:
        logger.info(f"Intensive QR code scanning with additional adaptiveThreshold.")

    (
        first_pre_test_qr_time,
        qr_code_areas,
        pre_test_qr_code_area,
    ) = get_qr_code_area(
        input_video_files[file_index], global_configurations, do_adaptive_threshold_scan
    )
    logger.info(
        f"QR code area for full scan is set to {qr_code_areas[0]} for mezzanine QR code, "
        f"and {qr_code_areas[1]} for test status QR code."
    )

    # add pre-test qr code area
    # this removes the first and last vertical quarter of image
    if global_configurations.get_enable_cropped_scan_for_pre_test_qr():
        qr_code_areas.append(pre_test_qr_code_area)
        logger.info(
            f"Additional QR code scan with roughly cropped area {qr_code_areas[2]} for pre-test QR code is enabled."
        )
    for i in range (0, len(input_video_files)):
        input_video_path_str = input_video_files[i]
        logger.info(f"Analysing '{input_video_path_str}'...")

        input_video_path = Path(input_video_path_str).resolve()
        if not input_video_path.is_file():
            raise Exception(f"Recorded file '{input_video_path}' not found")

        vidcap = cv2.VideoCapture(input_video_path_str)
        fps: float = vidcap.get(cv2.CAP_PROP_FPS)
        width: int = int(vidcap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height: int = int(vidcap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if input_video_files.index(input_video_path_str) == 0:
            vidcap.set(cv2.CAP_PROP_POS_MSEC, first_pre_test_qr_time)
            starting_camera_frame_number = int(first_pre_test_qr_time/1000 * fps)

        if fps < 1 or width <= 0 or height <= 0:
            vidcap.release()
            open(input_video_path_str, "rb")
            # File is readable but invalid.
            raise OSError(errno.EINVAL, "Video is invalid")

        try:
            if observation_framework is None:
                observation_framework = ObservationFrameworkProcessor(
                    log_manager, global_configurations, fps, do_adaptive_threshold_scan
                )

            observation_framework.extract_and_read_audio_data(input_video_path_str, i)

            last_camera_frame_number = observation_framework.iter_qr_codes_in_video(
                vidcap, starting_camera_frame_number, qr_code_areas
            )
            starting_camera_frame_number += last_camera_frame_number
        finally:
            vidcap.release()

    if observation_framework:
        for input_video_path_str in input_video_files:
            rename_input_file(
                input_video_path_str,
                input_video_path,
                observation_framework.pre_test_qr_code.session_token,
            )

    logger.info(f"Device Observation Framework analysis ended.")


def clear_path(file_path: str, session_log_threshold: int) -> None:
    """log path: list of session log files and event files
    result path: list of session folders contain result file
    if number of logs or results exceeded configured threshold
    delete some file to release the disk space
    """
    if os.path.isdir(file_path):
        full_path = [
            os.path.join(file_path, f)
            for f in os.listdir(file_path)
            if os.path.isdir(os.path.join(file_path, f))
        ]
        num_session = len(full_path)

        num_of_session_to_delete = num_session - session_log_threshold
        if num_of_session_to_delete > 0:
            oldest = sorted(full_path, key=os.path.getctime)[0:num_of_session_to_delete]
            logger.info(
                f"Removing oldest {num_of_session_to_delete} file(s): {oldest}!"
            )
            for oldest_session in oldest:
                shutil.rmtree(oldest_session)


def clear_up(global_configurations: GlobalConfigurations) -> None:
    """check log and result path to release the disk space
    global_configurations: to get threshold and path to clear
    """
    log_file_path = global_configurations.get_log_file_path()
    result_file_path = global_configurations.get_result_file_path()
    session_log_threshold = global_configurations.get_session_log_threshold()

    clear_path(log_file_path, session_log_threshold)
    clear_path(result_file_path, session_log_threshold)


def check_python_version() -> bool:
    """Check minimum Python version is being used.
    Returns:
        True if version is OK.
    """
    if sys.version_info.major == 3 and sys.version_info.minor >= 6:
        return True
    logger.error(
        "Aborting... Python version 3.6 or greater is required.\n"
        f"Current Python version is {sys.version_info.major}.{sys.version_info.minor}."
    )
    return False


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"DPCTF Device Observation Framework (v{VERSION})"
    )
    parser.add_argument("--input", help="Input Video Path")
    parser.add_argument(
        "--log",
        help="Logging level to write to log file.",
        default="info",
        choices=["debug", "info"],
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
    parser.add_argument("--ignore_corrupted", help="Specific condition to ignore.", default="")
    parser.add_argument(
        "--range",
        help="Search QR codes to crop the QR code area for better detection. QR codes area detection includes mezzanine QR codes and Test Status QR code.",
        default="",
        metavar="id(file_index):start(s):duration(s)",
    )
    args = parser.parse_args()
    do_adaptive_threshold_scan = False
    if args.scan == "intensive":
        do_adaptive_threshold_scan = True

    global_configurations = GlobalConfigurations()
    global_configurations.set_ignore_corrupted(args.ignore_corrupted)
    global_configurations.set_system_mode(args.mode)
    global_configurations.set_qr_search_range(args.range)
    log_file_path = global_configurations.get_log_file_path()

    log_file = log_file_path + "/events.log"
    log_manager = LogManager(log_file, args.log)

    if not check_python_version():
        sys.exit(1)

    input_video_files = []
    input_video_path = Path(args.input).resolve()

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
                logger.warning(f"{full_path} is not a file, skipped!")
    else:
        input_video_files.append(str(input_video_path))

    # sort input files based on the configuration
    sort_input_files_by = global_configurations.get_sort_input_files_by()
    if sort_input_files_by == "filename":
        sorted(input_video_files)
    else:
        input_video_files.sort(key=os.path.getmtime)

    try:
        run(
            input_video_files,
            log_manager,
            global_configurations,
            do_adaptive_threshold_scan,
        )
    except ObsFrameTerminate as e:
        logger.exception(
            f"Serious error is detected! {e} system is terminating!",
            exc_info=False,
        )
        clear_up(global_configurations)
        sys.exit(1)
    except ConfigError as e:
        logger.exception(
            f"Serious error is detected! {e}",
            exc_info=False,
        )
        clear_up(global_configurations)
        sys.exit(1)
    except Exception as e:
        logger.exception(
            f"Serious error is detected! {e}: {traceback.format_exc()}"
        )
        clear_up(global_configurations)
        sys.exit(1)

    logger.info(
        f"Device Observation Framework has finished analysing all selected recordings, "
        f"Device Observation Framework is exiting."
    )
    clear_up(global_configurations)


if __name__ == "__main__":
    main()
