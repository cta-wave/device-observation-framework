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
Contributor: Eurofins Digital Product Testing UK Limited
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
        self.content_parameters = ["fragment_duration_multi_mpd"]

    def _get_last_frame_num(self, frame_rate: Fraction) -> int:
        """return last frame number
        this is calculated based on last track duration
        """
        last_playout = self.parameters_dict["second_playout"][-1]
        fragment_duration = self.parameters_dict["fragment_duration_multi_mpd"][
            (last_playout[0], last_playout[1])
        ]
        last_track_duration = fragment_duration * last_playout[2]
        half_duration_frame = (1000 / frame_rate) / 2
        last_frame_num = math.floor(
            (last_track_duration + half_duration_frame) / 1000 * frame_rate
        )
        return last_frame_num

    def _get_expected_track_duration(self) -> float:
        """return expected CMAF duration
        first representation duration is second_playout_switching_time
        second representation duration is sum of all fragment duration from the second_playout
        """
        cmaf_track_durations = []
        cmaf_track_durations.append(
            self.parameters_dict["second_playout_switching_time"] * 1000
        )
        second_duration = 0.0
        for second_playout in self.parameters_dict["second_playout"]:
            fragment_duration = self.parameters_dict["fragment_duration_multi_mpd"][
                (second_playout[0], second_playout[1])
            ]
            second_duration += fragment_duration
        cmaf_track_durations.append(second_duration)

        return cmaf_track_durations
