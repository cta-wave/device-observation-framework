"""Observation rendering_delay_within_threshold

Make observation of rendering

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
from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr
from global_configurations import GlobalConfigurations
from .observation import Observation

FIRST_FRAME_APPLIED_EVENT = "appended"


class RenderingDelayWithinThreshold(Observation):
    """RenderingDelayWithinThreshold class
    The rendering delay is the time between successful appending of the first
    CMAF fragment and the first media sample is visible or audible .
    """

    def __init__(self, global_configurations: GlobalConfigurations):
        super().__init__(
            "[OF] Measure the time between the successful appending of the first CMAF chunk that exceeded "
            "min_buffer_duration and the first media sample being visible or audible. "
            "This value shall be compared against render_threshold.",
            global_configurations,
        )

    @staticmethod
    def _get_frame_applied_event(
        test_status_qr_codes: List[TestStatusDecodedQr], camera_frame_duration_ms: float
    ) -> Tuple[bool, float]:
        """loop through event qr code to find 1st FIRST_FRAME_APPLIED_EVENT event

        Args:
            test_status_qr_codes (List[TestStatusDecodedQr]): Test Status QR codes list containing
                currentTime as reported by MSE.
            camera_frame_duration_ms (float): duration of a camera frame on milliseconds.

        Returns:
            (bool, float): True if the 1st FIRST_FRAME_APPLIED_EVENT is found
            event_current_time: current time of the 1st test runner FIRST_FRAME_APPLIED_EVENT event.
        """
        for i in range(0, len(test_status_qr_codes)):
            current_status = test_status_qr_codes[i]
            # check for the 1st "appended" action from TR events
            if current_status.status == FIRST_FRAME_APPLIED_EVENT:
                event_camera_frame_num = current_status.camera_frame_num
                if i + 1 < len(test_status_qr_codes):
                    next_status = test_status_qr_codes[i + 1]
                    previous_qr_generation_delay = next_status.delay
                    event_current_time = (
                        event_camera_frame_num * camera_frame_duration_ms
                    ) - previous_qr_generation_delay
                    return True, event_current_time
                break

        return False, 0

    def make_observation(
        self,
        _test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        _audio_segments,
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list, list]:
        """Implements the logic:
        render_delay = (QRa.first_camera_frame_num * camera_frame_duration_ms)
            - ((event.camera_frame_num * camera_frame_duration_ms) - d)
        render_delay < render_threshold

        Args:
            _unused:
            mezzanine_qr_codes: detected QR codes list from Mezzanine
            test_status_qr_codes: detected QR codes list from test runner
            parameters_dict: parameters are from test runner config file
            and some are generated from OF

        Returns:
            Result status and message.
        """
        self.logger.info("Making observation %s.", self.result["name"])
        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = (
                f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            )
            self.logger.info("[%s] %s", self.result["status"], self.result["message"])
            return self.result, [], []

        render_threshold = parameters_dict["render_threshold"]
        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]

        event_found, event_ct = RenderingDelayWithinThreshold._get_frame_applied_event(
            test_status_qr_codes, camera_frame_duration_ms
        )

        first_mezzanine_frame_time = (
            mezzanine_qr_codes[0].first_camera_frame_num * camera_frame_duration_ms
        )
        if not event_found:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = (
                f"'{FIRST_FRAME_APPLIED_EVENT}' event was not found."
            )
        else:
            render_delay = first_mezzanine_frame_time - event_ct
            self.result["message"] = (
                f"Maximum permitted rendering delay is render_threshold={render_threshold}ms."
                f"The presentation rendering delay is {round(render_delay, 4)}ms"
            )
            if render_delay < render_threshold:
                self.result["status"] = "PASS"
            elif render_delay < 0:
                self.result["status"] = "FAIL"
                self.result["message"] = f"{render_delay} is negative"
            else:
                self.result["status"] = "FAIL"

        self.logger.debug("[%s] %s", self.result["status"], self.result["message"])
        return self.result, [], []
