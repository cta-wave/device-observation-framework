# -*- coding: utf-8 -*-
"""Observation audio_duration_matches_cmaf_track

Make observation of audio_duration_matches_cmaf_track

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
from typing import Dict, List, Tuple

from dpctf_audio_decoder import AudioSegment
from global_configurations import GlobalConfigurations

from .observation import Observation


class AudioDurationMatchesCMAFTrack(Observation):
    """AudioDurationMatchesCMAFTrack class
    The playback duration of the playback matches the duration of the CMAF Track,
    i.e. TR [k, S] = TR [k, 1] + td[k].
    """

    def __init__(self, global_configurations: GlobalConfigurations):
        super().__init__(
            "[OF] Audio: The playback duration shall match the duration of the CMAF Track.",
            global_configurations,
        )

    def _get_starting_missing_time(
        self, expected_start_time: float, first_segment: AudioSegment
    ) -> float:
        """returns the difference between expected and actual start times"""
        missing_time = first_segment.media_time - expected_start_time
        return missing_time

    def _get_ending_missing_time(
        self, expected_end_time: float, last_segment: AudioSegment
    ) -> float:
        """returns the difference between expected and actual end times"""
        missing_time = expected_end_time - round(
            last_segment.media_time + last_segment.duration
        )
        return missing_time

    def make_observation(
        self,
        _test_type,
        _mezzanine_qr_codes,
        audio_segments: List[AudioSegment],
        _test_status_qr_codes,
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list, list]:
        """make observations"""
        self.logger.info("Making observation %s.", self.result["name"])

        if not audio_segments:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = "No audio segment is detected."
            self.logger.info("[%s] %s", self.result["status"], self.result["message"])
            return self.result, [], []

        detected_audio_duration = (
            audio_segments[-1].audio_segment_timing
            + audio_segments[-1].duration
            - audio_segments[0].audio_segment_timing
        )

        start_missing_time = self._get_starting_missing_time(
            parameters_dict["audio_starting_time"], audio_segments[0]
        )
        end_missing_time = self._get_ending_missing_time(
            parameters_dict["audio_ending_time"], audio_segments[-1]
        )
        expected_duration = (
            parameters_dict["expected_audio_track_duration"]
            - start_missing_time
            - end_missing_time
        )
        tolerance = parameters_dict["duration_tolerance"]
        time_difference = abs(detected_audio_duration - expected_duration)

        # checking for negative detected audio duration
        if detected_audio_duration < 0:
            self.result["status"] = "FAIL"
            self.result["message"] = (
                f"Detected duration is {detected_audio_duration}ms, "
                "the duration can not be negative."
            )
            return self.result, [], []

        # checking if the time difference is greater than the tolerance
        if time_difference > tolerance:
            self.result["status"] = "FAIL"
            self.result["message"] += (
                f"Playback duration is {round(detected_audio_duration, 2)}ms does not match "
                f"expected track duration is {round(expected_duration, 2)}. "
                f"Detected duration is different by {round(time_difference, 2)}ms. "
                f"Allowed tolerance is {tolerance}ms."
            )
        else:
            self.result["status"] = "PASS"
            self.result["message"] += (
                f"Playback duration is {round(detected_audio_duration, 2)}ms, "
                f"expected track duration is {round(expected_duration, 2)}. "
                f"Detected duration is different by {round(time_difference, 2)}ms. "
                f"Allowed tolerance is {tolerance}ms."
            )
        self.logger.debug("[%s] %s", self.result["status"], self.result["message"])
        return self.result, [], []
