# -*- coding: utf-8 -*-
# pylint: disable=import-error
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
Contributor: Resillion UK Limited
"""
from typing import Dict, List, Tuple

from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr
from test_code.test import TestType
from global_configurations import GlobalConfigurations

from .observation import Observation


class StartUpDelay(Observation):
    """StartUpDelay class
    The start-up delay should be sufficiently low, i.e., TR [k, 1] - Ti < TSMax..
    """

    def __init__(self, global_configurations: GlobalConfigurations):
        super().__init__(
            "[OF] Video start-up delay: The start-up delay should be sufficiently low.",
            global_configurations,
        )

    def _get_additional_tolerance(self, parameters_dict: dict) -> float:
        """Get additional tolerance for random_access_time test"""
        additional_tolerance = 0
        if "random_access_time" in parameters_dict:
            random_access_to_time = parameters_dict["random_access_time"] * 1000
            for i in range(0, len(parameters_dict["video_fragment_durations"]) - 1):
                random_access_to_time -= parameters_dict["video_fragment_durations"][i]
                if (
                    random_access_to_time
                    < parameters_dict["video_fragment_durations"][i + 1]
                ):
                    break
            additional_tolerance = random_access_to_time
        return additional_tolerance

    def make_observation(
        self,
        test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        _audio_segments,
        test_status_qr_codes: List[TestStatusDecodedQr],
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list, list]:
        """Implements the logic:
        start_up_delay = (QRa.first_camera_frame_num * camera_frame_duration_ms)
            - ((play_event.camera_frame_num * camera_frame_duration_ms) - d)
        start_up_delay < TSMax

        Args:
            test_type: defined in test.py
            mezzanine_qr_codes: detected QR codes list from Mezzanine
            test_status_qr_codes: detected QR codes list from test runner
            parameters_dict: parameters are from test runner config file
            and some are generated from OF

        Returns:
            Result status and message.
        """
        self.logger.info("Making observation %s.", self.result["name"])
        if test_type == TestType.TRUNCATED:
            self.result["name"] = (
                "[OF] Video start-up delay: "
                "The delay between 'representation_change' and presenting "
                "the first frame of the second presentation should be sufficiently low."
            )

        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = (
                f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            )
            self.logger.info("[%s] %s", self.result["status"], self.result["message"])
            return self.result, [], []

        max_permitted_startup_delay_ms = parameters_dict[
            "ts_max"
        ] + self._get_additional_tolerance(parameters_dict)
        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]

        if test_type == TestType.TRUNCATED:
            # check presentation changes twice
            content_starting_index_list = Observation.get_content_change_position(
                mezzanine_qr_codes
            )
            if len(content_starting_index_list) != 2:
                self.result["status"] = "FAIL"
                self.result["message"] += (
                    f" Truncated test should change presentation once. "
                    f"Actual presentation change is {len(content_starting_index_list) - 1}."
                )
                return self.result, [], []

            # only check the 2nd presentation start up delay
            mezzanine_qr_codes = mezzanine_qr_codes[content_starting_index_list[1] :]
            event = "representation_change"
        else:
            event = "play"

        event_found, event_ct = Observation.find_event(
            event, test_status_qr_codes, camera_frame_duration_ms
        )

        frame_change_found = False
        for mezzanine_qr_code in mezzanine_qr_codes:
            frame_ct = (
                mezzanine_qr_code.first_camera_frame_num * camera_frame_duration_ms
            )
            if frame_ct > event_ct:
                frame_change_found = True
                break

        if not event_found:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = (
                f"A test status QR code with first '{event}' last_action "
                "followed by a further test status QR code was not found."
            )
        elif not frame_change_found:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = f"No frame change detected after '{event}'."
        else:
            start_up_delay = frame_ct - event_ct
            self.result["message"] = (
                f"Maximum permitted startup delay is {max_permitted_startup_delay_ms}ms. "
                f"The presentation start up delay is {round(start_up_delay, 4)}ms."
            )

            if start_up_delay < max_permitted_startup_delay_ms:
                self.result["status"] = "PASS"
            else:
                self.result["status"] = "FAIL"

        self.logger.debug("[%s] %s", self.result["status"], self.result["message"])
        return self.result, [], []
