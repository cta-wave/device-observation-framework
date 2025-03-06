# -*- coding: utf-8 -*-
# pylint: disable=import-error, disable=consider-using-enumerate
"""observation base class

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
import logging
from typing import Dict, List, Tuple

from dpctf_audio_decoder import AudioSegment
from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr
from global_configurations import GlobalConfigurations


class Observation:
    """Observation base class"""

    result: Dict[str, str]
    """observation result
    status: NOT_RUN | PASS | FAIL
    message: observation message this will be displayed on test runner
    name: description of the observation
    """
    tolerances: Dict[str, int]
    """tolerances of the observation
    this is configured in CONFIG.INI file
    """
    missing_frame_threshold: int
    """Threshold of missing frame.
    If the number of missing frames on an individual test is greater than this
    post error message and terminate the session.
    """
    global_configurations: GlobalConfigurations
    """global configuration object to get some OF configuration from"""

    logger: logging.Logger
    """logger"""

    def __init__(self, name: str, global_configurations: GlobalConfigurations):
        self.logger = global_configurations.get_logger()
        self.result = {
            "status": "NOT_RUN",
            "message": "",
            "name": name,
        }
        self.global_configurations = global_configurations

        if global_configurations is None:
            self.tolerances = {}
            self.missing_frame_threshold = 0
        else:
            self.tolerances = global_configurations.get_tolerances()
            self.missing_frame_threshold = (
                global_configurations.get_missing_frame_threshold()
            )

    @staticmethod
    def find_event(
        event: str,
        test_status_qr_codes: List[TestStatusDecodedQr],
        camera_frame_duration_ms: float,
    ) -> Tuple[bool, float]:
        """loop through event qr code to find 1st event

        Args:
            event: 1st event string to find
            test_status_qr_codes (List[TestStatusDecodedQr]): Test Status QR codes list containing
                currentTime as reported by MSE.
            camera_frame_duration_ms (float): duration of a camera frame on milliseconds.

        Returns:
            (bool, float): True if the 1st event is found,
            play_current_time from the 1st test runner event.
        """
        for i in range(0, len(test_status_qr_codes)):
            current_status = test_status_qr_codes[i]

            # check for the 1st play action from TR events
            if current_status.last_action == event:
                play_event_camera_frame_num = current_status.camera_frame_num

                if i + 1 < len(test_status_qr_codes):
                    next_status = test_status_qr_codes[i + 1]
                    previous_qr_generation_delay = next_status.delay
                    play_current_time = (
                        play_event_camera_frame_num * camera_frame_duration_ms
                    ) - previous_qr_generation_delay
                    return True, play_current_time
                break

        return False, 0

    @staticmethod
    def get_playback_change_position(
        mezzanine_qr_codes: List[MezzanineDecodedQr],
    ) -> List[int]:
        """loop through the detected mezzanine list to save
        playback change positions including content change
        and playback switching
        """
        current_content_id = mezzanine_qr_codes[0].content_id
        current_frame_rate = mezzanine_qr_codes[0].frame_rate
        change_starting_index_list = [0]
        for i in range(1, len(mezzanine_qr_codes)):
            if (
                mezzanine_qr_codes[i].content_id != current_content_id
                or mezzanine_qr_codes[i].frame_rate != current_frame_rate
            ):
                # the content did change save the starting index
                change_starting_index_list.append(i)
                current_content_id = mezzanine_qr_codes[i].content_id
                current_frame_rate = mezzanine_qr_codes[i].frame_rate
        return change_starting_index_list

    @staticmethod
    def get_content_change_position(
        mezzanine_qr_codes: List[MezzanineDecodedQr],
    ) -> List[int]:
        """loop through the detected mezzanine list to save
        content ID change positions
        """
        current_content_id = mezzanine_qr_codes[0].content_id
        change_starting_index_list = [0]
        for i in range(1, len(mezzanine_qr_codes)):
            if mezzanine_qr_codes[i].content_id != current_content_id:
                # the content did change save the starting index
                change_starting_index_list.append(i)
                current_content_id = mezzanine_qr_codes[i].content_id
        return change_starting_index_list

    @staticmethod
    def get_audio_segments_chunk(
        audio_segments: List[AudioSegment],
    ) -> List[List[AudioSegment]]:
        """
        loop through the audio segment to split
        audio segment into chunks with same audio content ID
        """
        current_content_id = audio_segments[0].audio_content_id
        audio_segments_chunk_list = []
        start = 0
        for i in range(1, len(audio_segments)):
            if audio_segments[i].audio_content_id != current_content_id:
                # the content did change save the chunk
                end = i
                audio_segments_chunk_list.append(audio_segments[start:end])
                current_content_id = audio_segments[i].audio_content_id
                start = i + 1
        audio_segments_chunk_list.append(audio_segments[start:])
        return audio_segments_chunk_list
