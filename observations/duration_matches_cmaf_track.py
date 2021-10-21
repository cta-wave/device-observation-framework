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

from .observation import Observation
from typing import List, Dict
from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr
from global_configurations import GlobalConfigurations

logger = logging.getLogger(__name__)

class DurationMatchesCMAFTrack(Observation):
    """DurationMatchesCMAFTrack class
    The playback duration of the playback matches the duration of the CMAF Track, i.e. TR [k, S] = TR [k, 1] + td[k].
    """
    def __init__(self, global_configurations: GlobalConfigurations):
        super().__init__(
            "[OF] The playback duration of the playback matches the duration of the CMAF Track, "
            "i.e. TR [k, S] = TR [k, 1] + td[k].",
            global_configurations)

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

    @staticmethod
    def get_frame_change_after_play(
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        test_status_qr_codes: List[TestStatusDecodedQr],
        camera_frame_duration_ms: dict,
    ) -> int:
        first_play_qr_index = 0
        event_found, play_ct = Observation._get_play_event(
            test_status_qr_codes, camera_frame_duration_ms
        )

        if event_found:
            for i, mezzanine_qr_code in enumerate(mezzanine_qr_codes):
                frame_ct = (
                    mezzanine_qr_code.first_camera_frame_num * camera_frame_duration_ms
                )
                print("play_ct", play_ct, "frame_ct", frame_ct)
                if frame_ct >= play_ct:
                    first_play_qr_index = i
                    break
        print(first_play_qr_index)
        return first_play_qr_index

    def make_observation(
        self,
        _unused1,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
        _unused2,
    ) -> Dict[str, str]:
        """Implements the logic:
        (QRn.last_camera_frame_num - QRa.first_camera_frame_num) * camera_frame_duration_ms
        == expected_track_duration +/- tolerance
        """
        logger.info(f"Making observation {self.result['name']}...")
        duration_tolerance_ms = self.tolerances["duration_tolerance_ms"]

        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "FAIL"
            self.result[
                "message"
            ] = f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result

        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]
        first_play_qr_index = self.get_frame_change_after_play(
            mezzanine_qr_codes, test_status_qr_codes, camera_frame_duration_ms
        )
        starting_missing_frame = self._get_starting_missing_frame(
            parameters_dict["first_frame_num"], mezzanine_qr_codes[0]
        )
        ending_missing_frame = self._get_ending_missing_frame(
            parameters_dict["last_frame_num"], mezzanine_qr_codes[-1]
        )
        first_frame_duration = 1000 / mezzanine_qr_codes[0].frame_rate
        last_frame_duration = 1000 / mezzanine_qr_codes[-1].frame_rate

        # playback duration get measured from the frame change after play()
        # till the last detected frame
        playback_duration = (
            mezzanine_qr_codes[-1].first_camera_frame_num
            - mezzanine_qr_codes[first_play_qr_index].first_camera_frame_num
        ) * camera_frame_duration_ms + last_frame_duration

        # adjust expected track duration based on the missing frames
        start_frames_to_take_out = starting_missing_frame + first_play_qr_index
        expected_duration = (
            parameters_dict["expected_track_duration"]
            - start_frames_to_take_out * first_frame_duration
            - ending_missing_frame * last_frame_duration
        )

        if abs(expected_duration - playback_duration) > duration_tolerance_ms:
            self.result["status"] = "FAIL"
            self.result["message"] = (
                f"Playback duration {round(playback_duration, 2)}ms does not match expected duration "
                f"{round(expected_duration, 2)}ms +/- tolerance of {duration_tolerance_ms}ms."
            )
        else:
            self.result["status"] = "PASS"
            self.result["message"] = (
                f"Playback duration is {round(playback_duration, 2)}ms, expected track duration is "
                f"{round(expected_duration, 2)}ms."
            )
        
        self.result["message"] += (
            f" Allowed tolerance is {duration_tolerance_ms}ms."
            f" Starting missing frame number is {starting_missing_frame}."
            f" Ending missing frame number is {ending_missing_frame}."
        )

        logger.debug(f"[{self.result['status']}] {self.result['message']}")
        return self.result
