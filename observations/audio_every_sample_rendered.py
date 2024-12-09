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
Contributor: Resillion UK Limited
"""
import logging
from typing import Dict, List, Tuple

from dpctf_audio_decoder import AudioSegment
from global_configurations import GlobalConfigurations
from test_code.test import TestType

from .observation import Observation

logger = logging.getLogger(__name__)

REPORT_NUM_OF_FAILURE = 20


class AudioEverySampleRendered(Observation):
    """AudioEverySampleRendered class
    Every audio sample shall be rendered and the samples shall be rendered
    in increasing presentation time order.
    """

    total_error_count = 0
    """total error segments count"""

    def __init__(self, global_configurations: GlobalConfigurations, name: str = None):
        if name is None:
            name = (
                "[OF] When examined as a continuous sequence of timestamped audio samples of "
                "the audio stream, the 20ms test audio samples shall be a complete rendering of "
                "the source audio track and are rendered in increasing presentation time order."
            )
        super().__init__(name, global_configurations)

    def _get_detected_time(
        self, audio_segment: AudioSegment, parameters_dict: dict
    ) -> float:
        """return detected time from given segment"""
        detected_time = (
            audio_segment.audio_segment_timing
            + parameters_dict["audio_starting_time"]
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
        self,
        audio_segment: AudioSegment,
        previous_audio_segment: AudioSegment,
        parameters_dict: dict,
    ) -> bool:
        """Check current segment is in line with previous segment"""
        tolerance = self.global_configurations.get_audio_alignment_tolerance()
        detected_time = self._get_detected_time(audio_segment, parameters_dict)
        previous_segment_detected_time = self._get_detected_time(
            previous_audio_segment, parameters_dict
        )
        diff_with_previous_segment = detected_time - previous_segment_detected_time
        if diff_with_previous_segment <= 0:
            return False
        elif (
            abs(diff_with_previous_segment - parameters_dict["audio_sample_length"])
            > tolerance
        ):
            return False
        else:
            return True

    def _check_in_line_with_next(
        self,
        audio_segment: AudioSegment,
        next_audio_segment: AudioSegment,
        parameters_dict: dict,
    ) -> bool:
        """Check current segment is in line with next segment"""
        tolerance = self.global_configurations.get_audio_alignment_tolerance()
        detected_time = self._get_detected_time(audio_segment, parameters_dict)
        next_segment_detected_time = self._get_detected_time(
            next_audio_segment, parameters_dict
        )
        diff_with_next_segment = next_segment_detected_time - detected_time
        if diff_with_next_segment <= 0:
            return False
        elif (
            abs(diff_with_next_segment - parameters_dict["audio_sample_length"])
            > tolerance
        ):
            return False
        else:
            return True

    def _check_segment(
        self, audio_segments: List[AudioSegment], i: int, parameters_dict: dict
    ) -> bool:
        """check segment is rendered one by one:
        When a segment matches expected time return True.
        If not, check the current segment is in line with other segments.
        Check that three points determine a line:
            when a segment is in line with the previous segment and the next segment
              return True
            when a segment is NOT in line with the previous segment and the next segment
              return False
            when a segment is in line with two previous segments return True
            when a segment is in line with two next segments return True
        """
        segment_match_expected_time = self._check_match_expected_time(
            audio_segments[i], parameters_dict
        )
        if segment_match_expected_time:
            return True

        # check current segment is in line with previous segment
        in_line_with_previous_segment = False
        if i > 0:
            in_line_with_previous_segment = self._check_in_line_with_previous(
                audio_segments[i], audio_segments[i - 1], parameters_dict
            )
        # check current segment is in line with next segment
        in_line_with_next_segment = False
        if i < len(audio_segments) - 1:
            in_line_with_next_segment = self._check_in_line_with_next(
                audio_segments[i], audio_segments[i + 1], parameters_dict
            )
        if not in_line_with_previous_segment and not in_line_with_next_segment:
            return False
        if in_line_with_previous_segment and in_line_with_next_segment:
            return True

        # check a segment is in line with two previous segments
        if in_line_with_previous_segment:
            # check in line with one more previous segment
            # for 2nd segment, True if 1st segment is correctly rendered
            if i > 1:
                in_line_with_previous_segment_2 = self._check_in_line_with_previous(
                    audio_segments[i - 1], audio_segments[i - 2], parameters_dict
                )
            else:
                in_line_with_previous_segment_2 = self._check_match_expected_time(
                    audio_segments[0], parameters_dict
                )
            return in_line_with_previous_segment_2

        # check a segment is in line with two next segments
        if in_line_with_next_segment:
            # check in line with one more next segment
            # for the second last segment, True if last segment is in line with it
            if i < len(audio_segments) - 2:
                in_line_with_next_segment_2 = self._check_in_line_with_next(
                    audio_segments[i + 1], audio_segments[i + 2], parameters_dict
                )
            else:
                in_line_with_next_segment_2 = self._check_match_expected_time(
                    audio_segments[len(audio_segments) - 1], parameters_dict
                )
            return in_line_with_next_segment_2

    def _check_every_sample_rendered(
        self, audio_segments: List[AudioSegment], parameters_dict: dict
    ) -> Tuple[int, List[AudioSegment]]:
        """
        checks every sample is rendered and in increasing order returns error count
        and a list of updated audio segment which only contains correct segments
        """
        updated_audio_segments = []
        starting_error_count = None
        ending_error_count = 0
        mid_error_count = 0
        error_count = 0
        failing_message = ""

        for i in range(0, len(audio_segments)):
            result = self._check_segment(audio_segments, i, parameters_dict)
            if result:
                if starting_error_count is None:
                    starting_error_count = error_count
                ending_error_count = 0
                updated_audio_segments.append(audio_segments[i])
            else:
                if error_count < REPORT_NUM_OF_FAILURE:
                    expected_time = int(audio_segments[i].media_time)
                    failing_message += f"{expected_time}ms "
                ending_error_count += 1
                error_count += 1

        self.total_error_count += error_count
        mid_error_count = error_count - starting_error_count - ending_error_count
        if error_count > 0:
            self.result[
                "message"
            ] += "Audio segments failed at the following timestamps: "
            self.result["message"] += failing_message

        if error_count >= REPORT_NUM_OF_FAILURE:
            self.result["message"] += "...too many failures, reporting truncated. "

        return (
            starting_error_count,
            ending_error_count,
            mid_error_count,
            updated_audio_segments,
        )

    def make_observation(
        self,
        test_type,
        _mezzanine_qr_codes,
        audio_segments: List[AudioSegment],
        _test_status_qr_codes,
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], List[AudioSegment], list]:
        """
        make_observation for different test type

        Args:
            audio_segments: audio segment list
            parameters_dict: parameter dictionary

        Returns:
            Dict[str, str]: observation result
        """
        logger.info("Making observation %s.", self.result["name"])

        if not audio_segments:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = "No audio segment is detected."
            logger.info("[%s] %s", self.result["status"], self.result["message"])
            return self.result, [], []

        start_segment_num_tolerance = self.tolerances["start_segment_num_tolerance"]
        end_segment_num_tolerance = self.tolerances["end_segment_num_tolerance"]
        mid_segment_num_tolerance = self.tolerances["mid_segment_num_tolerance"]
        splice_start_segment_num_tolerance = self.tolerances[
            "splice_start_segment_num_tolerance"
        ]
        splice_end_segment_num_tolerance = self.tolerances[
            "splice_end_segment_num_tolerance"
        ]

        starting_error_count = 0
        ending_error_count = 0
        mid_error_count = 0
        max_splice_starting_error_count = 0
        max_splice_ending_error_count = 0
        updated_audio_segments = []

        if test_type == TestType.SPLICING:
            chunk_list = Observation.get_audio_segments_chunk(audio_segments)
            mid_error_count = 0
            for i in range(0, len(chunk_list)):
                (
                    splice_starting_error_count,
                    splice_ending_error_count,
                    splice_mid_error_count,
                    updated_audio_chunk,
                ) = self._check_every_sample_rendered(chunk_list[i], parameters_dict)
                mid_error_count += splice_mid_error_count
                if i == 0:
                    starting_error_count = splice_starting_error_count
                else:
                    if splice_starting_error_count > max_splice_starting_error_count:
                        max_splice_starting_error_count = splice_starting_error_count
                if i == len(chunk_list) - 1:
                    ending_error_count = splice_ending_error_count
                else:
                    if splice_ending_error_count > max_splice_ending_error_count:
                        max_splice_ending_error_count = splice_ending_error_count
                updated_audio_segments.extend(updated_audio_chunk)
        else:
            (
                starting_error_count,
                ending_error_count,
                mid_error_count,
                updated_audio_segments,
            ) = self._check_every_sample_rendered(audio_segments, parameters_dict)

        self.result[
            "message"
        ] += f"Found {self.total_error_count} segments are missing. "
        if (
            mid_error_count > mid_segment_num_tolerance
            or starting_error_count > start_segment_num_tolerance
            or ending_error_count > end_segment_num_tolerance
            or max_splice_starting_error_count > splice_start_segment_num_tolerance
            or max_splice_ending_error_count > splice_end_segment_num_tolerance
        ):
            if starting_error_count > 0:
                self.result["message"] += (
                    f"{starting_error_count} start segment failed, "
                    f"tolerance is {start_segment_num_tolerance}. "
                )
            if ending_error_count > 0:
                self.result["message"] += (
                    f"{ending_error_count} end segment failed, "
                    f"tolerance is {end_segment_num_tolerance}. "
                )
            if mid_error_count > 0:
                self.result["message"] += (
                    f"{mid_error_count} mid segment failed, "
                    f"tolerance is {mid_segment_num_tolerance}. "
                )
            if max_splice_starting_error_count > 0:
                self.result["message"] += (
                    f"Splice start segment number tolerance is "
                    f"{splice_start_segment_num_tolerance}. "
                )
            if max_splice_ending_error_count > 0:
                self.result[
                    "message"
                ] += f"Splice end segment number tolerance is {splice_end_segment_num_tolerance}. "
            self.result["status"] = "FAIL"
        else:
            self.result[
                "message"
            ] += "Segments are rendered in order within the tolerance."
            self.result["status"] = "PASS"

        logger.debug("[%s] %s", self.result["status"], self.result["message"])

        return self.result, updated_audio_segments, []
