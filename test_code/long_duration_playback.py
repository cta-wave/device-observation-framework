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
import logging

from .regular_playback_of_a_cmaf_presentation import RegularPlaybackOfACmafPresentation
from .test import TestContentType

logger = logging.getLogger(__name__)


class LongDurationPlayback(RegularPlaybackOfACmafPresentation):
    """LongDurationPlayback to handle test long-duration-playback.html
    Derived from RegularPlaybackOfACmafPresentation test code.
    """

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
            #(
            #    "audio_every_sample_rendered",
            #    "AudioEverySampleRendered",
            #),
            ("start_up_delay", "StartUpDelay"),
            #("audio_start_up_delay", "AudioStartUpDelay"),
            ("duration_matches_cmaf_track", "DurationMatchesCMAFTrack"),
            #("audio_duration_matches_cmaf_track", "AudioDurationMatchesCMAFTrack"),
            ("sample_matches_current_time", "SampleMatchesCurrentTime"),
            #(
            #    "earliest_sample_same_presentation_time",
            #    "EarliestSampleSamePresentationTime",
            #),
            #(
            #    "audio_video_synchronization",
            #    "AudioVideoSynchronization",
            #),
        ]
