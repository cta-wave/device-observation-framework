# -*- coding: utf-8 -*-
"""
DPCTF device observation test code source-buffer-re-initialization-without-changetype

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
import math
from fractions import Fraction

from exceptions import ConfigError
from .mse_append_window import MseAppendWindow
from .test import TestType


class SourceBufferReInitializationWithoutChangetype(MseAppendWindow):
    """SourceBufferReInitializationWithoutChangetype to handle test
    source-buffer-re-initialization-without-changetype.html"""

    def _set_test_type(self) -> None:
        """set test type SEQUENTIAL|SWITCHING|SPLICING"""
        self.test_type = TestType.SPLICING

    def _init_parameters(self) -> None:
        """initialise the test_config_parameters required for the test"""
        self.parameters = [
            "mse_reset_tolerance",
            "tolerance",
            "frame_tolerance",
            "duration_tolerance",
            "duration_frame_tolerance",
            "playout",
        ]

    def _get_last_frame_num(self, frame_rate: Fraction) -> int:
        """return last frame number
        this is calculated based on last track duration
        """
        last_playout = self.parameters_dict["playout"][-1]
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
        for splicing test this is sum of all fragment duration from the playout
        """
        cmaf_track_duration = 0
        fragment_duration_multi_mpd = self.parameters_dict[
            "video_fragment_duration_multi_mpd"
        ]
        for playout in self.parameters_dict["playout"]:
            fragment_duration = fragment_duration_multi_mpd[tuple(playout)]
            cmaf_track_duration += fragment_duration
        self.parameters_dict["expected_video_track_duration"] = cmaf_track_duration

    def _save_expected_audio_track_duration(self) -> None:
        """save expected audio CMAF duration"""
        # this test is not in scope for audio
        raise ConfigError("Not in scope.")
