# -*- coding: utf-8 -*-
"""observation earliest_sample_same_presentation_time

make observation of earliest_sample_same_presentation_time

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
from typing import Dict, List, Tuple

from dpctf_audio_decoder import AudioSegment
from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr
from global_configurations import GlobalConfigurations

from .observation import Observation


class EarliestSampleSamePresentationTime(Observation):
    """EarliestSampleSamePresentationTime class
    The WAVE presentation starts with the earliest video and audio sample that
    corresponds to the same presentation time as the earliest video sample.
    """

    def __init__(self, global_configurations: GlobalConfigurations):
        super().__init__(
            "[OF] The WAVE presentation starts with the earliest video and audio sample that"
            " corresponds to the same presentation time as the earliest video sample.",
            global_configurations,
        )

    def make_observation(
        self,
        _test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        audio_segments: List[AudioSegment],
        _test_status_qr_codes: List[TestStatusDecodedQr],
        _parameters_dict: dict,
        _observation_data_export_file: str,
    ) -> Tuple[Dict[str, str], list, list]:
        """
        Check The WAVE presentation starts with the earliest video and audio sample that
        corresponds to the same presentation time as the earliest video sample.
        """
        self.logger.info("Making observation %s.", self.result["name"])

        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = (
                f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            )
            self.logger.info("[%s] %s", self.result["status"], self.result["message"])
            return self.result, [], []

        # check audio when pass the video check
        if not audio_segments:
            self.result["status"] = "NOT_RUN"
            self.result["message"] += " No audio segment is detected."
            self.logger.info("[%s] %s", self.result["status"], self.result["message"])
            return self.result, [], []

        earliest_sample_alignment_tolerance = self.tolerances[
            "earliest_sample_alignment_tolerance"
        ]
        self.result["message"] += (
            f"The earliest video and audio sample alignment tolerance is "
            f"{earliest_sample_alignment_tolerance} ms. "
        )

        video_frame_duration = round(1000 / mezzanine_qr_codes[0].frame_rate)
        earliest_video_media_time = (
            mezzanine_qr_codes[0].media_time - video_frame_duration
        )
        earliest_audio_media_time = audio_segments[0].media_time
        diff = abs(earliest_video_media_time - earliest_audio_media_time)

        if diff > earliest_sample_alignment_tolerance:
            self.result["status"] = "FAIL"
        else:
            self.result["status"] = "PASS"
        self.result["message"] += (
            f"The earliest video sample presentation time is {earliest_video_media_time} ms while "
            f"the earliest audio sample presentation time is {earliest_audio_media_time} ms. There "
            f"is a {diff} ms time difference between video and audio sample presentation times."
        )

        self.logger.debug("[%s] %s", self.result["status"], self.result["message"])
        return self.result, [], []
