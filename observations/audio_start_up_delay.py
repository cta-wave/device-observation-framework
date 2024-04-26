# -*- coding: utf-8 -*-
# pylint: disable=import-error
"""Observation audio_start_up_delay

Make observation of audio_start_up_delay

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
from dpctf_qr_decoder import TestStatusDecodedQr

from .observation import Observation

logger = logging.getLogger(__name__)


class AudioStartUpDelay(Observation):
    """StartUpDelay class
    The start-up delay should be sufficiently low, i.e., TR [k, 1] - Ti < TSMax..
    """

    def __init__(self, _):
        super().__init__(
            "[OF] Audio start-up-delay: The start-up delay shall be sufficiently low."
        )

    def make_observation(
        self,
        _test_type,
        _mezzanine_qr_codes,
        audio_segments: List[AudioSegment],
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list]:
        """make observation

        Args:
            test_type: defined in test.py
            mezzanine_qr_codes: detected QR codes list from Mezzanine
            test_status_qr_codes: detected QR codes list from test runner
            parameters_dict: parameters are from test runner config file
            and some are generated from OF

        Returns:
            Result status and message.
        """
        logger.info(f"Making observation {self.result['name']}...")

        if not audio_segments:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = "No audio segment is detected."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result, []

        # Get time when test status = play
        event_found, event_ct = Observation._find_event(
            "play", test_status_qr_codes, parameters_dict["camera_frame_duration_ms"]
        )
        # get relative event current time to test start time
        event_ct -= parameters_dict["test_start_time"]
        max_permitted_startup_delay = parameters_dict["ts_max"]

        if not event_found:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = (
                "A test status QR code with first 'play' last_action "
                "followed by a further test status QR code was not found."
            )
        else:
            start_up_delay = audio_segments[0].audio_segment_timing - event_ct
            self.result["message"] = (
                f"Maximum permitted startup delay is {max_permitted_startup_delay}ms."
                f"The presentation start up delay is {round(start_up_delay, 4)}ms"
            )

            if start_up_delay < max_permitted_startup_delay:
                self.result["status"] = "PASS"
            else:
                self.result["status"] = "FAIL"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")
        return self.result, []
