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

from .observation import Observation
from typing import List, Dict
from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr


logger = logging.getLogger(__name__)


class StartUpDelay(Observation):
    """StartUpDelay class
    The start-up delay should be sufficiently low, i.e., TR [k, 1] - Ti < TSMax..
    """

    def __init__(self, _):
        super().__init__(
            "[OF] The start-up delay should be sufficiently low, i.e., TR [k, 1] - Ti < TSMax."
        )

    @staticmethod
    def _get_play_event(
        test_status_qr_codes: List[TestStatusDecodedQr],
        camera_frame_duration_ms: float,
    ) -> (bool, float):
        """loop through event qr code to find 1st playing play event

        Args:
            test_status_qr_codes (List[TestStatusDecodedQr]): Test Status QR codes list containing
                currentTime as reported by MSE.
            camera_frame_duration_ms (float): duration of a camera frame on msecs.

        Returns:
            (bool, float): True if the 1st play event is found, play_current_time from the 1st test runner play event.
        """
        for i in range(0, len(test_status_qr_codes)):
            current_status = test_status_qr_codes[i]

            # check for the 1st play action from TR events
            if current_status.last_action == "play":
                play_event_camera_frame_num = current_status.camera_frame_num

                if i + 1 < len(test_status_qr_codes):
                    next_status = test_status_qr_codes[i + 1]
                    previous_qr_generation_delay = next_status.delay
                    play_current_time = (
                        play_event_camera_frame_num * camera_frame_duration_ms
                    ) - previous_qr_generation_delay
                    return True, play_current_time
                break

        return False, 0

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
        first_frame_current_time = (
            mezzanine_qr_codes[1].first_camera_frame_num * camera_frame_duration_ms
            - float(1000 / mezzanine_qr_codes[0].frame_rate)
        )

        event_found, play_current_time = self._get_play_event(
            test_status_qr_codes, camera_frame_duration_ms
        )
        if not event_found:
            self.result["status"] = "FAIL"
            self.result["message"] = (
                f"A test status QR code with first 'play' last_action "
                f"followed by a further test status QR code was not found."
            )
        else:
            start_up_delay = first_frame_current_time - play_current_time
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
