# -*- coding: utf-8 -*-
"""DPCTF device observation test code truncated_playback_and_restart

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

from .sequential_track_playback import SequentialTrackPlayback
from .test import TestType

logger = logging.getLogger(__name__)


class TruncatedPlaybackAndRestart(SequentialTrackPlayback):
    """TruncatedPlaybackAndRestart to handle test truncated-playback-and-restart.html
    Derived from SequentialTrackPlayback test code.
    """

    def _set_test_type(self) -> None:
        """set test type"""
        self.test_type = TestType.TRUNCATED

    def _init_parameters(self) -> None:
        self.parameters = [
            "ts_max",
            "tolerance",
            "frame_tolerance",
            "duration_tolerance",
            "duration_frame_tolerance",
            "playout",
            "second_playout",
            "second_playout_switching_time",
        ]

    def _init_observations(self) -> None:
        """initialise the observations required for the test"""
        self.observations = [
            ("every_sample_rendered", "EverySampleRendered"),
            ("duration_matches_cmaf_track", "DurationMatchesCMAFTrack"),
            ("start_up_delay", "StartUpDelay"),
            ("sample_matches_current_time", "SampleMatchesCurrentTime"),
        ]

    def _get_last_frame_num(self, frame_rate: Fraction) -> int:
        """return last frame number
        this is calculated based on last track duration
        """
        last_playout = self.parameters_dict["second_playout"][-1]
        fragment_duration_multi_mpd = self.parameters_dict[
            "video_fragment_duration_multi_mpd"
        ]
        last_track_duration = 0
        for i in range(last_playout[2]):
            key = (last_playout[0], last_playout[1], i + 1)
            last_track_duration += fragment_duration_multi_mpd[key]

        half_frame_duration = (1000 / frame_rate) / 2
        last_frame_num = math.floor(
            (last_track_duration + half_frame_duration) / 1000 * frame_rate
        )
        return last_frame_num

    def _save_expected_video_track_duration(self) -> None:
        """save expected video CMAF duration
        first representation duration is second_playout_switching_time
        second representation duration is sum of all fragment duration from the second_playout
        """
        cmaf_track_durations = []
        cmaf_track_durations.append(
            self.parameters_dict["second_playout_switching_time"] * 1000
        )
        second_duration = 0.0
        fragment_duration_multi_mpd = self.parameters_dict[
            "video_fragment_duration_multi_mpd"
        ]
        for second_playout in self.parameters_dict["second_playout"]:
            fragment_duration = fragment_duration_multi_mpd[tuple(second_playout)]
            second_duration += fragment_duration
        cmaf_track_durations.append(second_duration)

        self.parameters_dict["expected_video_track_duration"] = cmaf_track_durations

    def _save_expected_audio_track_duration(self) -> None:
        """save expected audio cmaf duration"""
        # this test currently out of scope for audio
        raise Exception("Not in scope.")
