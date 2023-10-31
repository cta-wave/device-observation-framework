# -*- coding: utf-8 -*-
"""DPCTF device observation test code
random_access_from_one_place_in_a_stream_to_a_different_place_in_the_same_stream

test random_access_from_one_place_in_a_stream_to_a_different_place_in_the_same_stream

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

from .mse_append_window import MseAppendWindow
from .test import TestType

logger = logging.getLogger(__name__)


class RandomAccessFromOnePlaceInAStreamToADifferentPlaceInTheSameStream(
    MseAppendWindow
):

    """RandomAccessFromOnePlaceInAStreamToADifferentPlaceInTheSameStream to handle
    test random-access-from-one-place-in-a-stream-to-a-different-place-in-the-same-stream.html.
    Derived from MseAppendWindow test code. Uses same logic except start frame and duration take
    account of the random start point.
    """

    def _set_test_type(self) -> None:
        """set test type"""
        self.test_type = TestType.GAPSINPLAYBACK

    def _init_parameters(self) -> None:
        self.parameters = [
            "tolerance",
            "frame_tolerance",
            "random_access_to",
            "random_access_from",
            "random_access_from_tolerance",
            "duration_tolerance",
            "duration_frame_tolerance",
        ]

    def _get_gap_from_and_to_frames(self, frame_rate: Fraction) -> list:
        """return gap from and to frames"""
        random_access_from_frame = math.floor(
            (self.parameters_dict["random_access_from"]) * frame_rate
        )
        random_access_to_frame = (
            math.floor((self.parameters_dict["random_access_to"]) * frame_rate) + 1
        )
        return [random_access_from_frame, random_access_to_frame]

    def _save_expected_video_track_duration(self) -> None:
        """save expected video cmaf track duration"""
        video_cmaf_track_duration_ms = self.parameters_dict["video_content_duration"]
        random_access_from_ms = self.parameters_dict["random_access_from"] * 1000
        random_access_to_ms = self.parameters_dict["random_access_to"] * 1000
        expected_video_track_duration = random_access_from_ms + (
            video_cmaf_track_duration_ms - random_access_to_ms
        )
        self.parameters_dict[
            "expected_video_track_duration"
        ] = expected_video_track_duration

    def _save_expected_audio_track_duration(self) -> None:
        """save expected audio cmaf track duration"""
        # Audio observation not in scope
        raise Exception("Not in scope.")
