# -*- coding: utf-8 -*-
"""observation sample_matches_current_time

make observation of sample_matches_current_time

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
import csv
import logging
import sys
from typing import Dict, List, Tuple

from configuration_parser import PlayoutParser
from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr
from test_code.test import TestType

from .observation import Observation

logger = logging.getLogger(__name__)

REPORT_NUM_OF_FAILURE = 50
CAMERA_FRAME_ADJUSTMENT = 0.5
"""a FIXED arbitrary value 1/2 according to the test set up
to account for the possibility that the QR code was
discernible between capture frames"""


class SampleMatchesCurrentTime(Observation):
    """SampleMatchesCurrentTime class
    The presented sample matches the one reported by the currentTime value within the tolerance of the sample duration.
    """

    def __init__(self, _, name: str = None):
        if name is None:
            name = (
                "[OF] The presented sample matches the one reported by the currentTime value within the "
                "tolerance of the sample duration."
            )
        super().__init__(name)

    @staticmethod
    def _get_target_camera_frame_num(
        camera_frame_num: int,
        delay: int,
        camera_frame_duration_ms: float,
        camera_frame_rate: float,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        ct_frame_tolerance: int,
    ) -> (Tuple[float, float]):
        """Calculate expected target camera frame numbers of the current time event
        by compensating for the delay in the QR code generation and applying tolerances.
        sample_tolerance_in_recording = 1000/mezzanine_frame_rate/(1000/camera_frame_rate)
            = camera_frame_rate/mezzanine_frame_rate

        Args:
            camera_frame_num (int): camera frame on which the status event QR code was first seen.
            delay (int): time taken to generate the status event QR code in msecs.
            camera_frame_duration_ms (float): duration of a camera frame on msecs.
            camera_frame_rate: recording frame rate
            mezzanine_qr_codes (List[MezzanineDecodedQr]): Ordered list of unique mezzanine QR codes found.
            ct_frame_tolerance(int): OF tolerance of frame number configured in config.ini

        Returns:
            First and last possible camera frame numbers which we expect may match the status event QR currentTime.
        """
        target_camera_frame_num = camera_frame_num - delay / camera_frame_duration_ms

        mezzanine_frame_rate = mezzanine_qr_codes[0].frame_rate
        for i in range(0, len(mezzanine_qr_codes)):
            if mezzanine_qr_codes[i].first_camera_frame_num > target_camera_frame_num:
                mezzanine_frame_rate = mezzanine_qr_codes[i - 1].frame_rate
                break

        sample_tolerance_in_recording = (
            ct_frame_tolerance * camera_frame_rate / mezzanine_frame_rate
        )
        first_possible = (
            target_camera_frame_num
            - CAMERA_FRAME_ADJUSTMENT
            - sample_tolerance_in_recording
        )
        last_possible = (
            target_camera_frame_num
            + CAMERA_FRAME_ADJUSTMENT
            + sample_tolerance_in_recording
        )

        return first_possible, last_possible

    @staticmethod
    def _find_diff_within_tolerance(
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        current_status: TestStatusDecodedQr,
        first_possible: float,
        last_possible: float,
        allowed_tolerance: float,
        ct_frame_tolerance: int,
    ) -> (Tuple[bool, float]):
        """Applies the logic:
        for first_possible_camera_frame_num_of_target to last_possible_camera_frame_num_of_target
            foreach mezzanine_qr_code on camera_frame
                if mezzanine_qr_code.media_time == (ct_event.current_time +/- sample_tolerance)
                    test is PASSED

        Args:
            mezzanine_qr_codes (List[MezzanineDecodedQr]): Ordered list of unique mezzanine QR codes found.
            current_status (TestStatusDecodedQr): Test Status QR code containing currentTime as reported by MSE.
            first_possible (float): First point (as fractional camera frame number) that could contain currentTime.
            last_possible (float): Last point (as fractional camera frame number) that could contain currentTime.
            allowed_tolerance (float): Test-specific tolerance as specified in test-config.json.
            ct_frame_tolerance(int): OF tolerance of frame number configured in config.ini.

        Returns:
            (bool, float): True if time difference passed, Actual time difference detected.
        """
        diff_found = False
        time_diff = sys.float_info.max
        current_time_ms = current_status.current_time * 1000

        for code in mezzanine_qr_codes:
            appear_from = code.first_camera_frame_num - CAMERA_FRAME_ADJUSTMENT
            appear_till = code.last_camera_frame_num + CAMERA_FRAME_ADJUSTMENT

            if first_possible > appear_till or last_possible < appear_from:
                pass
            else:
                new_time_diff = abs(code.media_time - current_time_ms)
                if new_time_diff < time_diff:
                    time_diff = new_time_diff

                if (
                    time_diff
                    <= allowed_tolerance + ct_frame_tolerance * 1000 / code.frame_rate
                ):
                    diff_found = True
                    break

        return diff_found, time_diff

    @staticmethod
    def _write_time_differences(
        time_diff_file: str, time_differences: List[Tuple[int, int]]
    ):
        """export time differences to csv file"""
        logger.debug(f"Exporting time differences to csv file {time_diff_file}...")

        with open(time_diff_file, "a") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Current Time", "Time Difference"])

            for pairs in time_differences:
                writer.writerow([pairs[0], round(pairs[1], 4)])

    def make_observation(
        self,
        test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
        time_diff_file: str,
    ) -> Dict[str, str]:
        """Implements the logic:
        sample_tolerance_in_recording = ct_frame_tolerance * 1000/mezzanine_frame_rate/(1000/camera_frame_rate)
            = ct_frame_tolerance * camera_frame_rate/mezzanine_frame_rate
        sample_tolerance = ct_frame_tolerance * 1000/mezzanine_frame_rate

        target_camera_frame_num_of_ct_event
            = ct_event.first_seen_camera_frame_num - (ct_event.d / camera_frame_duration_ms)
        first_possible_camera_frame_num_of_target
            = target_camera_frame_num_of_ct_event - CAMERA_FRAME_ADJUSTMENT - sample_tolerance_in_recording
        last_possible_camera_frame_num_of_target
            = target_camera_frame_num_of_ct_event + CAMERA_FRAME_ADJUSTMENT  + sample_tolerance_in_recording

        for first_possible_camera_frame_num_of_target to last_possible_camera_frame_num_of_target
                foreach mezzanine_qr_code on camera_frame that within the range
                        if mezzanine_qr_code.media_time == (ct_event.current_time +/- (sample_tolerance + tolerance))
                                test is PASSED
        """
        logger.info(f"Making observation {self.result['name']}...")

        if not mezzanine_qr_codes:
            self.result["status"] = "FAIL"
            self.result["message"] = f"No QR mezzanine code detected."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result

        camera_frame_rate = parameters_dict["camera_frame_rate"]
        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]
        allowed_tolerance = parameters_dict["tolerance"]
        ct_frame_tolerance = parameters_dict["frame_tolerance"]
        failure_report_count = 0
        self.result[
            "message"
        ] += (
            f" Allowed tolerance is {ct_frame_tolerance} frames, {allowed_tolerance}ms."
        )

        # for splicing test adjust media time in mezzanine_qr_codes
        # media time for period 2 starts from 0 so the actual media time is += period_duration[0]
        # media time for period 3 starts from where it was left but need to add the ad insertion duration
        # so the actual media time is += period_duration[1]
        if test_type == TestType.SPLICING:
            period_list = PlayoutParser.get_splicing_period_list(
                parameters_dict["playout"],
                parameters_dict["fragment_duration_multi_mpd"],
            )
            change_type_list = PlayoutParser.get_change_type_list(
                parameters_dict["playout"]
            )

            period_index = 0
            change_count = 0
            current_content_id = mezzanine_qr_codes[0].content_id
            current_frame_rate = mezzanine_qr_codes[0].frame_rate
            for i in range(1, len(mezzanine_qr_codes)):
                if (
                    mezzanine_qr_codes[i].content_id != current_content_id
                    or mezzanine_qr_codes[i].frame_rate != current_frame_rate
                ):
                    # the content did change
                    change_count += 1
                    current_content_id = mezzanine_qr_codes[i].content_id
                    current_frame_rate = mezzanine_qr_codes[i].frame_rate

                    if change_type_list[change_count - 1] == "splicing":
                        period_index += 1

                if period_index > 0:
                    mezzanine_qr_codes[i].media_time += period_list[period_index - 1]

        time_differences = []

        for i in range(0, len(test_status_qr_codes)):
            current_status = test_status_qr_codes[i]
            if i + 1 < len(test_status_qr_codes):
                if (
                    current_status.status == "playing"
                    and current_status.last_action == "play"
                ):
                    if "render_threshold" in parameters_dict:
                        # skip the ct=0.0 check for low_latency_initialization test
                        # 1st frame wont be rendered until chunk is appended
                        if current_status.current_time == 0.0:
                            continue
                    first_possible, last_possible = self._get_target_camera_frame_num(
                        current_status.camera_frame_num,
                        test_status_qr_codes[i + 1].delay,
                        camera_frame_duration_ms,
                        camera_frame_rate,
                        mezzanine_qr_codes,
                        ct_frame_tolerance,
                    )
                    diff_found, time_diff = self._find_diff_within_tolerance(
                        mezzanine_qr_codes,
                        current_status,
                        first_possible,
                        last_possible,
                        allowed_tolerance,
                        ct_frame_tolerance,
                    )
                    # The multiplication happens so that we get the results in ms
                    time_differences.append(
                        (current_status.current_time * 1000, time_diff)
                    )

                    if not diff_found:
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

        if failure_report_count >= REPORT_NUM_OF_FAILURE:
            self.result[
                "message"
            ] += f"...too many failures, reporting truncated. Total failure count is {failure_report_count}. "

        if self.result["status"] != "FAIL":
            self.result["status"] = "PASS"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")

        # Exporting time diff data to a CSV file
        if time_diff_file and time_differences:
            self._write_time_differences(time_diff_file, time_differences)

        return self.result
