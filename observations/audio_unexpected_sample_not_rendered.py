# -*- coding: utf-8 -*-
# pylint: disable=import-error,logging-fstring-interpolation,consider-using-enumerate, bare-except
"""Observation AudioUnexpectedSampleNotRendered

Make observation of audio_unexpected_sample_not_rendered

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
from typing import Dict, List, Tuple

import numpy as np

from audio_file_reader import get_time_from_segment
from dpctf_audio_decoder import AudioSegment, get_trim_from
from global_configurations import GlobalConfigurations

from .observation import Observation

REPORT_NUM_OF_FAILURE = 50
logger = logging.getLogger(__name__)


class AudioUnexpectedSampleNotRendered(Observation):
    """AudioUnexpectedSampleNotRendered class
    No audio sample earlier than random_access_fragment shall be rendered.
    """

    def __init__(self, global_configurations: GlobalConfigurations, name: str = None):
        if name is None:
            name = "[OF] No audio sample earlier than random access shall be rendered."
        super().__init__(name, global_configurations)

    def _get_audio_segment_diffs(self, parameters: Dict) -> list:
        """
        Compare each segment of unexpected audio with recorded audio data
        from start of tests till prior to beginning of expected segment data,
        and calculate offsets for an each unexpected audio segment.
        returns lists of differences with previous segment.
        """
        subject_data = parameters["audio_subject_data"]
        audio_segment_timings = []
        unexpected_segment = parameters["unexpected_audio_segment_data"]
        expected_segment = parameters["expected_audio_segment_data"]
        sample_rate = parameters["sample_rate"]
        observation_period = sample_rate * parameters["audio_sample_length"]
        # get sub-data in recording prior to beginning of segment data
        trim_to = get_trim_from(
            subject_data,
            expected_segment,
            sample_rate,
            parameters["audio_sample_length"],
            self.global_configurations,
            True,
        )
        pre_segment_data = subject_data[0:trim_to].copy()
        duration = math.floor((len(unexpected_segment)) / sample_rate)
        max_segments = math.floor(duration * sample_rate / observation_period)
        audio_segment_timings = np.zeros((max_segments), dtype=np.uint)
        segment_diffs_pre = [0] * max_segments
        # loop unexpected segments and get the segment time and
        # calculate diffs with previous and next segments
        for i in range(0, max_segments):
            this_segment = unexpected_segment[
                (i * observation_period) : ((i + 1) * observation_period)
            ]
            audio_segment_timings[i] = get_time_from_segment(
                pre_segment_data, this_segment
            )
            if i > 0:
                current = audio_segment_timings[i].item()
                previous = (audio_segment_timings[i - 1]).item()
                segment_diffs_pre[i] = current - previous
        return segment_diffs_pre

    def _within_tolerance(self, value: int, parameters_dict: dict) -> bool:
        """
        check value is within the defined tolerance
        and value cannot be negative
        """
        observation_period = (
            parameters_dict["sample_rate"] * parameters_dict["audio_sample_length"]
        )
        # tolerance 1 ms
        tolerance = parameters_dict["sample_rate"]
        if value < 0:
            return False
        diff = abs(value - observation_period)
        if diff < tolerance:
            return True
        else:
            return False

    def make_observation(
        self,
        _test_type,
        _mezzanine_qr_codes,
        audio_segments: List[AudioSegment],
        _test_status_qr_codes,
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list, list]:
        """
        make_observation for different test type

        Args:
            audio_segments: detected audio segment list,
                only used to check if there is any audio detected
            parameters_dict: parameter dictionary

        Returns:
            Dict[str, str]: observation result
        """
        logger.info("Making observation %s.", self.result["name"])

        if not audio_segments:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = "No audio segment is detected."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result, [], []

        sample_length = parameters_dict["audio_sample_length"]
        segment_diffs_pre = self._get_audio_segment_diffs(parameters_dict)
        segment_count = len(segment_diffs_pre)
        # check that unexpected segments are NOT aligned
        # segments are aligned when two diffs are within tolerance
        error_count = 0
        for i in range(0, segment_count):
            aligned = False
            # previous diff within tolerance - aligned with previous
            if self._within_tolerance(segment_diffs_pre[i], parameters_dict):
                # check next segment is aligned
                if i + 1 < segment_count:
                    if self._within_tolerance(
                        segment_diffs_pre[i + 1], parameters_dict
                    ):
                        aligned = True
                # Two previous segments are aligned then set aligned to True
                # check one more previous segment is aligned
                else:
                    if i == 0:
                        continue
                    if self._within_tolerance(
                        segment_diffs_pre[i - 1], parameters_dict
                    ):
                        aligned = True

            # if previous diff NOT within tolerance - NOT aligned with previous
            else:
                # check next two segments are aligned
                if i + 2 >= segment_count:
                    continue
                if self._within_tolerance(
                    segment_diffs_pre[i + 1], parameters_dict
                ) and self._within_tolerance(segment_diffs_pre[i + 2], parameters_dict):
                    aligned = True

            if aligned:
                error_count += 1
                if error_count == 1:
                    self.result[
                        "message"
                    ] += f"Unexpected audio samples detected at segment: {i * sample_length}ms"
                if 1 < error_count <= REPORT_NUM_OF_FAILURE:
                    self.result["message"] += f", {i * sample_length}ms"
                elif error_count == REPORT_NUM_OF_FAILURE + 1:
                    self.result[
                        "message"
                    ] += ", ...to many unexpected audio samples detected"

        if error_count == 0:
            self.result[
                "message"
            ] += "No audio sample earlier than random access were rendered."
            self.result["status"] = "PASS"
        else:
            self.result[
                "message"
            ] += f". Total unexpected audio samples detected: {error_count}"
            self.result["status"] = "FAIL"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")

        return self.result, [], []
