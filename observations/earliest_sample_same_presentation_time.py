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
import logging
import sys
from typing import Dict, List, Tuple

from dpctf_audio_decoder import AudioSegment
from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr

from .observation import Observation

logger = logging.getLogger(__name__)


class EarliestSampleSamePresentationTime(Observation):
    """EarliestSampleSamePresentationTime class
    The WAVE presentation starts with the earliest video and audio sample that
    corresponds to the same presentation time as the earliest video sample.
    """

    def __init__(self, _):
        super().__init__(
            "[OF] The WAVE presentation starts with the earliest video and audio sample that"
            " corresponds to the same presentation time as the earliest video sample."
        )

    def make_observation(
        self,
        _test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        audio_segments: List[AudioSegment],
        test_status_qr_codes: List[TestStatusDecodedQr],
        _parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list, list]:
        """Observation is derived from SampleMatchesCurrentTime and uses the same observations logic
        But it checks for the 1st event only.
        """
        logger.info(f"Making observation {self.result['name']}...")

        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = (
                f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            )
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result, [], []

        # Compare video presentation time with HTML reported presentation time
        starting_ct = None
        for i in range(0, len(test_status_qr_codes)):
            current_status = test_status_qr_codes[i]
            if current_status.status == "playing" and (
                current_status.last_action == "play"
                or current_status.last_action == "representation_change"
            ):
                starting_ct = current_status.current_time * 1000
                break

        if starting_ct == None:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = f"HTML starting presentation time is not found."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result, [], []

        video_result = False
        video_frame_duration = round(1000 / mezzanine_qr_codes[0].frame_rate)
        earliest_video_media_time = (
            mezzanine_qr_codes[0].media_time - video_frame_duration
        )
        if earliest_video_media_time == starting_ct:
            video_result = True
        else:
            self.result["status"] = "FAIL"
            video_result = False
        self.result["message"] += (
            f"Earliest video sample presentation time is {earliest_video_media_time} ms,"
            f" expected starting presentation time is {starting_ct} ms."
        )

        if video_result:
            # check audio when pass the video check
            if not audio_segments:
                self.result["status"] = "NOT_RUN"
                self.result["message"] += " No audio segment is detected."
                logger.info(f"[{self.result['status']}] {self.result['message']}")
                return self.result, [], []

            earliest_audio_media_time = audio_segments[0].media_time

            if earliest_video_media_time == earliest_audio_media_time:
                self.result["status"] = "PASS"
            else:
                self.result["status"] = "FAIL"
            self.result[
                "message"
            ] += f" Earliest audio sample presentation time is {earliest_audio_media_time} ms."

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")
        return self.result, [], []
