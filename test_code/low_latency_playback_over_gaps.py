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
Contributor: Resillion UK Limited
"""
import logging
import math
from fractions import Fraction

from .random_access_from_one_place_in_a_stream_to_a_different_place_in_the_same_stream import (
    RandomAccessFromOnePlaceInAStreamToADifferentPlaceInTheSameStream,
)

logger = logging.getLogger(__name__)


class LowLatencyPlaybackOverGaps(
    RandomAccessFromOnePlaceInAStreamToADifferentPlaceInTheSameStream
):
    """LowLatencyPlaybackOverGaps to handle test low_latency_playback_over_gaps.html
    Derived from MseAppendWindow test code. Uses same logic.
    """

    def _init_parameters(self) -> None:
        """initialise the observations required for the test"""
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

    def _get_gap_from_and_to_frames(self, frame_rate: Fraction) -> list:
        """return gap from and to frames"""
        gap_from = self.parameters_dict["min_buffer_duration"]
        if "gap_duration" in self.parameters_dict:
            gap_to = gap_from + self.parameters_dict["gap_duration"] / 1000
        else:
            # if "gap_duration" not defined the gap will be same as a video_fragment_duration
            # taking video_fragment_duration from the 1st video fragment
            gap_to = (
                gap_from + self.parameters_dict["video_fragment_durations"][0] / 1000
            )
        gap_from_frame = math.floor(gap_from * frame_rate)
        gap_to_frame = math.floor(gap_to * frame_rate) + 1
        return [gap_from_frame, gap_to_frame]

    # def _save_expected_video_track_duration(self) -> None:
    #    """save expected video cmaf track duration"""
    #    video_cmaf_track_duration_ms = self.parameters_dict["video_content_duration"]
    #    expected_video_track_duration = video_cmaf_track_duration_ms
    #    if self.parameters_dict["playback_mode"] == "vod":
    #        if "gap_duration" in self.parameters_dict:
    #            expected_video_track_duration = (
    #                video_cmaf_track_duration_ms - self.parameters_dict["gap_duration"]
    #            )
    #        else:
                # if "gap_duration" not defined the gap will be same as a video_fragment_duration
                # taking video_fragment_duration from the 1st video fragment
    #            expected_video_track_duration = (
    #                video_cmaf_track_duration_ms
    #                - self.parameters_dict["video_fragment_durations"][0]
    #            )
    #    self.parameters_dict[
    #        "expected_video_track_duration"
    #    ] = expected_video_track_duration

    def _save_expected_audio_track_duration(self) -> None:
        """save expected audio cmaf track duration"""
        # Audio observation not in scope
        raise Exception("Not in scope.")
