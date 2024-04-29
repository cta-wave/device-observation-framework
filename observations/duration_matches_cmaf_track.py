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
Contributor: Resillion UK Limited
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

    def _get_waiting_frame(
            self,
            test_status_qr_codes: List[TestStatusDecodedQr],
            mezzanine_qr_codes: List[MezzanineDecodedQr],
            camera_frame_duration_ms: float,
        ) -> int:
        """
        detect the waiting in playback based on the test runner status qr code
        return frame number mezzanine index where the playback waiting is detected
        """
        waiting_start_time = 0
        status = ""
        waiting_mezzanine_frame = 0
        play_start_frame = mezzanine_qr_codes[1].first_camera_frame_num
        # start detecting waiting only after the play is started
        # and ignore a few waiting status before the playback start
        # assume test runner status is reported correctly on time
        for x in range(len(test_status_qr_codes)):
            if test_status_qr_codes[x].camera_frame_num < play_start_frame:
                # skip status before the play starts (2nd detected frame)
                # which we used to measure duration from
                continue
            if status == "" and test_status_qr_codes[x].status == "playing":
                status = "playing"
            elif status == "playing" and test_status_qr_codes[x].status == "waiting":
                waiting_start_time = (
                    test_status_qr_codes[x].camera_frame_num * camera_frame_duration_ms
                    - test_status_qr_codes[x + 1].delay
                )
                waiting_frame = int(waiting_start_time / camera_frame_duration_ms)
                # get matching waiting mezzanine_qr_code
                for i in range(len(mezzanine_qr_codes)):
                    if mezzanine_qr_codes[i].first_camera_frame_num > waiting_frame:
                        waiting_mezzanine_frame = i
                        break
                break
        return waiting_mezzanine_frame

    def _get_gap_frame(
            self,
            mezzanine_qr_codes: List[MezzanineDecodedQr],
            frame_after_gap: int,
        ) -> int:
        """
        detect the gap in playback
        return frame number where the playback gap is detected
        """
        detected_mezzanine_index_at_gap = 0
        # reverse search to get the index of the gap
        for x in range(len(mezzanine_qr_codes) -1, 0, -1):
            if mezzanine_qr_codes[x].frame_number < frame_after_gap:
                detected_mezzanine_index_at_gap = x
                break
        return detected_mezzanine_index_at_gap

    def check_duration_equal_or_greater(
        self,
        expected_track_duration: float,
        camera_frame_duration_ms: float,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        parameters_dict: dict,
        mid_missing_frame_duration:float
    ) -> bool:
        """duration check for truncated test presentation one"""
        result = False
        first_frame_duration = 1000 / mezzanine_qr_codes[0].frame_rate
        last_frame_duration = 1000 / mezzanine_qr_codes[-1].frame_rate

        # adjust expected track duration based on the starting missing frames
        starting_missing_frame = self._get_starting_missing_frame(
            parameters_dict["first_frame_num"], mezzanine_qr_codes[0]
        )
        expected_track_duration -= starting_missing_frame * first_frame_duration

        # adjust expected track duration based on the ending missing frames
        ending_missing_frame = self._get_ending_missing_frame(
            parameters_dict["last_frame_num"], mezzanine_qr_codes[-1]
        )
        expected_track_duration -= ending_missing_frame * last_frame_duration

        # playback duration get measured from the 2nd detected frame
        # till the last detected frame
        playback_duration = (
            mezzanine_qr_codes[-1].first_camera_frame_num
            - mezzanine_qr_codes[1].first_camera_frame_num
        ) * camera_frame_duration_ms + first_frame_duration + last_frame_duration

        if playback_duration >= expected_track_duration:
            self.result["message"] += (
                f"Playback duration {round(playback_duration, 2)}ms is "
                f"equal to or greater than the duration of the 'second_playout_switching_time'. "
                f"Expected track duration is {round(expected_track_duration, 2)}ms."
            )
            result = True
        else:
            if mid_missing_frame_duration > 0:
                if playback_duration + mid_missing_frame_duration >= expected_track_duration:
                    self.result["message"] += (
                        f"Playback duration {round(playback_duration, 2)}ms is "
                        f"equal to or greater than the duration of the 'second_playout_switching_time'. "
                        f"Expected track duration is {round(expected_track_duration, 2)}ms. "
                        f"The media timeline is not preserved for mid missing frames and "
                        f"{round(mid_missing_frame_duration, 2)}ms duration is dropped from the media timeline."
                    )
                    result = True
                else:
                    self.result["message"] += (
                        f"Playback duration {round(playback_duration, 2)}ms is not "
                        f"equal to or greater than the duration of the 'second_playout_switching_time'. "
                        f"Expected track duration is {round(expected_track_duration, 2)}ms. "
                        f"Mid missing frame duration is {round(mid_missing_frame_duration, 2)}ms. "
                    )
                    result = False
            else:
                self.result["message"] += (
                    f"Playback duration {round(playback_duration, 2)}ms is not "
                    f"equal to or greater than the duration of the 'second_playout_switching_time'. "
                    f"Expected track duration is {round(expected_track_duration, 2)}ms."
                )
                result = False

        return result

    def check_duration_match(
        self,
        expected_track_duration: float,
        waiting_frame: int,
        test_type: TestType,
        camera_frame_duration_ms: float,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        parameters_dict: dict,
        mid_missing_frame_duration: float,
    ) -> bool:
        """
        check detected duration matches with the expected duration
        """
        duration_tolerance = parameters_dict["duration_tolerance"]
        duration_frame_tolerance = parameters_dict["duration_frame_tolerance"]

        first_frame_duration = 1000 / mezzanine_qr_codes[0].frame_rate
        last_frame_duration = 1000 / mezzanine_qr_codes[-1].frame_rate

        # adjust expected track duration based on the starting missing frames
        starting_missing_frame = self._get_starting_missing_frame(
            parameters_dict["first_frame_num"], mezzanine_qr_codes[0]
        )
        expected_track_duration -= starting_missing_frame * first_frame_duration

        # adjust expected track duration based on the ending missing frames
        ending_missing_frame = self._get_ending_missing_frame(
            parameters_dict["last_frame_num"], mezzanine_qr_codes[-1]
        )
        expected_track_duration -= ending_missing_frame * last_frame_duration

        # waiting in playback
        if waiting_frame > 1 and waiting_frame < len(mezzanine_qr_codes) - 1:
            # playback duration get measured from the 2nd detected frame
            # till the last detected frame
            playback_duration = (
                mezzanine_qr_codes[waiting_frame - 1].first_camera_frame_num
                - mezzanine_qr_codes[1].first_camera_frame_num
            ) * camera_frame_duration_ms + 2 * first_frame_duration
            playback_duration += (
                mezzanine_qr_codes[-1].first_camera_frame_num
                - mezzanine_qr_codes[waiting_frame + 1].first_camera_frame_num
            ) * camera_frame_duration_ms + 2 * last_frame_duration

            # if there is a gap in frame number adjust expected duration
            if (test_type == TestType.GAPSINPLAYBACK):
                frame_num_gap = (
                    mezzanine_qr_codes[waiting_frame + 1].frame_number 
                    - mezzanine_qr_codes[waiting_frame].frame_number
                )
                expected_track_duration -= (
                    frame_num_gap - 1
                ) * first_frame_duration
        else:
            # playback duration is measured from the 2nd detected frame
            # till the last detected frame
            playback_duration = (
                mezzanine_qr_codes[-1].first_camera_frame_num
                - mezzanine_qr_codes[1].first_camera_frame_num
            ) * camera_frame_duration_ms + first_frame_duration + last_frame_duration

        total_tolerance_duration = (
            duration_tolerance
            + duration_frame_tolerance * 1000 / mezzanine_qr_codes[-1].frame_rate
        )
        if "mse_reset_tolerance" in parameters_dict:
            total_tolerance_duration += parameters_dict["mse_reset_tolerance"]

        duration_diff = abs(expected_track_duration - playback_duration)
        if duration_diff > total_tolerance_duration:
            if (
                mid_missing_frame_duration > 0 and
                expected_track_duration > playback_duration
            ):
                adjusted_duration_diff = abs(
                    duration_diff - mid_missing_frame_duration
                )
                if adjusted_duration_diff > total_tolerance_duration:
                    result = False
                    self.result["message"] += (
                        f"Playback duration {round(playback_duration, 2)}ms does not match expected duration "
                        f"{round(expected_track_duration, 2)}ms +/- tolerance of {duration_tolerance}ms. "
                        f"Detected duration is different by {round(duration_diff, 2)}ms. "
                        f"Mid missing frame duration is {round(mid_missing_frame_duration, 2)}ms. "
                    )
                else:
                    result = True
                    self.result["message"] += (
                        f"Playback duration is {round(playback_duration, 2)}ms, expected track duration is "
                        f"{round(expected_track_duration, 2)}ms. "
                        f"Detected duration is different by {round(duration_diff, 2)}ms. "
                        f"The media timeline is not preserved for mid missing frames and "
                        f"{round(mid_missing_frame_duration, 2)}ms duration is dropped from the media timeline."
                    )
            else:
                result = False
                self.result["message"] += (
                    f"Playback duration {round(playback_duration, 2)}ms does not match expected duration "
                    f"{round(expected_track_duration, 2)}ms +/- tolerance of {duration_tolerance}ms. "
                    f"Detected duration is different by {round(duration_diff, 2)}ms."
                )
        else:
            result = True
            self.result["message"] += (
                f"Playback duration is {round(playback_duration, 2)}ms, expected track duration is "
                f"{round(expected_track_duration, 2)}ms. "
                f"Detected duration is different by {round(duration_diff, 2)}ms."
            )

        self.result["message"] += (
            f" Allowed tolerance is {duration_tolerance}ms and duration frame tolerance is {duration_frame_tolerance}."
            f" Starting missing frame number is {starting_missing_frame}."
            f" Ending missing frame number is {ending_missing_frame}."
        )
        if "mse_reset_tolerance" in parameters_dict:
            additional_tolerance = parameters_dict["mse_reset_tolerance"]
            self.result[
                "message"
            ] += f" Additional allowed mse_reset_tolerance is {additional_tolerance}ms."

        return result

    def make_observation(
        self,
        test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        _audio_segments,
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list, list]:
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
            return self.result, [], []

        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]

        first_mid_missing_frame_duration = 0
        second_mid_missing_frame_duration = 0
        if parameters_dict["mid_missing_frame_duration"]:
            first_mid_missing_frame_duration = parameters_dict["mid_missing_frame_duration"][0]
            second_mid_missing_frame_duration = parameters_dict["mid_missing_frame_duration"][1]

        mezzanine_index_at_gap = 0
        # find the mezzanine_index_at_gap to adjust duration check
        # when waiting in playback (all frames rendered) or gap in playback (some frames not rendered)
        if test_type == TestType.WAITINGINPLAYBACK:
            mezzanine_index_at_gap = self._get_waiting_frame(
                test_status_qr_codes, mezzanine_qr_codes, camera_frame_duration_ms
            )
        if test_type == TestType.GAPSINPLAYBACK:
            frame_after_gap = parameters_dict["gap_from_and_to_frames"][1]
            mezzanine_index_at_gap = self._get_gap_frame(
                mezzanine_qr_codes, frame_after_gap
            )
            # when playback mode is live the track catches up with time
            if "playback_mode" in parameters_dict:
                if parameters_dict["playback_mode"] == "live":
                    mezzanine_index_at_gap = 0

        if test_type == TestType.TRUNCATED:
            # check individually for first presentation and second presentation
            change_starting_index_list = Observation.get_content_change_position(
                mezzanine_qr_codes
            )
            if len(change_starting_index_list) != 2:
                self.result["status"] = "FAIL"
                self.result["message"] += (
                    f" Truncated test should change presentation once. "
                    f"Actual presentation change is {len(change_starting_index_list) - 1}."
                )
                return self.result, [], []
            # Check first presentation
            self.result["message"] += "First presentation: "
            first_result = self.check_duration_equal_or_greater(
                parameters_dict["expected_video_track_duration"][0],
                camera_frame_duration_ms,
                mezzanine_qr_codes[: change_starting_index_list[1] - 1],
                parameters_dict,
                first_mid_missing_frame_duration,
            )
            # Check second presentation
            self.result["message"] += " Second presentation: "
            second_result = self.check_duration_match(
                parameters_dict["expected_video_track_duration"][1],
                mezzanine_index_at_gap,
                test_type,
                camera_frame_duration_ms,
                mezzanine_qr_codes[change_starting_index_list[1] :],
                parameters_dict,
                second_mid_missing_frame_duration,
            )
            result = first_result and second_result
        else:
            result = self.check_duration_match(
                parameters_dict["expected_video_track_duration"],
                mezzanine_index_at_gap,
                test_type,
                camera_frame_duration_ms,
                mezzanine_qr_codes,
                parameters_dict,
                first_mid_missing_frame_duration,
            )

        if result:
            self.result["status"] = "PASS"
        else:
            self.result["status"] = "FAIL"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")
        return self.result, [], []
