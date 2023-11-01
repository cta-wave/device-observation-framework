# -*- coding: utf-8 -*-
# pylint: disable=import-error,logging-fstring-interpolation
"""Observation UnexpectSampleNotRendered

Make observation of unexpected_sample_not_rendered

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

from dpctf_qr_decoder import MezzanineDecodedQr
from global_configurations import GlobalConfigurations
from .observation import Observation

logger = logging.getLogger(__name__)
REPORT_NUM_OF_FAILURE = 10

class UnexpectSampleNotRendered(Observation):
    """UnexpectSampleNotRendered class
    No sample earlier than random_access_fragment shall be rendered.
    """

    def __init__(self, global_configurations: GlobalConfigurations, name: str = None):
        name = (
            "[OF] No video sample earlier than random access shall be rendered."
        )
        super().__init__(name, global_configurations)

    def make_observation(
        self,
        _test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        _audio_segments,
        _test_status_qr_codes,
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list]:
        """
        Args:
            _unused
            mezzanine_qr_codes: lists of MezzanineDecodedQr
            _unused1
            _unused2
            parameters_dict: parameter dictionary
            _unused3

        Returns:
            Dict[str, str]: observation result
        """
        logger.info("Making observation %s...", self.result["name"])

        if not mezzanine_qr_codes:
            self.result["status"] = "PASS"
            self.result["message"] += "No unexpected frames were rendered."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result, []

        first_frame_num = parameters_dict["first_frame_num"]
        unexpected_frame_counter = 0
        for mezzanine_qr_code in mezzanine_qr_codes:
            current_frame = mezzanine_qr_code.frame_number
            if current_frame < first_frame_num:
                unexpected_frame_counter += 1
                if unexpected_frame_counter == 1:
                    self.result["message"] += "Following unexpected frames rendered: "
                if unexpected_frame_counter < REPORT_NUM_OF_FAILURE:
                    self.result["message"] += f"{current_frame} "

        if unexpected_frame_counter == 0:
            self.result["status"] = "PASS"
            self.result[
                "message"
            ] += "No unexpected frames were rendered."
        else:
            self.result["status"] = "FAIL"
            if unexpected_frame_counter >= REPORT_NUM_OF_FAILURE:
                self.result["message"] += "... too many unexpected frames detected"
            self.result[
                "message"
            ] += f"Total unexpected frames rendered: {unexpected_frame_counter}"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")
        return self.result, []
