# -*- coding: utf-8 -*-
"""DPCTF device observation test code long_duration_playback

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
import dataclasses

from .regular_playback_of_a_cmaf_presentation import RegularPlaybackOfACmafPresentation
from .test import TestContentType
from .test import TestType


class LongDurationPlayback(RegularPlaybackOfACmafPresentation):
    """LongDurationPlayback to handle test long-duration-playback.html
    Derived from RegularPlaybackOfACmafPresentation test code.
    """

    # holds the start frame number for the current observation window
    _current_start: int = None

    def _set_test_type(self) -> None:
        """set test type"""
        self.test_type = TestType.LONGDURATIONPLAYBACK

    # this function to be removed when we have audio stream for the test
    def _set_test_content_type(self) -> None:
        """set test type SINGLE|COMBINED"""
        self.test_content_type = TestContentType.SINGLE

    # audio test to be uncommented when we have audio stream for the test
    def _init_observations(self) -> None:
        """initialise the observations required for the test"""
        self.observations = [
            (
                "every_sample_rendered",
                "EverySampleRendered",
            ),
            (
                "audio_every_sample_rendered",
                "AudioEverySampleRendered",
            ),
            ("start_up_delay", "StartUpDelay"),
            ("audio_start_up_delay", "AudioStartUpDelay"),
            ("duration_matches_cmaf_track", "DurationMatchesCMAFTrack"),
            ("audio_duration_matches_cmaf_track", "AudioDurationMatchesCMAFTrack"),
            ("sample_matches_current_time", "SampleMatchesCurrentTime"),
            (
                "earliest_sample_same_presentation_time",
                "EarliestSampleSamePresentationTime",
            ),
            (
                "audio_video_synchronization",
                "AudioVideoSynchronization",
            ),
        ]

    def set_observation_window(self, frame_number, is_start: bool) -> None:
        """Set observation_window parameters for long duration playback test"""
        if is_start:
            self._current_start = frame_number
        else:
            if self._current_start is None:
                raise ValueError("End without start")
            if "observation_window" not in self.parameters_dict:
                self.parameters_dict["observation_window"] = []
            self.parameters_dict["observation_window"].append(
                (self._current_start, frame_number)
            )
            self._current_start = None


@dataclasses.dataclass
class LongDurationPlaybackData:
    """Data class to hold long duration playback test related data and flags for optimized QR code detection during the test"""

    def __init__(self):
        self.is_reduced_detection = False
        """Flag indicating if reduced QR detection interval is active"""
        self.is_initial_detection = True
        """LD test starting check flag to handle starting check duration"""
        self.is_last_detection = False
        """LD test last check flag to handle ending check duration"""
        self.ld_last_qr_detection_start_at = 0
        """Starting frame number where last QR detection was performed for LD test"""
        self.ready_for_next_interval = True
        """Flag indicating if new QR detection interval is to be set for LD test"""
