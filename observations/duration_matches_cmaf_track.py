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
from dpctf_qr_decoder import MezzanineDecodedQr
from global_configurations import GlobalConfigurations

logger = logging.getLogger(__name__)

DURATION_TOLERANCE_MS = 10


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
        when missing_frames exceed the start_frame_num_tolerance
        duration check only take account start_frame_num_tolerance 

        Args:
            expected_first_frame_num: expected frame number of the first frame
            first_qr_code: first MezzanineDecodedQr from MezzanineDecodedQr lists

        Returns:
            int: missing frame numbers on starting that take account in duration check
        """
        start_frame_num_tolerance = self.tolerances["start_frame_num_tolerance"]
        missing_frames = first_qr_code.frame_number - expected_first_frame_num

        if start_frame_num_tolerance < abs(missing_frames):
            missing_frames = start_frame_num_tolerance

        return missing_frames

    def _get_ending_missing_frame(
        self, expected_last_frame_num: int, last_qr_code: MezzanineDecodedQr
    ) -> int:
        """Return missing ending frame numbers that take account in duration check
        when missing_frames exceed the end_frame_num_tolerance
        duration check only take account end_frame_num_tolerance 

        Args:
            expected_last_frame_num: expected frame number of the last frame
            last_qr_code: last  MezzanineDecodedQr from MezzanineDecodedQr lists

        Returns:
            int: missing frame numbers om ending that take account in duration check
        """
        end_frame_num_tolerance = self.tolerances["end_frame_num_tolerance"]
        missing_frames = expected_last_frame_num - last_qr_code.frame_number

        if end_frame_num_tolerance < abs(missing_frames):
            missing_frames = end_frame_num_tolerance

        return missing_frames

    def make_observation(
        self,
        _unused1,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        _unused2,
        parameters_dict: dict
    ) -> Dict[str, str]:
        """Implements the logic:
        (QRn.last_camera_frame_num - QRa.first_camera_frame_num) * camera_frame_duration_ms
        == expected_track_duration +/- tolerance
        """
        logger.info(f"Making observation {self.result['name']}...")

        if not mezzanine_qr_codes:
            self.result["status"] = "FAIL"
            self.result[
                "message"
            ] = f"No mezzanine QR code detected."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result

        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]
        first_frame_duration = 1000 / mezzanine_qr_codes[0].frame_rate
        last_frame_duration = 1000 / mezzanine_qr_codes[0].frame_rate
        playback_duration = (
            mezzanine_qr_codes[-1].first_camera_frame_num
            - mezzanine_qr_codes[0].first_camera_frame_num
        ) * camera_frame_duration_ms + last_frame_duration
        expected_track_duration = parameters_dict["expected_track_duration"]

        starting_missing_frame = self._get_starting_missing_frame(
            parameters_dict["first_frame_num"], mezzanine_qr_codes[0]
        )
        ending_missing_frame = self._get_ending_missing_frame(
            parameters_dict["last_frame_num"], mezzanine_qr_codes[-1]
        )

        # adjust expected track duration based on the missing frames
        expected_track_duration = (
            expected_track_duration
            - starting_missing_frame * first_frame_duration
            + ending_missing_frame * last_frame_duration
        )
        
        if abs(expected_track_duration - playback_duration) > DURATION_TOLERANCE_MS:
            self.result["status"] = "FAIL"
            self.result["message"] = (
                f"Playback duration {round(playback_duration, 2)}ms does not match expected duration "
                f"{round(expected_track_duration, 2)}ms +/- tolerance of {DURATION_TOLERANCE_MS}ms."
            )
        else:
            self.result["status"] = "PASS"
            self.result["message"] = (
                f"Playback duration is {round(playback_duration, 2)}ms, CMAF track duration is "
                f"{expected_track_duration}ms."
            )
        
        self.result["message"] += (
            f" Allowed tolerance is {DURATION_TOLERANCE_MS}ms."
            f" Starting missing frame tolerance is {starting_missing_frame}."
            f" Ending missing frame tolerance is {ending_missing_frame}."
        )

        logger.debug(f"[{self.result['status']}] {self.result['message']}")
        return self.result
