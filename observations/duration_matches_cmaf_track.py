# -*- coding: utf-8 -*-
"""Observation duration_matches_cmaf_track

Make observation of duration_matches_cmaf_track

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
from typing import Dict, List, Tuple

from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr
from global_configurations import GlobalConfigurations
from test_code.test import TestType

from .observation import Observation

logger = logging.getLogger(__name__)


class DurationMatchesCMAFTrack(Observation):
    """DurationMatchesCMAFTrack class
    The playback duration of the playback matches the duration of the CMAF Track,
    i.e. TR [k, S] = TR [k, 1] + td[k].
    """

    def __init__(self, global_configurations: GlobalConfigurations):
        super().__init__(
            "[OF] Video: The playback duration shall match the duration of the CMAF Track",
            global_configurations,
        )

    def _get_starting_missing_frame(
        self, expected_first_frame_num: int, first_qr_code: MezzanineDecodedQr
    ) -> int:
        """return missing starting frame numbers that take account in duration check
        Args:
            expected_first_frame_num: expected frame number of the first frame
            first_qr_code: first MezzanineDecodedQr from MezzanineDecodedQr lists
        Returns:
            int: missing frame numbers on starting that take account in duration check
        """
        missing_frames = first_qr_code.frame_number - expected_first_frame_num
        return missing_frames

    def _get_ending_missing_frame(
        self, expected_last_frame_num: int, last_qr_code: MezzanineDecodedQr
    ) -> int:
        """Return missing ending frame numbers that take account in duration check
        Args:
            expected_last_frame_num: expected frame number of the last frame
            last_qr_code: last  MezzanineDecodedQr from MezzanineDecodedQr lists
        Returns:
            int: missing frame numbers on ending that take account in duration check
        """
        missing_frames = expected_last_frame_num - last_qr_code.frame_number
        return missing_frames

    def _get_waiting_duration(self, test_status_qr_codes, camera_frame_duration_ms):
        """
        calculate waiting duration based on the test runner status qr code
        return minimin possible gap duration and maximun possible gap duration
        """
        min_gap_duration = 0
        max_gap_duration = 0
        waiting_start_time = 0
        playing_start_time = 0
        status = ""

        # start detecting waiting only after the play is started
        # and ignore a few waiting status before the playback start
        # assume test runner status is reported correctly on time
        for x in range(len(test_status_qr_codes)):
            if status == "" and test_status_qr_codes[x].status == "playing":
                status = "playing"
            elif status == "playing" and test_status_qr_codes[x].status == "waiting":
                waiting_start_time = (
                    test_status_qr_codes[x].camera_frame_num * camera_frame_duration_ms
                    - test_status_qr_codes[x + 1].delay
                )
                status = "waiting"
            elif status == "waiting" and test_status_qr_codes[x].status == "playing":
                playing_start_time = (
                    test_status_qr_codes[x].camera_frame_num * camera_frame_duration_ms
                    - test_status_qr_codes[x + 1].delay
                )
                min_gap_duration += (
                    playing_start_time - waiting_start_time - camera_frame_duration_ms
                )
                max_gap_duration += (
                    playing_start_time - waiting_start_time + camera_frame_duration_ms
                )
                status = "playing"
        return [min_gap_duration, max_gap_duration]

    def check_duration_match(
        self,
        expected_track_duration,
        waiting_durations,
        camera_frame_duration_ms,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        parameters_dict: dict,
        adjust_starting_missing_frames,
        adjust_ending_missing_frames,
    ) -> bool:
        """
        check detected duration matches with the expected duration
        """
        duration_tolerance = parameters_dict["duration_tolerance"]
        duration_frame_tolerance = parameters_dict["duration_frame_tolerance"]

        first_frame_duration = 1000 / mezzanine_qr_codes[0].frame_rate
        last_frame_duration = 1000 / mezzanine_qr_codes[-1].frame_rate

        if adjust_starting_missing_frames:
            starting_missing_frame = self._get_starting_missing_frame(
                parameters_dict["first_frame_num"], mezzanine_qr_codes[0]
            )
            # adjust expected track duration based on the missing frames
            expected_track_duration -= starting_missing_frame * first_frame_duration

        if adjust_ending_missing_frames:
            ending_missing_frame = self._get_ending_missing_frame(
                parameters_dict["last_frame_num"], mezzanine_qr_codes[-1]
            )
            # adjust expected track duration based on the missing frames
            expected_track_duration -= ending_missing_frame * last_frame_duration

        if adjust_starting_missing_frames:
            # playback duration get measured from the 2nd detected frame
            # till the last detected frame
            playback_duration = (
                mezzanine_qr_codes[-1].first_camera_frame_num
                - mezzanine_qr_codes[1].first_camera_frame_num
            ) * camera_frame_duration_ms + first_frame_duration + last_frame_duration
        else:
            playback_duration = (
                mezzanine_qr_codes[-1].first_camera_frame_num
                - mezzanine_qr_codes[0].first_camera_frame_num
            ) * camera_frame_duration_ms + last_frame_duration

        total_tolerance_duration = (
            duration_tolerance
            + duration_frame_tolerance * 1000 / mezzanine_qr_codes[-1].frame_rate
        )
        if "mse_reset_tolerance" in parameters_dict:
            total_tolerance_duration += parameters_dict["mse_reset_tolerance"]
        if "stall_tolerance_margin" in parameters_dict:
            total_tolerance_duration += parameters_dict["stall_tolerance_margin"]
        if "random_access_from_tolerance" in parameters_dict:
            total_tolerance_duration += parameters_dict["random_access_from_tolerance"]

        # duration check for truncated test presentation one
        # where adjust_starting_missing_frames=True and adjust_ending_missing_frames=Flase
        if adjust_starting_missing_frames and not adjust_ending_missing_frames:
            duration_diff = playback_duration - expected_track_duration
            if duration_diff >= 0:
                result = True
                self.result["message"] += (
                    f"Playback duration {round(playback_duration, 2)}ms is "
                    f"equal to or greater than the duration of the expected track duration "
                    f"{round(expected_track_duration, 2)}ms."
                )
            else:
                result = False
                self.result["message"] += (
                    f"Playback duration {round(playback_duration, 2)}ms is not "
                    f"equal to or greater than the duration of the expected track duration "
                    f"{round(expected_track_duration, 2)}ms."
                )
            return result

        # waiting in playback
        # if gap in duration check the different duration is within the minimum possible gap
        # and mximun possible gap taking into account the duration tolerance as well
        if waiting_durations:
            duration_diff = abs(expected_track_duration - playback_duration)
            if (
                duration_diff > waiting_durations[1] + total_tolerance_duration
                or duration_diff < waiting_durations[0] - total_tolerance_duration
            ):
                result = False
                self.result["message"] += (
                    f"Playback duration {round(playback_duration, 2)}ms does not match expected duration "
                    f"{round(expected_track_duration, 2)}ms. "
                    f"Minimum waiting durationn is {round(waiting_durations[0], 2)}ms, "
                    f"and Maximun waiting duration is {round(waiting_durations[1], 2)}ms."
                )
            else:
                result = True
                self.result["message"] += (
                    f"Playback duration is {round(playback_duration, 2)}ms, expected track duration is "
                    f"{round(expected_track_duration, 2)}ms. "
                    f"Minimum waiting durationn is {round(waiting_durations[0], 2)}ms, "
                    f"and Maximun waiting duration is {round(waiting_durations[1], 2)}ms."
                )
        # all other general playback
        else:
            duration_diff = abs(expected_track_duration - playback_duration)
            if duration_diff > total_tolerance_duration:
                result = False
                self.result["message"] += (
                    f"Playback duration {round(playback_duration, 2)}ms does not match expected duration "
                    f"{round(expected_track_duration, 2)}ms +/- tolerance of {duration_tolerance}ms."
                )
            else:
                result = True
                self.result["message"] += (
                    f"Playback duration is {round(playback_duration, 2)}ms, expected track duration is "
                    f"{round(expected_track_duration, 2)}ms."
                )

        self.result[
            "message"
        ] += f" Allowed tolerance is {duration_tolerance}ms and duration frame tolerance is {duration_frame_tolerance}."
        if adjust_starting_missing_frames:
            self.result["message"] += (
                f" Starting missing frame number is {starting_missing_frame}."
            )
        if adjust_ending_missing_frames:
            self.result[
                "message"
            ] += f" Ending missing frame number is {ending_missing_frame}."

        if "mse_reset_tolerance" in parameters_dict:
            additional_tolerance = parameters_dict["mse_reset_tolerance"]
            self.result[
                "message"
            ] += f" Additional allowed mse_reset_tolerance is {additional_tolerance}ms."
        if "stall_tolerance_margin" in parameters_dict:
            additional_tolerance = parameters_dict["stall_tolerance_margin"]
            self.result[
                "message"
            ] += f" Additional allowed stall_tolerance_margin is {additional_tolerance}ms."
        if "random_access_from_tolerance" in parameters_dict:
            additional_tolerance = parameters_dict["random_access_from_tolerance"]
            self.result[
                "message"
            ] += f" Additional allowed random_access_from_tolerance is {additional_tolerance}ms."

        return result

    def make_observation(
        self,
        test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        _audio_segments,
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list]:
        """Implements the logic:
        (QRn.last_camera_frame_num - QRa.first_camera_frame_num) * camera_frame_duration_ms
        == expected_track_duration +/- tolerance
        """
        logger.info(f"Making observation {self.result['name']}...")

        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "NOT_RUN"
            self.result[
                "message"
            ] = f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result, []

        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]

        waiting_durations = []
        # adjust expected duration based on waiting in playback
        if test_type == TestType.WAITINGINPLAYBACK:
            waiting_durations = self._get_waiting_duration(
                test_status_qr_codes, camera_frame_duration_ms
            )

        if test_type == TestType.TRUNCATED:
            # check individualy for first presentation and second presentaion
            change_starting_index_list = Observation.get_content_change_position(
                mezzanine_qr_codes
            )
            # only concider start missing frames
            adjust_starting_missing_frames = True
            adjust_ending_missing_frames = False
            self.result["message"] += "First presentation: "
            first_result = self.check_duration_match(
                parameters_dict["expected_video_track_duration"][0],
                waiting_durations,
                camera_frame_duration_ms,
                mezzanine_qr_codes[: change_starting_index_list[1] - 1],
                parameters_dict,
                adjust_starting_missing_frames,
                adjust_ending_missing_frames,
            )
            # only concider ending missing frames
            adjust_starting_missing_frames = False
            adjust_ending_missing_frames = True
            self.result["message"] += " Second presentation: "
            second_result = self.check_duration_match(
                parameters_dict["expected_video_track_duration"][1],
                waiting_durations,
                camera_frame_duration_ms,
                mezzanine_qr_codes[change_starting_index_list[1] :],
                parameters_dict,
                adjust_starting_missing_frames,
                adjust_ending_missing_frames,
            )
            result = first_result and second_result
        else:
            adjust_starting_missing_frames = True
            adjust_ending_missing_frames = True
            result = self.check_duration_match(
                parameters_dict["expected_video_track_duration"],
                waiting_durations,
                camera_frame_duration_ms,
                mezzanine_qr_codes,
                parameters_dict,
                adjust_starting_missing_frames,
                adjust_ending_missing_frames,
            )

        if result:
            self.result["status"] = "PASS"
        else:
            self.result["status"] = "FAIL"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")
        return self.result, []
