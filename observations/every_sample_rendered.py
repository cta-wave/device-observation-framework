# -*- coding: utf-8 -*-
# pylint: disable=import-error
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
Contributor: Resillion UK Limited
"""
import logging
import math
from typing import Dict, List, Optional, Tuple

from configuration_parser import PlayoutParser
from dpctf_qr_decoder import MezzanineDecodedQr
from exceptions import ObsFrameTerminate
from global_configurations import GlobalConfigurations
from test_code.test import TestType

from .observation import Observation

logger = logging.getLogger(__name__)


class EverySampleRendered(Observation):
    """EverySampleRendered class
    Every sample S[k,s] shall be rendered and the samples shall be rendered
    in increasing presentation time order.
    """

    missing_frame_count: int
    """total missing frame count"""
    mid_missing_frame_count: int
    """mid missing frame count not include frame missing at start and end and
    when contents switches"""
    mid_missing_frame_duration: list
    """sum of all mid missing frame duration for
    presentation one and presentation two"""

    def __init__(self, global_configurations: GlobalConfigurations, name: str = None):
        if name is None:
            name = (
                "[OF] Every video frame S[k,s] shall be rendered and the video frames "
                "shall be rendered in increasing presentation time order."
            )
        super().__init__(name, global_configurations)
        self.missing_frame_count = 0
        self.mid_missing_frame_count = 0
        self.mid_missing_frame_duration = [0, 0]

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

        # print when there is any missing frame (even within the tolerance, which would pass)
        if missing_first_frame != 0:
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

        # print when there is any missing frame (even within the tolerance, which would pass)
        if missing_last_frame != 0:
            self.result["message"] += (
                f" Last frame found is {last_qr_code.frame_number}, "
                f"expected to end at {last_frame_num}."
                f" Last frame number tolerance is {end_frame_num_tolerance}."
            )
        return result

    def _check_every_frame(
        self,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        playout_no: Optional[int] = None,
        presentation_id: int = 1,
    ) -> bool:
        """Check all intervening frames. All frames must be present and in ascending order,
        except a mid_frame_num_tolerance of missing frames is allowed.

        Args:
            mezzanine_qr_codes: lists of MezzanineDecodedQr

        Returns:
            bool: True if all the mid frames are present
        """
        check = True
        mid_frame_num_tolerance = self.tolerances["mid_frame_num_tolerance"]
        missing_frames = []
        out_of_order_frames = []

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

                if (
                    self.missing_frame_threshold == 0
                    or self.missing_frame_count <= self.missing_frame_threshold
                ):
                    if previous_frame > current_frame:
                        self.result["message"] += (
                            f" Frames out of order {previous_frame}, {current_frame}"
                            f"{' in playout ' + str(playout_no) if playout_no else ''}."
                        )
                        out_of_order_frames.append(previous_frame)
                        out_of_order_frames.append(current_frame)
                    else:
                        for frame in range(previous_frame, current_frame - 1):
                            missing_frames.append(frame + 1)

        for out_of_order_frame in out_of_order_frames:
            if out_of_order_frame in missing_frames:
                missing_frames.remove(out_of_order_frame)

        self.mid_missing_frame_count += len(missing_frames)
        if missing_frames and len(mezzanine_qr_codes) > 0:
            missing_frame_duration = (
                len(missing_frames) * 1000 / mezzanine_qr_codes[0].frame_rate
            )
            if presentation_id == 1:
                self.mid_missing_frame_duration[0] += missing_frame_duration
            else:
                self.mid_missing_frame_duration[1] += missing_frame_duration
        self.missing_frame_count += len(missing_frames)

        if missing_frames:
            self.result[
                "message"
            ] += f" Following frames are missing{' in playout ' + str(playout_no) if playout_no else ''}:"
            print_range = len(missing_frames)
            if (
                self.missing_frame_threshold != 0
                and print_range > self.missing_frame_threshold
            ):
                print_range = self.missing_frame_threshold
            for i in range(print_range):
                self.result["message"] += f" {missing_frames[i]}"

        if (
            self.missing_frame_threshold != 0
            and self.missing_frame_count > self.missing_frame_threshold
        ):
            # if the missing frame exceeded the threshold
            # send error to the test runner, display error on the console and
            # end the observation framework the following tests will not be observed.
            self.result["message"] += (
                f"... too many missing frames, reporting truncated. "
                f"Total of missing frames "
                f"in {'playout ' + str(playout_no) if playout_no else ''} "
                f"is {self.missing_frame_count}. "
                f"Device Observation Framework is exiting, "
                f"and the following tests are not observed."
            )
            raise ObsFrameTerminate(self.result["message"])

        # missing frame within the tolerance
        if self.mid_missing_frame_count <= mid_frame_num_tolerance:
            check = True

        return check

    def check_every_frame_by_block(
        self,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        change_index_list: List[int],
        playout_sequence: List[int],
        presentation_id: int = 1,
    ) -> bool:
        """check mid frames for block by block
        each block is different track
        """
        mid_frame_result = True
        for i, starting_index in enumerate(change_index_list):
            if starting_index == change_index_list[-1]:
                # check mid frames for last block
                mid_frame_result = mid_frame_result and self._check_every_frame(
                    mezzanine_qr_codes[change_index_list[-1] :],
                    playout_sequence[-1],
                    presentation_id,
                )
            else:
                last_index = change_index_list[i + 1] - 1
                mid_frame_result = mid_frame_result and self._check_every_frame(
                    mezzanine_qr_codes[starting_index:last_index],
                    playout_sequence[i],
                    presentation_id,
                )

        return mid_frame_result

    def observe_switching_mid_frame(
        self,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        playout: list,
        fragment_duration_multi_reps: Dict[int, list],
    ) -> bool:
        """observe switching set tests
        playback more than one representations

        Parse playout parameter to a list of switching point in media timeline
        switching_positions: a list of switching position in media timeline

        check every switching points starting frame and ending frame
        check that the samples shall be rendered in increasing order within the same representations
        for QRb to QRn: QR[i-1].mezzanine_frame_num + 1 == QR[i].mezzanine_frame_num
        """
        switching_positions = []
        switching_position = 0
        switching_positions.append(switching_position)
        for i in range(1, len(playout)):
            rep_id = playout[i][1]
            frag_id = playout[i][2]
            switching_position += fragment_duration_multi_reps[(rep_id, frag_id)]
            # when track change
            previous_rep_id = playout[i - 1][1]
            if rep_id != previous_rep_id:
                switching_positions.append(switching_position)

        change_switching_index_list = Observation.get_playback_change_position(
            mezzanine_qr_codes
        )

        # check configuration and actual switching matches
        configured_switching_num = len(switching_positions)
        actual_switching_num = len(change_switching_index_list)
        if actual_switching_num != configured_switching_num:
            self.result["message"] += (
                f" Number of switches does not match. "
                f"Test is configured to switch {configured_switching_num} times. "
                f"Actual number of switches is {actual_switching_num}. "
            )
            return False

        # check mid frames block by block
        playout_sequence = PlayoutParser.get_playout_sequence(playout)
        mid_frame_result = self.check_every_frame_by_block(
            mezzanine_qr_codes, change_switching_index_list, playout_sequence
        )
        for i, starting_index in enumerate(change_switching_index_list):
            if i > 0:
                # check previous ending frame and new starting frame numbers
                # the expected frame number position in the content being switched from is
                # the expected relative time of the switch
                # (derived from the test config) * that content's frames per second
                half_frame_duration = (
                    1000 / mezzanine_qr_codes[starting_index - 1].frame_rate
                ) / 2
                previous_ending_frame_num = math.floor(
                    (switching_positions[i] + half_frame_duration)
                    / 1000
                    * mezzanine_qr_codes[starting_index - 1].frame_rate
                )
                # compare expected with the actual frame number detected at this switch point
                diff_ending_frame = abs(
                    mezzanine_qr_codes[starting_index - 1].frame_number
                    - previous_ending_frame_num
                )
                if diff_ending_frame != 0:
                    mid_frame_result = False
                    self.result["message"] += (
                        f" Playout {playout_sequence[i - 1]} ending frame found is"
                        f" {mezzanine_qr_codes[starting_index - 1].frame_number },"
                        f" expected to end with {previous_ending_frame_num}."
                    )

                # the expected frame number position in the content being switched to the expected
                # the expected relative time of the switch
                # (derived from the test config) * that content's frames per second
                # compare expected with the actual frame number detected at this switch point
                half_frame_duration = (
                    1000 / mezzanine_qr_codes[starting_index].frame_rate
                ) / 2
                current_starting_frame_num = (
                    math.floor(
                        (switching_positions[i] + half_frame_duration)
                        / 1000
                        * mezzanine_qr_codes[starting_index].frame_rate
                    )
                    + 1
                )
                diff_starting_frame = abs(
                    mezzanine_qr_codes[starting_index].frame_number
                    - current_starting_frame_num
                )
                if diff_starting_frame != 0:
                    mid_frame_result = False
                    self.result["message"] += (
                        f" Playout {playout_sequence[i]} starting frame found is"
                        f" {mezzanine_qr_codes[starting_index].frame_number },"
                        f" expected to start from {current_starting_frame_num}."
                    )

        return mid_frame_result

    def observe_splicing_mid_frame(
        self,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        playouts: List[List[int]],
        fragment_duration_multi_mpd: dict,
    ) -> bool:
        """playout[i]: Provides the triple (Switching Set, CMAF track number, Fragment number)
        for every playout position i=1,…,N that is be played out.

        on each splicing point:
            check previous ending and new starting frames are correct for each periods
            check that the samples shall be rendered in increasing order within the same period
            for QRb to QRn: QR[i-1].mezzanine_frame_num + 1 == QR[i].mezzanine_frame_num
        """
        splice_start_frame_num_tolerance = self.tolerances[
            "splice_start_frame_num_tolerance"
        ]
        splice_end_frame_num_tolerance = self.tolerances[
            "splice_end_frame_num_tolerance"
        ]

        change_starting_index_list = Observation.get_playback_change_position(
            mezzanine_qr_codes
        )
        change_type_list = PlayoutParser.get_change_type_list(playouts)
        ending_playout_list = PlayoutParser.get_ending_playout_list(playouts)
        starting_playout_list = PlayoutParser.get_starting_playout_list(playouts)

        # check if the configured content change and actual content change matches
        # if not report error
        actual_change_num = len(change_starting_index_list)
        configured_change_num = len(change_type_list) + 1
        if actual_change_num != configured_change_num:
            self.result["message"] += (
                f" Number of changes does not match the 'playout' configuration. "
                f"Test is configured to change {configured_change_num} times. "
                f"Actual number of change is {actual_change_num}. "
            )
            return False
        # check mid frames block by block based on the starting index of content change
        mid_frame_result = True
        for i, starting_index in enumerate(change_starting_index_list):
            if starting_index == change_starting_index_list[-1]:
                # check mid frames for last block
                check_frame_result = mid_frame_result and self._check_every_frame(
                    mezzanine_qr_codes[change_starting_index_list[-1] :], i + 1
                )
                mid_frame_result = mid_frame_result and check_frame_result
            else:
                last_index = change_starting_index_list[i + 1] - 1
                check_frame_result = mid_frame_result and self._check_every_frame(
                    mezzanine_qr_codes[starting_index:last_index], i + 1
                )
                mid_frame_result = mid_frame_result and check_frame_result

            if i > 0:
                # check previous ending frame and new starting frame numbers
                ending_playout = ending_playout_list[i - 1]
                ending_time = 0
                for j in range(ending_playout[2]):
                    key = (ending_playout[0], ending_playout[1], j + 1)
                    ending_time += fragment_duration_multi_mpd[key]
                previous_ending_frame_num = math.floor(
                    ending_time
                    / 1000
                    * mezzanine_qr_codes[starting_index - 1].frame_rate
                )

                # compare expected with the actual frame number detected at this splice point
                diff_ending_frame = abs(
                    mezzanine_qr_codes[starting_index - 1].frame_number
                    - previous_ending_frame_num
                )

                if change_type_list[i - 1] == "splicing":
                    if diff_ending_frame > splice_end_frame_num_tolerance:
                        mid_frame_result = False
                        self.result["message"] += (
                            f" Ending with incorrect frame when splicing at period number {i}. "
                            f"Ending frame found is {mezzanine_qr_codes[starting_index -1].frame_number }, "
                            f"expected to end with {previous_ending_frame_num}. "
                            f"Splice end frame tolerance is {splice_end_frame_num_tolerance}."
                        )
                else:
                    if diff_ending_frame > 0:
                        mid_frame_result = False
                        self.result["message"] += (
                            f" Ending with incorrect frame when switching at number {i}. "
                            f"Ending frame found is {mezzanine_qr_codes[starting_index -1].frame_number }, "
                            f"expected to end with {previous_ending_frame_num}. "
                        )

                starting_playout = starting_playout_list[i - 1]
                starting_time = 0
                for j in range(starting_playout[2] - 1):
                    key = (starting_playout[0], starting_playout[1], j + 1)
                    starting_time += fragment_duration_multi_mpd[key]
                current_starting_frame_num = (
                    math.floor(
                        starting_time
                        / 1000
                        * mezzanine_qr_codes[starting_index].frame_rate
                    )
                    + 1
                )

                # compare expected with the actual frame number detected at this splice point
                diff_starting_frame = abs(
                    mezzanine_qr_codes[starting_index].frame_number
                    - current_starting_frame_num
                )

                if change_type_list[i - 1] == "splicing":
                    if diff_starting_frame > splice_start_frame_num_tolerance:
                        mid_frame_result = False
                        self.result["message"] += (
                            f" Starting from incorrect frame when splicing at period number {i + 1}. "
                            f"Starting frame found is {mezzanine_qr_codes[starting_index].frame_number }, "
                            f"expected to start from {current_starting_frame_num}. "
                            f"Splice start frame tolerance is {splice_start_frame_num_tolerance}."
                        )
                else:
                    if diff_starting_frame > 0:
                        mid_frame_result = False
                        self.result["message"] += (
                            f" Starting from incorrect frame when switching at number {i + 1}. "
                            f"Starting frame found is {mezzanine_qr_codes[starting_index].frame_number }, "
                            f"expected to start from {current_starting_frame_num}. "
                        )

        return mid_frame_result

    def observe_gap_in_playback_mid_frame(
        self, mezzanine_qr_codes: List[MezzanineDecodedQr], parameters_dict: dict
    ) -> bool:
        """
        observe gap_in_playback mid-frames
        check mid frames from beginning to gap_from_frame and from gap_to_frame till the end
        check for any frames within gap_from_frame to gap_to_frame are not rendered
        """
        mid_frame_result = False
        message = ""
        start_index = 0
        end_index = 0

        gap_from_frame = parameters_dict["gap_from_and_to_frames"][0]
        gap_to_frame = parameters_dict["gap_from_and_to_frames"][1]

        if gap_to_frame < gap_from_frame:
            message += (
                "Test configuration error: frame at the beginning of gap "
                "cannot be smaller than the ending of gap."
            )
            return mid_frame_result

        # observe every frame is rendered by separating qr codes into 2 parts
        # search to get the end index of the adjusted_gap_from_frame (added tolerance)
        adjusted_gap_from_frame = gap_from_frame
        if "stall_tolerance_margin" in parameters_dict:
            stall_tolerance_frame = (
                parameters_dict["stall_tolerance_margin"]
                / 1000
                * mezzanine_qr_codes[-1].frame_rate
            )
            adjusted_gap_from_frame += stall_tolerance_frame
        if "random_access_from_tolerance" in parameters_dict:
            random_access_from_tolerance_frame = (
                parameters_dict["random_access_from_tolerance"]
                / 1000
                * mezzanine_qr_codes[-1].frame_rate
            )
            adjusted_gap_from_frame += random_access_from_tolerance_frame
        for x in range(len(mezzanine_qr_codes)):
            if mezzanine_qr_codes[x].frame_number > adjusted_gap_from_frame:
                end_index = x - 1
                break

        # reverse search to get the start_index of gap_to_frame
        for x in range(len(mezzanine_qr_codes) - 1, 0, -1):
            if mezzanine_qr_codes[x].frame_number < gap_to_frame:
                start_index = x + 1
                break
        # check every frame is rendered before and after the gap
        check_frames_before_gap = self._check_every_frame(
            mezzanine_qr_codes[:end_index]
        )
        check_frames_after_gap = self._check_every_frame(
            mezzanine_qr_codes[start_index:]
        )
        if check_frames_before_gap and check_frames_after_gap:
            mid_frame_result = True

        # check the gap_from_frame and gap_to_frame matched with
        # the frames at end_index and start_index
        if mezzanine_qr_codes[start_index - 1].frame_number != gap_from_frame:
            if "stall_tolerance_margin" in parameters_dict:
                stall_tolerance_frame = (
                    parameters_dict["stall_tolerance_margin"]
                    / 1000
                    * mezzanine_qr_codes[-1].frame_rate
                )
                if (
                    abs(
                        mezzanine_qr_codes[start_index - 1].frame_number
                        - gap_from_frame
                    )
                    > stall_tolerance_frame
                ):
                    mid_frame_result = False
                    message += (
                        f" Last frame detected before gap {mezzanine_qr_codes[start_index - 1].frame_number}"
                        f" exceeded 'stall_tolerance_margin'={stall_tolerance_frame} frames"
                        f" of expected frame {gap_from_frame}."
                    )
                else:
                    message += (
                        f" Last frame detected before gap {mezzanine_qr_codes[start_index - 1].frame_number}"
                        f" is within the tolerance of 'stall_tolerance_margin'={stall_tolerance_frame}"
                        f" frames of expected frame {gap_from_frame}."
                    )
            elif "random_access_from_tolerance" in parameters_dict:
                random_access_from_tolerance_frame = (
                    parameters_dict["random_access_from_tolerance"]
                    / 1000
                    * mezzanine_qr_codes[-1].frame_rate
                )
                if (
                    abs(
                        mezzanine_qr_codes[start_index - 1].frame_number
                        - gap_from_frame
                    )
                    > random_access_from_tolerance_frame
                ):
                    mid_frame_result = False
                    message += (
                        f" Last frame detected before gap {mezzanine_qr_codes[start_index - 1].frame_number} exceeded"
                        f" 'random_access_from_tolerance':{random_access_from_tolerance_frame} frame"
                        f" of expected frame {gap_from_frame}."
                    )
                else:
                    message += (
                        f" Last frame detected before gap {mezzanine_qr_codes[start_index - 1].frame_number} is within the tolerance of"
                        f" 'random_access_from_tolerance':{random_access_from_tolerance_frame} frame"
                        f" of expected frame {gap_from_frame}."
                    )
            else:
                mid_frame_result = False
                message += (
                    f" Last frame detected before gap {gap_from_frame} doesn't matches"
                    f" expected frame {mezzanine_qr_codes[start_index - 1].frame_number}."
                )

        if mezzanine_qr_codes[start_index].frame_number != gap_to_frame:
            mid_frame_result = False
            message += (
                f" First frame detected after gap {gap_to_frame} doesn't matches"
                f" expected frame {mezzanine_qr_codes[start_index].frame_number}."
            )

        return mid_frame_result, message

    def observe_truncated_mid_frame(
        self,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        first_playout: List[List[int]],
        second_playout: List[List[int]],
        second_playout_switching_time: int,
        fragment_duration_multi_mpd: dict,
    ) -> bool:
        """playout[i]: Provides the triple (Switching Set, CMAF track number, Fragment number)
        for every playout position i=1,…,N that is be played out.
        first_playout: The playout parameter for the first switching set
        second_playout: The playout parameter for the second switching set
        second_playout_switching_time: The play position at which to switch to the second switching set.

        on each splicing point:
            check previous ending and new starting frames are correct for each periods
            check that the samples shall be rendered in increasing order within the same period
            for QRb to QRn: QR[i-1].mezzanine_frame_num + 1 == QR[i].mezzanine_frame_num
        """
        # check presentation changes twice
        content_starting_index_list = Observation.get_content_change_position(
            mezzanine_qr_codes
        )
        if len(content_starting_index_list) != 2:
            self.result["message"] += (
                f" Truncated test should change presentation once. "
                f"Actual presentation change is {len(content_starting_index_list) - 1}."
            )
            return False

        mezzanine_qr_codes_1 = mezzanine_qr_codes[: content_starting_index_list[1]]
        mezzanine_qr_codes_2 = mezzanine_qr_codes[content_starting_index_list[1] :]

        # check presentation one
        switching_starting_index_list_1 = Observation.get_playback_change_position(
            mezzanine_qr_codes_1
        )
        change_type_list_1 = PlayoutParser.get_change_type_list(first_playout)

        # check if the configured content change and actual content change matches
        # if not report error
        actual_change_num = len(switching_starting_index_list_1)
        configured_change_num = len(change_type_list_1) + 1
        if actual_change_num != configured_change_num:
            self.result["message"] += (
                f" For 1st presentation, number of changes does not match the 'playout' configuration. "
                f"Test is configured to change {configured_change_num} times. "
                f"Actual number of change is {actual_change_num}. "
            )
            return False

        # check presentation one
        switching_positions = []
        switching_position = 0
        switching_positions.append(switching_position)
        for i in range(1, len(first_playout)):
            switching_position += fragment_duration_multi_mpd[tuple(first_playout[i])]
            # when track change
            if first_playout[i][1] != first_playout[i - 1][1]:
                switching_positions.append(switching_position)

        change_switching_index_list = Observation.get_playback_change_position(
            mezzanine_qr_codes_1
        )

        # check configuration and actual switching matches
        configured_switching_num = len(switching_positions)
        actual_switching_num = len(change_switching_index_list)
        if actual_switching_num != configured_switching_num:
            self.result["message"] += (
                f" Presentation 1: Number of switches does not match. "
                f"Test is configured to switch {configured_switching_num} times. "
                f"Actual number of switches is {actual_switching_num}. "
            )
            return False

        # check mid frames block by block
        playout_sequence = PlayoutParser.get_playout_sequence(first_playout)
        mid_frame_result_1 = self.check_every_frame_by_block(
            mezzanine_qr_codes_1, change_switching_index_list, playout_sequence, 1
        )
        for i, starting_index in enumerate(change_switching_index_list):
            if i > 0:
                # check previous ending frame and new starting frame numbers
                # the expected frame number position in the content being switched from is the expected relative time
                # of the switch (derived from the test config) * that content's frames per second
                previous_ending_frame_num = math.floor(
                    switching_positions[i]
                    / 1000
                    * mezzanine_qr_codes_1[starting_index - 1].frame_rate
                )
                # compare expected with the actual frame number detected at this switch point
                diff_ending_frame = abs(
                    mezzanine_qr_codes_1[starting_index - 1].frame_number
                    - previous_ending_frame_num
                )
                if diff_ending_frame != 0:
                    mid_frame_result_1 = False
                    self.result["message"] += (
                        f" Playout {playout_sequence[i - 1]} ending frame found is"
                        f" {mezzanine_qr_codes_1[starting_index - 1].frame_number },"
                        f" expected to end with {previous_ending_frame_num}."
                    )

                # the expected frame number position in the content being switched to is the expected relative time
                # of the switch (derived from the test config) * that content's frames per second
                # compare expected with the actual frame number detected at this switch point
                current_starting_frame_num = (
                    math.floor(
                        switching_positions[i]
                        / 1000
                        * mezzanine_qr_codes_1[starting_index].frame_rate
                    )
                    + 1
                )
                diff_starting_frame = abs(
                    mezzanine_qr_codes_1[starting_index].frame_number
                    - current_starting_frame_num
                )
                if diff_starting_frame != 0:
                    mid_frame_result_1 = False
                    self.result["message"] += (
                        f" Playout {playout_sequence[i]} starting frame found is"
                        f" {mezzanine_qr_codes_1[starting_index].frame_number },"
                        f" expected to start from {current_starting_frame_num}."
                    )

        # check presentation one ending frame this should be in range
        # between the second_playout_switching_time and end of playout
        ending_frame_from = math.floor(
            second_playout_switching_time * mezzanine_qr_codes_1[-1].frame_rate
        )
        last_fragment = first_playout[-1]
        fragment_duration = fragment_duration_multi_mpd[tuple(last_fragment)]
        last_track_duration = fragment_duration * last_fragment[2]
        ending_frame_to = math.floor(
            last_track_duration / 1000 * mezzanine_qr_codes_1[-1].frame_rate
        )
        if (
            mezzanine_qr_codes_1[-1].frame_number < ending_frame_from
            or mezzanine_qr_codes_1[-1].frame_number > ending_frame_to
        ):
            end_frame_result = False
            self.result["message"] += (
                f" 1st presentation ending frame found is {mezzanine_qr_codes_1[-1].frame_number},"
                f" expected to end from {ending_frame_from} to {ending_frame_to}."
            )
        else:
            end_frame_result = True

        # check presentation two starting frame
        starting_frame = 1
        if starting_frame != mezzanine_qr_codes_2[0].frame_number:
            start_frame_result = False
            self.result["message"] += (
                f" 2nd presentation starting frame found is {mezzanine_qr_codes_2[0].frame_number},"
                f" expected to start with from {starting_frame}."
            )
        else:
            start_frame_result = True

        # check presentation two
        switching_starting_index_list_2 = Observation.get_playback_change_position(
            mezzanine_qr_codes_2
        )
        change_type_list_2 = PlayoutParser.get_change_type_list(second_playout)

        # check if the configured content change and actual content change matches
        # if not report error
        actual_change_num = len(switching_starting_index_list_2)
        configured_change_num = len(change_type_list_2) + 1
        if actual_change_num != configured_change_num:
            self.result["message"] += (
                f" For 2nd presentation number of changes does not match the 'playout' configuration. "
                f"Test is configured to change {configured_change_num} times. "
                f"Actual number of change is {actual_change_num}. "
            )
            return False

        # check presentation two
        switching_positions = []
        switching_position = 0
        switching_positions.append(switching_position)
        for i in range(1, len(second_playout)):
            switching_position += fragment_duration_multi_mpd[tuple(second_playout[i])]
            # when track change
            if second_playout[i][1] != second_playout[i - 1][1]:
                switching_positions.append(switching_position)

        change_switching_index_list = Observation.get_playback_change_position(
            mezzanine_qr_codes_2
        )

        # check configuration and actual switching matches
        configured_switching_num = len(switching_positions)
        actual_switching_num = len(change_switching_index_list)
        if actual_switching_num != configured_switching_num:
            self.result["message"] += (
                f" Presentation 2: Number of switches does not match. "
                f"Test is configured to switch {configured_switching_num} times. "
                f"Actual number of switches is {actual_switching_num}. "
            )
            return False

        # check mid frames block by block
        playout_sequence = PlayoutParser.get_playout_sequence(second_playout)
        mid_frame_result_2 = self.check_every_frame_by_block(
            mezzanine_qr_codes_2, change_switching_index_list, playout_sequence, 2
        )
        for i, starting_index in enumerate(change_switching_index_list):
            if i > 0:
                # check previous ending frame and new starting frame numbers
                # the expected frame number position in the content being switched from is the expected relative time
                # of the switch (derived from the test config) * that content's frames per second
                previous_ending_frame_num = math.floor(
                    switching_positions[i]
                    / 1000
                    * mezzanine_qr_codes_2[starting_index - 1].frame_rate
                )
                # compare expected with the actual frame number detected at this switch point
                diff_ending_frame = abs(
                    mezzanine_qr_codes_2[starting_index - 1].frame_number
                    - previous_ending_frame_num
                )
                if diff_ending_frame != 0:
                    mid_frame_result_2 = False
                    self.result["message"] += (
                        f" Playout {playout_sequence[i - 1]} ending frame found is"
                        f" {mezzanine_qr_codes_2[starting_index - 1].frame_number },"
                        f" expected to end with {previous_ending_frame_num}."
                    )

                # the expected frame number position in the content being switched to is the expected relative time
                # of the switch (derived from the test config) * that content's frames per second
                # compare expected with the actual frame number detected at this switch point
                current_starting_frame_num = (
                    math.floor(
                        switching_positions[i]
                        / 1000
                        * mezzanine_qr_codes_2[starting_index].frame_rate
                    )
                    + 1
                )
                diff_starting_frame = abs(
                    mezzanine_qr_codes_2[starting_index].frame_number
                    - current_starting_frame_num
                )
                if diff_starting_frame != 0:
                    mid_frame_result_2 = False
                    self.result["message"] += (
                        f" Playout {playout_sequence[i]} starting frame found is {mezzanine_qr_codes_2[starting_index].frame_number },"
                        f" expected to start from {current_starting_frame_num}."
                    )

        mid_frame_result = (
            mid_frame_result_1
            and mid_frame_result_2
            and start_frame_result
            and end_frame_result
        )
        return mid_frame_result

    def make_observation(
        self,
        test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        _audio_segments,
        _test_status_qr_codes,
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list, list]:
        """
        make_observation for different test type

        check 1st frame is present
        QRa.mezzanine_frame_num == first_frame_num

        check the last frame is present
        QRn.mezzanine_frame_num == round(cmaf_track_duration * mezzanine_frame_rate)

        Args:
            test_type: defined in test.py
            mezzanine_qr_codes: lists of MezzanineDecodedQr
            _unused:
            parameters_dict: parameter dictionary
            _unused2

        Returns:
            Dict[str, str]: observation result
        """
        logger.info("Making observation %s.", self.result["name"])

        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = (
                f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            )
            logger.info("[%s] %s", self.result["status"], self.result["message"])
            return self.result, [], []

        first_frame_result = self._check_first_frame(
            parameters_dict["first_frame_num"], mezzanine_qr_codes[0]
        )
        last_frame_result = self._check_last_frame(
            parameters_dict["last_frame_num"], mezzanine_qr_codes[-1]
        )

        message = ""
        if test_type == TestType.SWITCHING:
            mid_frame_result = self.observe_switching_mid_frame(
                mezzanine_qr_codes,
                parameters_dict["playout"],
                parameters_dict["video_fragment_duration_multi_reps"],
            )
        elif test_type == TestType.SPLICING:
            mid_frame_result = self.observe_splicing_mid_frame(
                mezzanine_qr_codes,
                parameters_dict["playout"],
                parameters_dict["video_fragment_duration_multi_mpd"],
            )
        elif test_type == TestType.GAPSINPLAYBACK:
            mid_frame_result, message = self.observe_gap_in_playback_mid_frame(
                mezzanine_qr_codes, parameters_dict
            )
        elif test_type == TestType.TRUNCATED:
            mid_frame_result = self.observe_truncated_mid_frame(
                mezzanine_qr_codes,
                parameters_dict["playout"],
                parameters_dict["second_playout"],
                parameters_dict["second_playout_switching_time"],
                parameters_dict["video_fragment_duration_multi_mpd"],
            )
        else:
            # check that the samples shall be rendered in increasing order:
            # for QRb to QRn: QR[i-1].mezzanine_frame_num + 1 == QR[i].mezzanine_frame_num
            mid_frame_result = self._check_every_frame(mezzanine_qr_codes)

        self.result["message"] += (
            f" Total of missing frame count is {self.missing_frame_count}." f"{message}"
        )

        if first_frame_result and last_frame_result and mid_frame_result:
            self.result["status"] = "PASS"
        else:
            self.result["status"] = "FAIL"

        logger.debug("[%s] %s", self.result["status"], self.result["message"])
        return self.result, [], self.mid_missing_frame_duration
