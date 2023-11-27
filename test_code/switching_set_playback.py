# -*- coding: utf-8 -*-
"""DPCTF device observation test code switching_set_playback

test switching_set_playback

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
from .test import TestType

logger = logging.getLogger(__name__)


class SwitchingSetPlayback(SequentialTrackPlayback):
    """SwitchingSetPlayback to handle test
    switching-set-playback.html
    overlapping-fragments.html
    This class is derived from SequentialTrackPlayback and uses the same observations logic.
    """

    def _set_test_type(self) -> None:
        """set test type SEQUENTIAL|SWITCHING|SPLICING"""
        self.test_type = TestType.SWITCHING

    def _init_parameters(self) -> None:
        """initialise the test_config_parameters required for the test"""
        self.parameters = [
            "ts_max",
            "tolerance",
            "frame_tolerance",
            "playout",
            "duration_tolerance",
            "duration_frame_tolerance",
            "audio_sample_length",
            "audio_tolerance",
            "audio_sample_tolerance",
        ]
        if "audio" in self.content_type:
            # maybe skip the playout for audio
            # audio switching set test is not in scope
            self.parameters = [
                "ts_max",
                "tolerance",
                "frame_tolerance",
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
            ]
        if "audio" in self.content_type:
            self.observations = [
                ("audio_every_sample_rendered", "AudioEverySampleRendered"),
                ("audio_duration_matches_cmaf_track", "AudioDurationMatchesCMAFTrack"),
                ("audio_start_up_delay", "AudioStartUpDelay"),
            ]
