# -*- coding: utf-8 -*-
"""DPCTF device observation test code low_latency_playback_over_gaps

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

from .random_access_from_one_place_in_a_stream_to_a_different_place_in_the_same_stream import \
    RandomAccessFromOnePlaceInAStreamToADifferentPlaceInTheSameStream
from .test import TestType

logger = logging.getLogger(__name__)


class LowLatencyPlaybackOverGaps(
    RandomAccessFromOnePlaceInAStreamToADifferentPlaceInTheSameStream
):
    """LowLatencyPlaybackOverGaps to handle test low_latency_playback_over_gaps.html
    Derived from MseAppendWindow test code. Uses same logic.
    """

    def _init_parameters(self) -> None:
        self.parameters = [
            "tolerance",
            "frame_tolerance",
            "duration_tolerance",
            "duration_frame_tolerance",
            "min_buffer_duration",
            "gap_duration",
            "playback_mode",
            "stall_tolerance_margin",
        ]
        self.content_parameters = ["cmaf_track_duration", "fragment_duration"]

    def _get_gap_from_and_to_frames(self, frame_rate):
        """return gap from and to frames"""
        gap_from = self.parameters_dict["min_buffer_duration"]
        if "gap_duration" in self.parameters_dict:
            gap_to = gap_from + self.parameters_dict["gap_duration"] / 1000
        else:
            gap_to = gap_from + self.parameters_dict["fragment_duration"] / 1000
        gap_from_frame = math.floor(gap_from * frame_rate)
        gap_to_frame = math.floor(gap_to * frame_rate) + 1
        return [gap_from_frame, gap_to_frame]

    def _get_expected_track_duration(self) -> float:
        """return expected cmaf track duration"""
        cmaf_track_duration_ms = self.parameters_dict["cmaf_track_duration"]
        expected_track_duration = cmaf_track_duration_ms
        if self.parameters_dict["playback_mode"] == "vod":
            if "gap_duration" in self.parameters_dict:
                expected_track_duration = (
                    cmaf_track_duration_ms - self.parameters_dict["gap_duration"]
                )
            else:
                expected_track_duration = (
                    cmaf_track_duration_ms - self.parameters_dict["fragment_duration"]
                )
        return expected_track_duration
