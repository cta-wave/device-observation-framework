# -*- coding: utf-8 -*-
"""WAVE DPCTF output file handler

Handle the output files, write data to files.

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
import csv
import logging
import os
from typing import List, Tuple

import matplotlib.pyplot as plt

from dpctf_audio_decoder import AudioSegment
from dpctf_qr_decoder import MezzanineDecodedQr, PreTestDecodedQr, TestStatusDecodedQr
from qr_recognition.qr_decoder import DecodedQr

logger = logging.getLogger(__name__)
logging.getLogger("matplotlib.font_manager").disabled = True


def write_header_to_csv_file(file_name: str, header: List[str]):
    """write header to a csv file"""
    # remove existing csv file, only keep the last result
    if os.path.exists(file_name):
        os.remove(file_name)

    with open(file_name, "a", encoding="utf-8") as file:
        file_writer = csv.writer(file)
        file_writer.writerow(header)
        file.close()


def write_data_to_csv_file(file_name: str, header: List[str], data: List[Tuple]):
    """export time differences to csv file"""
    # remove existing csv file, only keep the last result
    if os.path.exists(file_name):
        os.remove(file_name)

    with open(file_name, "a", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)

        for row_data in data:
            writer.writerow(row_data)


def extract_qr_data_to_csv(
    file_name: str, camera_frame_number: int, detected_qr_codes: List[DecodedQr]
) -> None:
    """Extract camera frame number and detected qr code data to a csv file"""
    if not file_name:
        return

    with open(file_name, "a", encoding="utf-8") as file:
        file_writer = csv.writer(file)

        for detected_code in detected_qr_codes:
            if isinstance(detected_code, MezzanineDecodedQr):
                file_writer.writerow(
                    [
                        camera_frame_number,
                        detected_code.content_id,
                        detected_code.media_time,
                        detected_code.frame_number,
                        detected_code.frame_rate,
                        detected_code.location,
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ]
                )
            elif isinstance(detected_code, TestStatusDecodedQr):
                file_writer.writerow(
                    [
                        camera_frame_number,
                        "",
                        "",
                        "",
                        "",
                        "",
                        detected_code.status,
                        detected_code.last_action,
                        detected_code.current_time,
                        detected_code.delay,
                        "",
                        "",
                    ]
                )
            elif isinstance(detected_code, PreTestDecodedQr):
                file_writer.writerow(
                    [
                        camera_frame_number,
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        detected_code.session_token,
                        detected_code.test_id,
                    ]
                )
            else:
                continue

        file.close()


def audio_data_to_csv(file_name: str, data: List[AudioSegment], parameters_dict: dict):
    """export audio segment data to csv file"""
    # remove existing csv file, only keep the last result
    if os.path.exists(file_name):
        os.remove(file_name)

    header = [
        "Content ID",
        "Duration",
        "Media Time",
        "Time in Recording",
        "Detected Time",
    ]
    with open(file_name, "a", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)

        for row_data in data:
            detected_time = (
                row_data.audio_segment_timing
                + parameters_dict["audio_starting_time"]
                - parameters_dict["offset"] / parameters_dict["sample_rate"]
            )
            writer.writerow(
                [
                    row_data.audio_content_id,
                    row_data.duration,
                    row_data.media_time,
                    row_data.audio_segment_timing,
                    detected_time,
                ]
            )

    # export to figure
    audio_segment_timings = []
    for audio_segment in data:
        audio_segment_timings.append(audio_segment.audio_segment_timing)

    plt.figure(0)
    plt.figure(figsize=(20, 15))
    plt.xlabel("Segment Number")
    plt.ylabel("Detected Position")
    plt.title("Detected Audio Segments")
    file_name = file_name.replace(".csv", ".png")
    plt.plot(audio_segment_timings)
    plt.savefig(file_name)
    plt.close()
