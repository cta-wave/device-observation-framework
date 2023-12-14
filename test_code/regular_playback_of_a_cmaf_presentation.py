# -*- coding: utf-8 -*-
"""DPCTF device observation test code regular_playback_of_a_cmaf_presentation

test regular_playback_of_a_cmaf_presentation

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

from .sequential_track_playback import SequentialTrackPlayback
from .test import TestContentType

logger = logging.getLogger(__name__)


class RegularPlaybackOfACmafPresentation(SequentialTrackPlayback):
    """RegularPlaybackOfACmafPresentation to handle test regular-playback-of-a-cmaf-presentation.html
    This class is derived from SequentialTrackPlayback but different observations.
    """

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
            ),
        ]

    def _init_parameters(self) -> None:
        """initialise the test_config_parameters required for the test"""
        self.parameters = [
            "ts_max",
            "tolerance",
            "frame_tolerance",
            "duration_tolerance",
            "duration_frame_tolerance",
            "audio_sample_length",
            "audio_tolerance",
            "audio_sample_tolerance",
            "av_sync_tolerance"
        ]

    def _set_test_content_type(self) -> None:
        """set test type SINGLE|COMBINED"""
        self.test_content_type = TestContentType.COMBINED

    def _save_expected_audio_track_duration(self) -> None:
        """save expected audio track duration"""
        # audio should match video
        self.parameters_dict["expected_audio_track_duration"] = (
            self.parameters_dict["video_content_duration"]
        )

    def _save_audio_ending_time(self) -> None:
        """save audio ending time"""
        # audio should match video
        self.parameters_dict["audio_ending_time"] = (
            self.parameters_dict["video_content_duration"]
        )
