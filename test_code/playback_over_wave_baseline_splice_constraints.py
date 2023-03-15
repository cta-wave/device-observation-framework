# -*- coding: utf-8 -*-
"""DPCTF device observation test code 
playback_over_wave_baseline_splice_constraints

test playback_over_wave_baseline_splice_constraints

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


class PlaybackOverWaveBaselineSpliceConstraints(SequentialTrackPlayback):
    """PlaybackOverWaveBaselineSpliceConstraints to handle test
    playback-over-wave-baseline-splice-constraints.html
    restricted-splicing-of-encrypted-content-https.html
    sequential-playback-of-encrypted-and-non-encrypted-baseline-content-https.html
    This class is derived from SequentialTrackPlayback and uses the same observations logic.
    """

    def _set_test_type(self) -> None:
        """set test type SEQUENTIAL|SWITCHING|SPLICING"""
        self.test_type = TestType.SPLICING

    def _init_parameters(self) -> None:
        """initialise the test_config_parameters required for the test"""
        self.parameters = [
            "ts_max",
            "tolerance",
            "frame_tolerance",
            "playout",
            "duration_tolerance",
            "duration_frame_tolerance",
        ]
        self.content_parameters = ["fragment_duration_multi_mpd"]

    def _get_last_frame_num(self, frame_rate: Fraction) -> int:
        """return last frame number
        this is calculated based on last track duration
        """
        last_playout = self.parameters_dict["playout"][-1]
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
        for splicing test this is sum of all fragment duration from the playout
        """
        cmaf_track_duration = 0
        for playout in self.parameters_dict["playout"]:
            fragment_duration = self.parameters_dict["fragment_duration_multi_mpd"][
                (playout[0], playout[1])
            ]
            cmaf_track_duration += fragment_duration
        return cmaf_track_duration
