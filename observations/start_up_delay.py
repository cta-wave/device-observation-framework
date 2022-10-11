# -*- coding: utf-8 -*-
"""Observation start_up_delay

Make observation of start_up_delay

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
from typing import Dict, List

from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr

from .observation import Observation

logger = logging.getLogger(__name__)


class StartUpDelay(Observation):
    """StartUpDelay class
    The start-up delay should be sufficiently low, i.e., TR [k, 1] - Ti < TSMax..
    """

    def __init__(self, _):
        super().__init__(
            "[OF] The start-up delay should be sufficiently low, i.e., TR [k, 1] - Ti < TSMax."
        )

    def make_observation(
        self,
        _unused,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
        _unused2,
    ) -> Dict[str, str]:
        """Implements the logic:
        start_up_delay = (QRa.first_camera_frame_num * camera_frame_duration_ms)
            - ((play_event.camera_frame_num * camera_frame_duration_ms) - d)
        start_up_delay < TSMax

        Args:
            _unused:
            mezzanine_qr_codes: detected QR codes list from Mezzanine
            test_status_qr_codes: detected QR codes list from test runner
            parameters_dict: parameters are from test runner config file and some are generated from OF

        Returns:
            Result status and message.
        """
        logger.info(f"Making observation {self.result['name']}...")

        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "FAIL"
            self.result[
                "message"
            ] = f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result

        max_permitted_startup_delay_ms = parameters_dict["ts_max"]
        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]

        event_found, play_ct = Observation._get_play_event(
            test_status_qr_codes, camera_frame_duration_ms
        )

        frame_change_found = False
        for mezzanine_qr_code in mezzanine_qr_codes:
            frame_ct = (
                mezzanine_qr_code.first_camera_frame_num * camera_frame_duration_ms
            )
            if frame_ct > play_ct:
                frame_change_found = True
                break

        if not event_found:
            self.result["status"] = "FAIL"
            self.result["message"] = (
                f"A test status QR code with first 'play' last_action "
                f"followed by a further test status QR code was not found."
            )
        elif not frame_change_found:
            self.result["status"] = "FAIL"
            self.result["message"] = f"No frame change detected after 'play'."
        else:
            start_up_delay = frame_ct - play_ct
            self.result["message"] = (
                f"Maximum permitted startup delay is {max_permitted_startup_delay_ms}ms."
                f"The presentation start up delay is {round(start_up_delay, 4)}ms"
            )

            if start_up_delay < max_permitted_startup_delay_ms:
                self.result["status"] = "PASS"
            else:
                self.result["status"] = "FAIL"

        logger.debug(f"[{self.result['status']}] {self.result['message']}")
        return self.result
