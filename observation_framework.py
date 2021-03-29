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
Licensor: Eurofins Digital Product Testing UK Limited
"""
import argparse
import sys
import os
import cv2
import errno
import logging
import traceback

from pathlib import Path
from global_configurations import GlobalConfigurations
from observation_framework_processor import ObservationFrameworkProcessor

MAJOR = 0
MINOR = 2
PATCH = 0
VERSION = f"{MAJOR}.{MINOR}.{PATCH}"


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
            logging.info(f"Recorded file renamed to '{new_file_path}'.")


def run(input_video_path_str: str, global_configurations: GlobalConfigurations):
    """Runs the observation framework, loads configuration from Test Runner
    and reads the recorded video file
    """
    logging.info(f"Device Observation Framework (v{VERSION}) analysing '{input_video_path_str}'...")

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
        observation_framework = ObservationFrameworkProcessor(
            global_configurations, fps
        )
        observation_framework.iter_qr_codes_in_video(vidcap)
    finally:
        vidcap.release()

    rename_input_file(
        input_video_path_str,
        input_video_path,
        observation_framework.pre_test_qr_code.session_token,
    )

    logging.info(f"Device Observation Framework analysis ended.")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description=f"DPCTF Device Observation Framework (v{VERSION})"
    )
    parser.add_argument("--input", help="Input Video Path")
    parser.add_argument("--log", help="Logging level to write to log file.", default="debug", choices=['debug', 'info'])
    args = parser.parse_args()

    global_configurations = GlobalConfigurations()
    from log_handler import create_logger

    create_logger(global_configurations.get_log_file(), args.log)

    try:
        run(args.input, global_configurations)
    except Exception as e:
        logging.exception(
            "Serious error is detected, Device Observation Framework is exiting!"
            f"{e}: {traceback.format_exc()}"
        )
        sys.exit(-1)


if __name__ == "__main__":
    main()
