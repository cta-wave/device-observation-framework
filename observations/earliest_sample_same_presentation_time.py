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
Contributor: Eurofins Digital Product Testing UK Limited
"""
import logging
from .sample_matches_current_time import SampleMatchesCurrentTime
from typing import List, Dict
from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr

logger = logging.getLogger(__name__)


class EarliestSampleSamePresentationTime(SampleMatchesCurrentTime):
    """EarliestSampleSamePresentationTime class
    N.B. Video only for phase one
    The presentation starts with the earliest video sample and the audio sample that corresponds to the same
    presentation time.
    """

    def __init__(self, _):
        super().__init__(
            None,
            "[OF] Video only: The presentation starts with the earliest video sample and the audio sample "
            "that corresponds to the same presentation time.",
        )

    def make_observation(
        self,
        _unused,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
        _unused2,
    ) -> Dict[str, str]:
        """Observation is derived from SampleMatchesCurrentTime and uses the same observations logic
        But it checks for the 1st event only.
        """
        logger.info(f"Making observation {self.result['name']}...")

        if not mezzanine_qr_codes:
            self.result["status"] = "FAIL"
            self.result["message"] = f"No QR mezzanine code detected."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result

        camera_frame_rate = parameters_dict["camera_frame_rate"]
        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]
        allowed_tolerance = parameters_dict["tolerance"]
        self.result["message"] += f"Allowed tolerance is {allowed_tolerance}."

        for i in range(0, len(test_status_qr_codes)):
            current_status = test_status_qr_codes[i]
            if (
                current_status.status == "playing"
                and current_status.last_action == "play"
            ):

                if i + 1 < len(test_status_qr_codes):
                    first_possible, last_possible = self._get_target_camera_frame_num(
                        current_status.camera_frame_num,
                        test_status_qr_codes[i + 1].delay,
                        camera_frame_duration_ms,
                        camera_frame_rate,
                        mezzanine_qr_codes,
                    )
                    diff_found, time_diff = self._find_diff_within_tolerance(
                        mezzanine_qr_codes,
                        current_status,
                        first_possible,
                        last_possible,
                        allowed_tolerance,
                    )
                    if not diff_found:
                        self.result["status"] = "FAIL"
                        self.result["message"] += (
                            " Time difference between first Test Runner reported media currentTime and actual media "
                            "time exceeded tolerance for following event:"
                            f" currentTime={current_status.current_time} time_diff={round(time_diff, 4)}."
                        )
                break

        if self.result["status"] != "FAIL":
            self.result["status"] = "PASS"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")
        return self.result
