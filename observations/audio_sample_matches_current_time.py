# -*- coding: utf-8 -*-
"""observation audio_sample_matches_current_time

make observation of audio_sample_matches_current_time

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
import sys
from typing import Dict, List, Tuple

from dpctf_audio_decoder import AudioSegment
from dpctf_qr_decoder import TestStatusDecodedQr
from output_file_handler import write_data_to_csv_file

from .observation import Observation

logger = logging.getLogger(__name__)

REPORT_NUM_OF_FAILURE = 50
CAMERA_FRAME_ADJUSTMENT = 0.5
"""a FIXED arbitrary value 1/2 according to the test set up
to account for the possibility that the QR code was
discernible between capture frames"""


class AudioSampleMatchesCurrentTime(Observation):
    """AudioSampleMatchesCurrentTime class
    The presented sample matches the one reported by the currentTime value within the tolerance of the sample duration.
    """

    def __init__(self, _, name: str = None):
        if name is None:
            name = (
                "[OF] Audio: The presented sample shall match the one reported by the currentTime value"
                " within the tolerance of the sample duration."
            )
        super().__init__(name)

    @staticmethod
    def _check_audio_diff_within_tolerance(
        audio_segments: List[AudioSegment],
        audio_sample_length: float,
        current_status: TestStatusDecodedQr,
        delay: int,
        camera_frame_duration_ms: float,
        test_start_time: float,
        allowed_tolerance: float,
        ct_sample_tolerance: float,
    ) -> Tuple[bool, float]:
        """check diff between reported status current time and audio sample time recorded jointly

        Args:
            audio_segments: Ordered list of audio segment found.
            audio_sample_length: audio sample duration in milliseconds defined in test-config.json.
            current_status (TestStatusDecodedQr): Test Status QR code containing currentTime as reported by MSE.
            delay (int): time taken to generate the status event QR code in milliseconds.
            camera_frame_duration_ms (float): duration of a camera frame on milliseconds.
            test_start_time: 1st pre-test qr code detection time in milliseconds.
            allowed_tolerance (float): Test-specific tolerance as specified in test-config.json.
            ct_sample_tolerance: OF tolerance of sample number configured in test-config.json.

        Returns:
            (bool, float): True if time difference passed, Actual time difference detected.
        """
        result = False
        time_diff = sys.float_info.max
        current_time_ms = current_status.current_time * 1000

        current_status_detected_time = (
            current_status.camera_frame_num * camera_frame_duration_ms - delay
        ) - test_start_time

        first_possible = (
            current_status_detected_time
            - CAMERA_FRAME_ADJUSTMENT * camera_frame_duration_ms
            - ct_sample_tolerance * audio_sample_length
        )
        last_possible = (
            current_status_detected_time
            + CAMERA_FRAME_ADJUSTMENT * camera_frame_duration_ms
            + ct_sample_tolerance * audio_sample_length
        )

        for i in range(0, len(audio_segments)):
            appear_from = (
                audio_segments[i].audio_segment_timing
                - CAMERA_FRAME_ADJUSTMENT * audio_sample_length
            )
            appear_till = (
                audio_segments[i].audio_segment_timing
                + CAMERA_FRAME_ADJUSTMENT * audio_sample_length
            )

            if first_possible > appear_till or last_possible < appear_from:
                pass
            else:
                new_time_diff = abs(audio_segments[i].media_time - current_time_ms)
                if new_time_diff < time_diff:
                    time_diff = new_time_diff

                if (
                    time_diff
                    <= allowed_tolerance + ct_sample_tolerance * audio_sample_length
                ):
                    result = True
                    break

        return result, time_diff

    def _check_sample_matches_current_time(
        self,
        audio_segments: List[AudioSegment],
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
    ) -> Tuple[int, list]:
        """returns the failure count and the time differences"""
        allowed_tolerance = parameters_dict["audio_tolerance"]
        ct_sample_tolerance = parameters_dict["audio_sample_tolerance"]
        audio_sample_length = parameters_dict["audio_sample_length"]
        test_start_time = parameters_dict["audio_test_start_time"]
        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]

        failure_report_count = 0
        time_differences = []

        first_current_time = None
        for i in range(0, len(test_status_qr_codes)):
            current_status = test_status_qr_codes[i]
            if i + 1 < len(test_status_qr_codes):
                if current_status.status == "playing" and (
                    current_status.last_action == "play"
                    or current_status.last_action == "representation_change"
                ):
                    if first_current_time == None:
                        first_current_time = current_status.current_time
                    # skip checks for starting ct report
                    if current_status.current_time == first_current_time:
                        continue

                    result, time_diff = self._check_audio_diff_within_tolerance(
                        audio_segments,
                        audio_sample_length,
                        current_status,
                        test_status_qr_codes[i + 1].delay,
                        camera_frame_duration_ms,
                        test_start_time,
                        allowed_tolerance,
                        ct_sample_tolerance,
                    )
                    # The multiplication happens so that we get the results in ms
                    time_differences.append(
                        (current_status.current_time * 1000, time_diff)
                    )

                    if not result:
                        self.result["status"] = "FAIL"
                        if failure_report_count == 0:
                            self.result["message"] += (
                                " Time difference between Test Runner reported media currentTime and actual media "
                                "time exceeded tolerance for following events:"
                            )

                        if failure_report_count < REPORT_NUM_OF_FAILURE:
                            self.result[
                                "message"
                            ] += f" currentTime={current_status.current_time} time_diff={round(time_diff, 4)}; "

                        failure_report_count += 1

        return failure_report_count, time_differences

    def make_observation(
        self,
        _test_type,
        _mezzanine_qr_codes,
        audio_segments: List[AudioSegment],
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
        observation_data_export_file: str,
    ) -> Tuple[Dict[str, str], list, list]:
        """make observation"""
        logger.info("Making observation %s.", self.result["name"])

        if not audio_segments:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = "No audio segment is detected."
            logger.info("[%s] %s", self.result["status"], self.result["message"])
            return self.result, [], []

        (
            failure_report_count,
            time_differences,
        ) = self._check_sample_matches_current_time(
            audio_segments, test_status_qr_codes, parameters_dict
        )

        if failure_report_count >= REPORT_NUM_OF_FAILURE:
            self.result["message"] += "...too many failures, reporting truncated."

        self.result["message"] += f" Total failure count is {failure_report_count}."

        if self.result["status"] != "FAIL":
            self.result["status"] = "PASS"

        # Exporting time diff data to a CSV file
        if observation_data_export_file and time_differences:
            write_data_to_csv_file(
                observation_data_export_file + "_audio_ct_diff.csv",
                ["Current Time", "Time Difference"],
                time_differences,
            )

        logger.debug("[%s] %s", self.result["status"], self.result["message"])
        return self.result, [], []
