# -*- coding: utf-8 -*-
# pylint: disable=import-error
"""observation audio_every_sample_rendered

make observation of audio_every_sample_rendered

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
from typing import Dict, List, Tuple

from dpctf_audio_decoder import AudioSegment
from global_configurations import GlobalConfigurations

from .observation import Observation

logger = logging.getLogger(__name__)

REPORT_NUM_OF_FAILURE = 20


class AudioEverySampleRendered(Observation):
    """AudioEverySampleRendered class
    Every audio sample shall be rendered and the samples shall be rendered
    in increasing presentation time order.
    """

    def __init__(self, global_configurations: GlobalConfigurations, name: str = None):
        if name is None:
            name = (
                "[OF] When examined as a continuous sequence of timestamped audio samples of the audio stream,"
                "the 20ms test audio samples shall be a complete rendering of the source audio track "
                "and are rendered in increasing presentation time order."
            )
        super().__init__(name, global_configurations)

    def _get_detected_time(
        self, audio_segment: AudioSegment, parameters_dict: dict
    ) -> float:
        """return detected time from given segement"""
        detected_time = (
            audio_segment.audio_segment_timing
            + parameters_dict["first_audio_media_time"]
            - parameters_dict["offset"] / parameters_dict["sample_rate"]
        )
        return detected_time

    def _check_match_expected_time(
        self, audio_segment: AudioSegment, parameters_dict: dict
    ) -> bool:
        """check detected segment time matches expected time"""
        expected_time = audio_segment.media_time
        detected_time = self._get_detected_time(audio_segment, parameters_dict)
        difference = abs(detected_time - expected_time)
        if difference > parameters_dict["audio_sample_length"]:
            return False
        else:
            return True

    def _check_in_line_with_previous(
        self, audio_segment: AudioSegment,
        previous_audio_segment: AudioSegment,
        parameters_dict: dict
    ) -> bool:
        """Check current segement is in line with previous segment"""
        tolerance = parameters_dict["audio_sample_length"] * 2
        detected_time = self._get_detected_time(audio_segment, parameters_dict)
        previous_segment_detected_time = (
            self._get_detected_time(previous_audio_segment, parameters_dict)
        )
        diff_with_previous_segment = detected_time - previous_segment_detected_time
        if diff_with_previous_segment <= 0:
            return False
        elif diff_with_previous_segment > tolerance:
            return False
        else:
            return True

    def _check_in_line_with_next(
        self, audio_segment: AudioSegment,
        next_audio_segment: AudioSegment,
        parameters_dict: dict
    ) -> bool:
        """Check current segement is in line with next segment"""
        tolerance = parameters_dict["audio_sample_length"] * 2
        detected_time = self._get_detected_time(audio_segment, parameters_dict)
        next_segment_detected_time = (
            self._get_detected_time(next_audio_segment, parameters_dict)
        )
        diff_with_next_segment = next_segment_detected_time - detected_time
        if diff_with_next_segment <= 0:
            return False
        elif diff_with_next_segment > tolerance:
            return False
        else:
            return True

    def _check_segment(
        self, audio_segments: List[AudioSegment], i: int, parameters_dict: dict
    ) -> bool:
        """check segment is rendered one by one:
        When a segment matches expected time return True.

        If not, check the current segement is in line with other segements.
        Check that three points determins a line:
            when a segment is in line with the previous segment and the next segement return True
            when a segment is NOT in line with the previous segment and the next segement return False

            when a segment is in line with two previous segments return True
            when a segment is in line with two next segments return True
        """
        segment_match_expected_time = (
            self._check_match_expected_time(audio_segments[i], parameters_dict)
        )
        if segment_match_expected_time:
            return True

        # check current segment is in line with previous segment
        in_line_with_previous_segment = False
        if i > 0:
            in_line_with_previous_segment = self._check_in_line_with_previous(
                audio_segments[i], audio_segments[i-1], parameters_dict
            )
        # check current segment is in line with next segment
        in_line_with_next_segment = False
        if i < len(audio_segments) - 1:
            in_line_with_next_segment = self._check_in_line_with_next(
                audio_segments[i], audio_segments[i+1], parameters_dict
            )
        if not in_line_with_previous_segment and not in_line_with_next_segment:
            return False
        if in_line_with_previous_segment and in_line_with_next_segment:
            return True

        # check a segmemt is in line with two previous segments or two next segments
        if in_line_with_previous_segment:
            # check in line with one more previous segment
            # for 2nd segment, True if 1st segment is in line with it
            in_line_with_previous_segment_2 = True
            if i > 1:
                in_line_with_previous_segment_2 = self._check_in_line_with_previous(
                    audio_segments[i-1], audio_segments[i-2], parameters_dict
                )
            return in_line_with_previous_segment_2
        elif in_line_with_next_segment:
            # check in line with one more next segment
            # for the second last segment, True if last segment is in line with it
            in_line_with_next_segment_2 = True
            if i < len(audio_segments) - 2:
                in_line_with_next_segment_2 = self._check_in_line_with_next(
                    audio_segments[i+1], audio_segments[i+2], parameters_dict
                )
            return in_line_with_next_segment_2

    def _check_every_sample_rendered(
        self, audio_segments: List[AudioSegment], parameters_dict: dict
    ) -> Tuple[int, List[AudioSegment]]:
        """checks every sample is rendered and in increasing order
        returns error count and
        a list of updated audio segement which only contains correct segements"""
        updated_audio_segments = []
        error_count = 0

        for i in range(0, len(audio_segments)):
            result = self._check_segment(audio_segments, i, parameters_dict)
            if result:
                updated_audio_segments.append(audio_segments[i])
            else:
                if error_count < REPORT_NUM_OF_FAILURE:
                    expected_time = float(audio_segments[i].media_time)
                    detected_time = (
                        self._get_detected_time(audio_segments[i], parameters_dict)
                    )
                    self.result["message"] += (
                        f"Segment({round(expected_time, 2)}ms) is not detected on expected time, "
                        f"sample is found at {round(detected_time, 2)}ms. "
                    )
                error_count += 1

        return error_count, updated_audio_segments

    def make_observation(
        self,
        _test_type,
        _mezzanine_qr_codes,
        audio_segments: List[AudioSegment],
        _test_status_qr_codes,
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], List[AudioSegment]]:
        """
        make_observation for different test type

        Args:
            audio_segments: audio segment list
            parameters_dict: parameter dictionary

        Returns:
            Dict[str, str]: observation result
        """
        logger.info(f"Making observation {self.result['name']}...")

        if not audio_segments:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = "No audio segment is detected."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result, []

        error_count, updated_audio_segments = (
            self._check_every_sample_rendered(audio_segments, parameters_dict)
        )

        if error_count == 0:
            self.result["message"] += "All segments are rendered and are in order."
            self.result["status"] = "PASS"
        else:
            if error_count >= REPORT_NUM_OF_FAILURE:
                self.result["message"] += "...too many failures, reporting truncated. "
            self.result["message"] += (
                "Found " + str(error_count) + " segments out of order"
            )
            self.result["status"] = "FAIL"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")

        return self.result, updated_audio_segments
