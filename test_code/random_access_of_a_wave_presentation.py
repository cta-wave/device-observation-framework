# -*- coding: utf-8 -*-
"""DPCTF device observation test code random_access_of_a_wave_presentation

test random_access_of_a_wave_presentation

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
import math

from typing import Tuple
from .random_access_to_fragment import RandomAccessToFragment
from .test import TestContentType
from audio_file_reader import read_audio_mezzanine

logger = logging.getLogger(__name__)


class RandomAccessOfAWavePresentation(RandomAccessToFragment):
    """RandomAccessOfAWavePresentation to handle test random-access-of-a-wave-presentation.html.
    Derived from RandomAccessToFragment test code. But different observations.
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
            "av_sync_tolerance",
        ]

    def _init_observations(self) -> None:
        """initialise the observations required for the test"""
        self.observations = [
            (
                "every_sample_rendered",
                "EverySampleRendered"
            ),
            (
                "audio_every_sample_rendered",
                "AudioEverySampleRendered"
            ),
            (
                "unexpected_sample_not_rendered",
                "UnexpectSampleNotRendered"
            ),
            (
                "audio_unexpected_sample_not_rendered",
                "AudioUnexpectedSampleNotRendered"
            ),
            (
                "start_up_delay",
                "StartUpDelay"
            ),
            (
                "audio_start_up_delay",
                "AudioStartUpDelay"
            ),
            (
                "duration_matches_cmaf_track",
                "DurationMatchesCMAFTrack"
            ),
            (
                "audio_duration_matches_cmaf_track",
                "AudioDurationMatchesCMAFTrack"
            ),
            (
                "sample_matches_current_time",
                "SampleMatchesCurrentTime"
            ),
            (
                "earliest_sample_same_presentation_time",
                "EarliestSampleSamePresentationTime"
            ),
            (
                "audio_video_synchronization",
                "AudioVideoSynchronization"
            )
        ]

    def _set_test_content_type(self) -> None:
        """set test type SINGLE|COMBINED"""
        self.test_content_type = TestContentType.COMBINED

    def _save_expected_audio_track_duration(self) -> None:
        """save expected audio track duration"""
        # audio should match video
        random_access_to_time_ms = (
            self._convert_random_access_fragment_to_time("video")
        )
        self.parameters_dict["expected_audio_track_duration"] = (
            self.parameters_dict["video_content_duration"]
            - random_access_to_time_ms
        )

    def _save_last_audio_media_time(self) -> None:
        """return last audio sample time in sample position"""
        # audio should match video
        self.parameters_dict["last_audio_media_time"] = (
            self.parameters_dict["video_content_duration"]
            - self.parameters_dict["audio_sample_length"]
        )

    def _save_first_audio_media_time(self) -> None:
        """
        save first audio media time
        The audio presentation starts with the sample that corresponds to 
        the same presentation time as the earliest video sample.
        """
        random_access_to_time_ms = (
            self._convert_random_access_fragment_to_time("video")
        )
        self.parameters_dict["first_audio_media_time"] = math.floor(
            random_access_to_time_ms
        )

    def _get_audio_segment_data(
        self, audio_content_ids: list
    ) -> Tuple[float, list, list]:
        """get expected audio mezzanine data for the test
        The audio presentation starts with the sample that corresponds to 
        the same presentation time as the earliest video sample.
            start_media_time: start time of expected audio
            expected_audio_segment_data: list of expected audio data
            unexpected_audio_segment_data: unexpected audio data
        """
        audio_segment_data = read_audio_mezzanine(
            self.global_configurations, audio_content_ids[0]
        )
        # audio random access should match video
        start_media_time = (
            self._convert_random_access_fragment_to_time("video")
        )
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
