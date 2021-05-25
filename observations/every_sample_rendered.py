# -*- coding: utf-8 -*-
"""observation every_sample_rendered

make observation of every_sample_rendered

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
import logging

from .observation import Observation
from typing import List, Dict
from dpctf_qr_decoder import MezzanineDecodedQr
from global_configurations import GlobalConfigurations
from exceptions import ObsFrameTerminate
from test_code.test import TestType

logger = logging.getLogger(__name__)


class EverySampleRendered(Observation):
    """EverySampleRendered class
    Every sample S[k,s] shall be rendered and the samples shall be rendered in increasing presentation time order.
    """

    missing_frame_count = 0
    """total missing frame count"""
    mid_missing_frame_count = 0
    """mid missing frame count not include frame missing at start and end and when contents switches"""

    def __init__(self, global_configurations: GlobalConfigurations, name: str = None):
        if name is None:
            name = (
                "[OF] Every sample S[k,s] shall be rendered and the samples shall be rendered in increasing "
                "presentation time order."
            )
        super().__init__(name, global_configurations)

    def _check_first_frame(
        self, first_frame_num: int, first_qr_code: MezzanineDecodedQr
    ) -> bool:
        """Check 1st expected frame is present,
        except a start_frame_num_tolerance of missing frames is allowed.

        Args:
            first_frame_num: expected frame number of the first frame
            first_qr_code: first MezzanineDecodedQr from MezzanineDecodedQr lists

        Returns:
            bool: True if the 1st is present.
        """
        result = True
        start_frame_num_tolerance = self.tolerances["start_frame_num_tolerance"]
        missing_first_frame = abs(first_qr_code.frame_number - first_frame_num)
        self.missing_frame_count += missing_first_frame
        if missing_first_frame > start_frame_num_tolerance:
            result = False

        self.result["message"] += (
            f" First frame found is {first_qr_code.frame_number}, "
            f"expected to start from {first_frame_num}."
            f" First frame number tolerance is {start_frame_num_tolerance}."
        )
        return result

    def _check_last_frame(
        self, last_frame_num: int, last_qr_code: MezzanineDecodedQr
    ) -> bool:
        """Check 1st expected frame is present,
        except an end_frame_num_tolerance of missing frames is allowed.

        Args:
            last_frame_num: expected frame number of the last frame
            last_qr_code: last  MezzanineDecodedQr from MezzanineDecodedQr lists

        Returns:
            bool: True if the last is present.
        """
        result = True
        end_frame_num_tolerance = self.tolerances["end_frame_num_tolerance"]
        missing_last_frame = abs(last_frame_num - last_qr_code.frame_number)
        self.missing_frame_count += missing_last_frame
        if missing_last_frame > end_frame_num_tolerance:
            result = False

        self.result["message"] += (
            f" Last frame found is {last_qr_code.frame_number}, "
            f"expected to end at {last_frame_num}."
            f" Last frame number tolerance is {end_frame_num_tolerance}."
        )
        return result

    def _check_every_frame(self, mezzanine_qr_codes: List[MezzanineDecodedQr]) -> bool:
        """Check all intervening frames. All frames must be present and in ascending order,
        except a mid_frame_num_tolerance of missing frames is allowed.

        Args:
            mezzanine_qr_codes: lists of MezzanineDecodedQr

        Returns:
            bool: True if all the mid frames are present
        """
        check = True
        mid_frame_num_tolerance = self.tolerances["mid_frame_num_tolerance"]

        # add tolerance to result message only once
        if "Mid frame number tolerance" not in self.result["message"]:
            self.result[
                "message"
            ] += f" Mid frame number tolerance is {mid_frame_num_tolerance}."

        for i in range(1, len(mezzanine_qr_codes)):
            if (
                mezzanine_qr_codes[i - 1].frame_number + 1
                != mezzanine_qr_codes[i].frame_number
            ):
                check = False
                previous_frame = mezzanine_qr_codes[i - 1].frame_number
                current_frame = mezzanine_qr_codes[i].frame_number
                for frame in range(previous_frame, current_frame - 1):
                    if (
                        self.missing_frame_threshold == 0
                        or self.missing_frame_count <= self.missing_frame_threshold
                    ):
                        self.result["message"] += f" Frame {frame + 1} is missing."
                self.mid_missing_frame_count += current_frame - previous_frame - 1
                self.missing_frame_count += current_frame - previous_frame - 1

        if (
            self.missing_frame_threshold != 0
            and self.missing_frame_count > self.missing_frame_threshold
        ):
            """if the missing frame exceeded the threshold
            send error to the test runner, display error on the console
            and end the observation framework
            the following tests will not be observed.
            """
            self.result["message"] += (
                f"... too many missing frames, reporting truncated. "
                f"Total of missing frames is {self.missing_frame_count}. "
                f"Device Observation Framework is exiting, and the following tests are not observed."
            )
            raise ObsFrameTerminate(self.result["message"])

        if self.mid_missing_frame_count <= mid_frame_num_tolerance:
            check = True

        return check

    def observe_switching_mid_frame(
        self,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        playout: List[int],
        fragment_duration: float,
    ) -> bool:
        """observe switching set tests
        playback more than one representations

        Parse playout parameter to a list of switching point in media timeline
        switching_times: a list of switching point in media timeline

        check every switching points starting frame and ending frame
        check that the samples shall be rendered in increasing order within the same repersentations
        for QRb to QRn: QR[i-1].mezzanine_frame_num + 1 == QR[i].mezzanine_frame_num
        """
        switching_times = []
        switching_point = 0
        switching_times.append(switching_point)
        for i in range(1, len(playout)):
            switching_point += fragment_duration
            if playout[i] != playout[i - 1]:
                switching_times.append(switching_point)

        current_content_id = mezzanine_qr_codes[0].content_id
        change_switching_index_list = [0]
        for i in range(1, len(mezzanine_qr_codes)):
            if mezzanine_qr_codes[i].content_id != current_content_id:
                # the content did change
                change_switching_index_list.append(i)
                current_content_id = mezzanine_qr_codes[i].content_id

        # check configuration and actual switching matches and validate configuration
        configured_switching_num = len(switching_times)
        actual_switching_num = len(change_switching_index_list)
        if actual_switching_num != configured_switching_num:
            self.result["message"] += (
                f" Number of switches does not match. "
                f"Test is configured to switch {configured_switching_num} times. "
                f"Actual number of switches is {actual_switching_num}. "
            )
            return False

        if configured_switching_num == 1:
            self.result["message"] += (
                f" Switching test configuration is not correct on Test Runner. "
                f"The switching test should switch at least once. "
            )
            return False

        # check mid frames block by block
        mid_frame_result = True
        for i, staring_index in enumerate(change_switching_index_list):
            if staring_index == change_switching_index_list[-1]:
                # check mid frames for last block
                mid_frame_result = mid_frame_result and self._check_every_frame(
                    mezzanine_qr_codes[change_switching_index_list[-1]:]
                )
            else:
                last_index = change_switching_index_list[i + 1] - 1
                mid_frame_result = mid_frame_result and self._check_every_frame(
                    mezzanine_qr_codes[staring_index:last_index]
                )

            if i > 0:
                # check previous ending frame and new starting frame numbers
                # the expected frame number position in the content being switched from is the expected relative time
                # of the switch (derived from the test config) * that content's frames per second
                previous_ending_frame_num = (
                    round(
                        switching_times[i]
                        / 1000
                        * mezzanine_qr_codes[staring_index - 1].frame_rate
                    )
                    - 1
                )

                # compare expected with the actual frame number detected at this switch point
                diff_ending_frame = abs(
                    mezzanine_qr_codes[staring_index - 1].frame_number
                    - previous_ending_frame_num
                )
                if diff_ending_frame != 0:
                    mid_frame_result = False
                    self.result["message"] += (
                        f" Ending with incorrect frame when switching at switch number {i}. "
                        f"Ending frame found is {mezzanine_qr_codes[staring_index - 1].frame_number }, "
                        f"expected to end with {previous_ending_frame_num}."
                    )

                # the expected frame number position in the content being switched to is the expected relative time
                # of the switch (derived from the test config) * that content's frames per second
                # compare expected with the actual frame number detected at this switch point
                current_starting_frame_num = round(
                    switching_times[i]
                    / 1000
                    * mezzanine_qr_codes[staring_index].frame_rate
                )
                diff_starting_frame = abs(
                    mezzanine_qr_codes[staring_index].frame_number
                    - current_starting_frame_num
                )
                if diff_starting_frame != 0:
                    mid_frame_result = False
                    self.result["message"] += (
                        f" Starting from incorrect frame when switching at switch number {i + 1}. "
                        f"Starting frame found is {mezzanine_qr_codes[staring_index].frame_number }, "
                        f"expected to start from {current_starting_frame_num}."
                    )

        return mid_frame_result

    def observe_splicing_mid_frame(
        self, mezzanine_qr_codes: List[MezzanineDecodedQr], period_duration: List[float]
    ) -> bool:
        """splicing set tests has 2 or 3 playback periods
        3 perids: main content - ad insertion - main content
        2 perids: main content - ad insertion

        on each splicing point:
            check previos ending and new starting frames are correct for each periods
            check that the samples shall be rendered in increasing order within the same period
            for QRb to QRn: QR[i-1].mezzanine_frame_num + 1 == QR[i].mezzanine_frame_num
        """
        current_content_id = mezzanine_qr_codes[0].content_id
        period_staring_index_list = [0]
        for i in range(1, len(mezzanine_qr_codes)):
            if mezzanine_qr_codes[i].content_id != current_content_id:
                # the content did change
                period_staring_index_list.append(i)
                current_content_id = mezzanine_qr_codes[i].content_id

        configured_splicing_num = len(period_duration)
        actual_splicing_num = len(period_staring_index_list)
        if actual_splicing_num != configured_splicing_num:
            self.result["message"] += (
                f" Number of splices does not match. "
                f"Test is configured to splice {configured_splicing_num} times. "
                f"Actual number of splices is {actual_splicing_num}. "
            )
            return False

        if configured_splicing_num != 3 and configured_splicing_num != 2:
            self.result["message"] += (
                f" Number of splices is incorrect. "
                f"The splicing test should splice 2 or 3 times. "
                f"but the configured number of splices is {configured_splicing_num}. "
            )
            return False

        splice_start_frame_num_tolerance = self.tolerances[
            "splice_start_frame_num_tolerance"
        ]
        splice_end_frame_num_tolerance = self.tolerances[
            "splice_end_frame_num_tolerance"
        ]
        # check mid frames block by block
        mid_frame_result = True
        for i, starting_index in enumerate(period_staring_index_list):
            if starting_index == period_staring_index_list[-1]:
                # check mid frames for last block
                mid_frame_result = mid_frame_result and self._check_every_frame(
                    mezzanine_qr_codes[period_staring_index_list[-1]:]
                )
            else:
                last_index = period_staring_index_list[i + 1] - 1
                mid_frame_result = mid_frame_result and self._check_every_frame(
                    mezzanine_qr_codes[starting_index:last_index]
                )

            if i > 0:
                # check previous ending frame and new starting frame numbers
                # the expected frame number position in the content being switched from is the expected relative time
                # of the switch (derived from the test config) * that content's frames per second
                previous_ending_frame_num = (
                    round(
                        period_duration[i]
                        / 1000
                        * mezzanine_qr_codes[starting_index - 1].frame_rate
                    )
                    - 1
                )

                # compare expected with the actual frame number detected at this splice point
                diff_ending_frame = abs(
                    mezzanine_qr_codes[starting_index - 1].frame_number
                    - previous_ending_frame_num
                )

                if diff_ending_frame > splice_end_frame_num_tolerance:
                    mid_frame_result = False
                    self.result["message"] += (
                        f" Ending with incorrect frame when splicing at period number {i}. "
                        f"Ending frame found is {mezzanine_qr_codes[starting_index -1].frame_number }, "
                        f"expected to end with {previous_ending_frame_num}. "
                        f"Splice end frame tolerance is {splice_end_frame_num_tolerance}."
                    )

                if i == 2:
                    # if splice back to the main content start from where it left off
                    current_starting_frame_num = round(
                        period_duration[0]
                        / 1000
                        * mezzanine_qr_codes[starting_index].frame_rate
                    )
                else:
                    current_starting_frame_num = 1

                # compare expected with the actual frame number detected at this splice point
                diff_starting_frame = abs(
                    mezzanine_qr_codes[starting_index].frame_number
                    - current_starting_frame_num
                )
                if diff_starting_frame > splice_start_frame_num_tolerance:
                    mid_frame_result = False
                    self.result["message"] += (
                        f" Starting from incorrect frame when splicing at period number {i + 1}. "
                        f"Starting frame found is {mezzanine_qr_codes[starting_index].frame_number }, "
                        f"expected to start from {current_starting_frame_num}. "
                        f"Splice start frame tolerance is {splice_start_frame_num_tolerance}."
                    )

        return mid_frame_result

    def make_observation(
        self,
        test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        _unused,
        parameters_dict: dict,
    ) -> Dict[str, str]:
        """
        make_observation for different test type

        check 1st frame is present
        QRa.mezzanine_frame_num == first_frame_num

        check the last frame is present
        QRn.mezzanine_frame_num == round(cmaf_track_duration * mezzanine_frame_rate)

        Args:
            test_type: SWITCHING|SPLICING|SEQUENTIAL
            mezzanine_qr_codes: lists of MezzanineDecodedQr
            _unused:
            parameters_dict: parameter dictionary

        Returns:
            Dict[str, str]: observation result
        """
        logger.info(f"Making observation {self.result['name']}...")

        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "FAIL"
            self.result[
                "message"
            ] = f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result

        first_frame_result = self._check_first_frame(
            parameters_dict["first_frame_num"], mezzanine_qr_codes[0]
        )
        last_frame_result = self._check_last_frame(
            parameters_dict["last_frame_num"], mezzanine_qr_codes[-1]
        )

        if test_type == TestType.SWITCHING:
            mid_frame_result = self.observe_switching_mid_frame(
                mezzanine_qr_codes,
                parameters_dict["playout"],
                parameters_dict["fragment_duration"],
            )
        elif test_type == TestType.SPLICING:
            mid_frame_result = self.observe_splicing_mid_frame(
                mezzanine_qr_codes, parameters_dict["period_duration"]
            )
        else:
            # check that the samples shall be rendered in increasing order:
            # for QRb to QRn: QR[i-1].mezzanine_frame_num + 1 == QR[i].mezzanine_frame_num
            mid_frame_result = self._check_every_frame(mezzanine_qr_codes)

        if first_frame_result and last_frame_result and mid_frame_result:
            self.result["status"] = "PASS"
        else:
            self.result["status"] = "FAIL"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")
        return self.result
