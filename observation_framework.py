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
import os
import cv2
import errno
import logging
import traceback
import shutil
import sys

from typing import List
from pathlib import Path
from global_configurations import GlobalConfigurations
from observation_framework_processor import ObservationFrameworkProcessor
from exceptions import ObsFrameTerminate
from log_handler import LogManager

MAJOR = 1
MINOR = 0
PATCH = 0
VERSION = f"{MAJOR}.{MINOR}.{PATCH}"

logger = logging.getLogger(__name__)


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
            logger.info(f"Recorded file renamed to '{new_file_path}'.")


def run(
    input_video_files: List[str],
    log_manager: LogManager,
    global_configurations: GlobalConfigurations,
):
    """Runs the observation framework, loads configuration from Test Runner
    and reads the recorded video file
    """
    observation_framework = None
    starting_camera_frame_number = 0

    for input_video_path_str in input_video_files:
        logger.info(
            f"Device Observation Framework (v{VERSION}) analysing '{input_video_path_str}'..."
        )

        input_video_path = Path(input_video_path_str).resolve()
        if not input_video_path.is_file():
            raise Exception(f"Recorded file '{input_video_path}' not found")

        vidcap = cv2.VideoCapture(input_video_path_str)
        fps: float = vidcap.get(cv2.CAP_PROP_FPS)
        width: int = int(vidcap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height: int = int(vidcap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if fps < 1 or width <= 0 or height <= 0:
            vidcap.release()
            open(input_video_path_str, "rb")
            # File is readable but invalid.
            raise OSError(errno.EINVAL, "Video is invalid")

        try:
            if observation_framework is None:
                observation_framework = ObservationFrameworkProcessor(
                    log_manager, global_configurations, fps
                )

            last_camera_frame_number = observation_framework.iter_qr_codes_in_video(
                vidcap, starting_camera_frame_number
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


def clear_path(file_path: str, file_type: str, session_log_threshold: int) -> None:
    """log path: list of session log files and event files
    result path: list of session folders contain result file
    if number of logs or results exceeded configured threshold
    delete some file to release the disk space
    """
    if os.path.isdir(file_path):
        if file_type == "log":
            full_path = [
                os.path.join(file_path, f)
                for f in os.listdir(file_path)
                if os.path.isfile(os.path.join(file_path, f))
                and "events" not in os.path.join(file_path, f)
            ]
        else:
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
                if file_type == "log":
                    os.remove(oldest_session)
                else:
                    shutil.rmtree(oldest_session)


def clear_up(global_configurations: GlobalConfigurations) -> None:
    """check log and result path to release the disk space
    global_configurations: to get threshold and path to clear
    """
    log_file_path = global_configurations.get_log_file_path()
    result_file_path = global_configurations.get_result_file_path()
    session_log_threshold = global_configurations.get_session_log_threshold()

    clear_path(log_file_path, "log", session_log_threshold)
    clear_path(result_file_path, "result", session_log_threshold)


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
        default="debug",
        choices=["debug", "info"],
    )
    args = parser.parse_args()

    global_configurations = GlobalConfigurations()
    log_file_path = global_configurations.get_log_file_path()

    log_file = log_file_path + "/events.log"
    log_manager = LogManager(log_file, args.log)

    if not check_python_version():
        sys.exit(1)

    input_video_files = []
    input_video_path = Path(args.input).resolve()
    if input_video_path.is_dir():
        input_files = os.listdir(input_video_path)
        for input_file in input_files:
            full_path = os.path.join(input_video_path, input_file)
            if Path(full_path).resolve().is_file():
                input_video_files.append(full_path)
            else:
                logger.warning(f"{full_path} is not a file, skipped!")
    else:
        input_video_files.append(args.input)

    # sort input files based on the configuration
    sort_input_files_by = global_configurations.get_sort_input_files_by()
    if sort_input_files_by == "filename":
        sorted(input_video_files)
    else:
        input_video_files.sort(key=os.path.getmtime)

    try:
        run(input_video_files, log_manager, global_configurations)
    except ObsFrameTerminate as e:
        logger.exception(
            f"Serious error is detected, when analysing {input_video_files}! "
            f"{e}: {traceback.format_exc()} "
            f"system is terminating."
        )
        clear_up(global_configurations)
        sys.exit(1)
    except Exception as e:
        logger.exception(
            f"Serious error is detected, when analysing {input_video_files}! "
            f"{e}: {traceback.format_exc()}"
        )

    logger.info(
        f"Device Observation Framework has finished analysing all selected recordings, "
        f"Device Observation Framework is exiting."
    )
    clear_up(global_configurations)


if __name__ == "__main__":
    main()
