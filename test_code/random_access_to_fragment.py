# -*- coding: utf-8 -*-
"""DPCTF device observation test code random_access_to_fragment

test random_access_to_fragment

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

from .sequential_track_playback import SequentialTrackPlayback

logger = logging.getLogger(__name__)


class RandomAccessToFragment(SequentialTrackPlayback):
    """RandomAccessToFragment to handle test random-access-to-fragment.html.
    Derived from SequentialTrackPlayback test code. Uses same logic except start frame and duration take
    account of the random start point.
    """

    def _init_parameters(self) -> None:
        self.parameters = [
            "ts_max",
            "tolerance",
            "frame_tolerance",
            "random_access_fragment",
            "duration_tolerance",
            "duration_frame_tolerance",
        ]
        self.content_parameters = ["cmaf_track_duration", "fragment_duration"]

    def _get_first_frame_num(self, frame_rate: float) -> int:
        """return first frame number"""
        random_access_fragment = self.parameters_dict["random_access_fragment"]
        fragment_duration_in_second = self.parameters_dict["fragment_duration"] / 1000
        first_frame_num = (
            random_access_fragment * fragment_duration_in_second * frame_rate + 1
        )

        return math.floor(first_frame_num)

    def _get_expected_track_duration(self) -> float:
        """return expected cmaf track duration"""
        random_access_fragment = self.parameters_dict["random_access_fragment"]
        fragment_duration = self.parameters_dict["fragment_duration"]
        cmaf_track_duration = self.parameters_dict["cmaf_track_duration"]
        expected_track_duration = (
            cmaf_track_duration - random_access_fragment * fragment_duration
        )

        return expected_track_duration
