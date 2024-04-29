# -*- coding: utf-8 -*-
"""DPCTF device observation test code random_access_to_fragment

test random_access_to_fragment

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
from fractions import Fraction
from typing import Tuple

from audio_file_reader import read_audio_mezzanine

from .sequential_track_playback import SequentialTrackPlayback

logger = logging.getLogger(__name__)


class RandomAccessToFragment(SequentialTrackPlayback):
    """RandomAccessToFragment to handle test random-access-to-fragment.html.
    Derived from SequentialTrackPlayback test code.Uses same logic except start frame
    and duration take account of the random start point.
    """

    def _init_parameters(self) -> None:
        self.parameters = [
            "ts_max",
            "tolerance",
            "frame_tolerance",
            "random_access_fragment",
            "duration_tolerance",
            "duration_frame_tolerance",
            "audio_sample_length",
            "audio_tolerance",
            "audio_sample_tolerance",
        ]

    def _init_observations(self) -> None:
        """initialise the observations required for the test"""
        if "video" in self.content_type:
            self.observations = [
                ("every_sample_rendered", "EverySampleRendered"),
                ("duration_matches_cmaf_track", "DurationMatchesCMAFTrack"),
                ("start_up_delay", "StartUpDelay"),
                ("sample_matches_current_time", "SampleMatchesCurrentTime"),
                ("unexpected_sample_not_rendered", "UnexpectedSampleNotRendered"),
            ]
        else:
            self.observations = [
                ("audio_every_sample_rendered", "AudioEverySampleRendered"),
                ("audio_duration_matches_cmaf_track", "AudioDurationMatchesCMAFTrack"),
                ("audio_start_up_delay", "AudioStartUpDelay"),
                (
                    "audio_unexpected_sample_not_rendered",
                    "AudioUnexpectedSampleNotRendered",
                ),
            ]

    def _convert_random_access_fragment_to_time(self, content_type) -> float:
        """convert random_access_fragment to random_access_to_time in second"""
        fragment_durations_parameter = content_type + "_fragment_durations"
        random_access_to_time = 0
        for i in range(self.parameters_dict["random_access_fragment"]):
            random_access_to_time += self.parameters_dict[fragment_durations_parameter][
                i
            ]
        return random_access_to_time

    def _get_first_frame_num(self, frame_rate: Fraction) -> int:
        """return first frame number"""
        random_access_to_time = self._convert_random_access_fragment_to_time("video")
        first_frame_num = math.floor(random_access_to_time / 1000 * frame_rate + 1)
        return first_frame_num

    def _save_expected_video_track_duration(self) -> None:
        """save expected video cmaf track duration"""
        random_access_to_time_ms = self._convert_random_access_fragment_to_time("video")
        self.parameters_dict["expected_video_track_duration"] = (
            self.parameters_dict["video_content_duration"] - random_access_to_time_ms
        )

    def _save_expected_audio_track_duration(self) -> None:
        """save expected audio cmaf track duration"""
        random_access_to_time_ms = self._convert_random_access_fragment_to_time("audio")
        self.parameters_dict["expected_audio_track_duration"] = (
            self.parameters_dict["audio_content_duration"] - random_access_to_time_ms
        )

    def _save_audio_starting_time(self) -> None:
        """save audio starting time"""
        random_access_to_time_ms = self._convert_random_access_fragment_to_time("audio")
        self.parameters_dict["audio_starting_time"] = math.floor(
            random_access_to_time_ms
        )

    def _get_audio_segment_data(
        self, audio_content_ids: list
    ) -> Tuple[float, list, list]:
        """
        get expected audio mezzanine data for the test
            start_media_time: start time of expected audio
            expected_audio_segment_data: list of expected audio data
            unexpected_audio_segment_data: unexpected audio data
        """
        audio_segment_data = read_audio_mezzanine(
            self.global_configurations, audio_content_ids[0]
        )
        start_media_time = self._convert_random_access_fragment_to_time("audio")
        random_access_point = math.floor(
            start_media_time * self.parameters_dict["sample_rate"]
        )
        expected_audio_segment_data = audio_segment_data[random_access_point:].copy()
        unexpected_audio_segment_data = audio_segment_data[0:random_access_point].copy()
        return (
            start_media_time,
            [expected_audio_segment_data],
            unexpected_audio_segment_data,
        )

    def _save_audio_data(
        self,
        audio_subject_data: list,
        expected_audio_segment_data: list,
        unexpected_audio_segment_data: list,
    ) -> None:
        """Override method to save audio data to be used in
        audio_unexpected_sample_not_rendered"""
        self.parameters_dict["audio_subject_data"] = audio_subject_data
        self.parameters_dict["expected_audio_segment_data"] = (
            expected_audio_segment_data
        )
        self.parameters_dict["unexpected_audio_segment_data"] = (
            unexpected_audio_segment_data
        )
