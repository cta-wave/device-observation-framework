# -*- coding: utf-8 -*-
"""Observation no_visible_video_shifts

Make observation of no_visible_video_shifts

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

from dpctf_qr_decoder import MezzanineDecodedQr
from global_configurations import GlobalConfigurations
from output_file_handler import write_data_to_csv_file

from .observation import Observation

logger = logging.getLogger(__name__)


class NoVisibleVideoShifts(Observation):
    """[OF] No visible shifts of objects in the video."""

    # max search frames
    max_search_frames: int = 16

    def __init__(self, global_configurations: GlobalConfigurations, name: str = None):
        super().__init__(
            "[OF] No visible shifts of objects in the video, "
            "no visible spatial offset of pixels in the video.",
            global_configurations,
        )
        self.max_search_frames = (
            global_configurations.get_max_search_frames_for_video_shift()
        )

    def _calculate_average_location(self, mezzanine_qr_code: MezzanineDecodedQr):
        """Calculate an average location [left, top, with, height]
        based on sum and qr code count"""
        location_average = [
            round(mezzanine_qr_code.location[x] / mezzanine_qr_code.detection_count, 2)
            for x in range (len(mezzanine_qr_code.location))
        ]
        return location_average

    def _get_batch(self, qr_codes: List[MezzanineDecodedQr]) -> dict:
        """get a qr code in each positions of the mezzanine qr area

        Args:
            qr_codes (List[MezzanineDecodedQr])

        Returns:
            dict: A dictionary where keys are positions and values are QR codes
        """
        positions = {
            "top_left": None,
            "top_right": None,
            "bottom_left": None,
            "bottom_right": None,
        }

        for code in qr_codes:
            position_id = code.frame_number % 4
            if position_id == 1 and not positions["bottom_left"]:
                positions["bottom_left"] = code
            elif position_id == 2 and not positions["bottom_right"]:
                positions["bottom_right"] = code
            elif position_id == 3 and not positions["top_right"]:
                positions["top_right"] = code
            elif position_id == 0 and not positions["top_left"]:
                positions["top_left"] = code

            # break loop if all positions have been found
            if None not in positions.values():
                break

        return positions

    def _all_qr_positions_found(self, batch: dict, direction: str) -> bool:
        """checks if all 4 QR positions are found in the batch

        Args:
            batch (dict): dictionary of QR codes and their positions

        Returns:
            bool: True if all positions are found
        """
        result = True
        failures = []
        for i in batch.keys():
            # checking for batch failures
            if batch[i] is None:
                result = False
                failures.append(i)

        failures_string = " ".join(failures)

        if not result:
            if direction == "forwards":
                self.result[
                    "message"
                ] += f"Cannot find {failures_string} QR code(s) after switch. "
            else:
                self.result[
                    "message"
                ] += f"Cannot find {failures_string} QR code(s) before switch. "

        return result

    def _compare_batches(
        self,
        forward_batch: dict,
        backward_batch: dict,
        tolerance: int,
    ) -> bool:
        """compares two batches of qr codes positions against eachother +/- tolerance

        Args:
            forward_batch (dict): batch after switching point
            backward_batch (dict): batch before switching point
            tolerance (int): shift tolerance

        Returns:
            bool: returns True if not tolerance failures, else False
        """

        for i in backward_batch.keys():
            result = True
            backward_location = self._calculate_average_location(backward_batch[i])
            forward_location = self._calculate_average_location(forward_batch[i])
            self.result["message"] += (
                f"QR code at position {i}: "
                f"backward {backward_location}, forward {forward_location}. "
            )

            # finding the difference of each location value
            # x, y, width, height
            diff_x = abs(backward_location[0] - forward_location[0])
            diff_y = abs(backward_location[1] - forward_location[1])
            diff_w = abs(backward_location[2] - forward_location[2])
            diff_h = abs(backward_location[3] - forward_location[3])

            # checking for tolerance failures
            if diff_x > tolerance or diff_y > tolerance:
                result = False
                self.result[
                    "message"
                ] += f"QR code shifts with difference (x={diff_x},y={diff_y}). "

            if diff_w > tolerance:
                result = False
                self.result[
                    "message"
                ] += f"QR code width resized with difference {diff_w}. "
            if diff_h > tolerance:
                result = False
                self.result[
                    "message"
                ] += f"QR code height resized with difference {diff_h}. "

            if result:
                self.result["message"] += "QR code positions match. "

        return result

    def make_observation(
        self,
        _test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        _audio_segments,
        _test_status_qr_codes,
        parameters_dict: dict,
        _observation_data_export_file,
    ) -> Tuple[Dict[str, str], list, list]:
        """
        make_observation for video only observation

        Args:
            _test_type
            mezzanine_qr_codes: lists of MezzanineDecodedQr
            _audio_segments
            _test_status_qr_codes
            _test_status_qr_codes
            parameters_dict: parameter dictionary
            _observation_data_export_file

        Returns:
            Dict[str, str]: observation result
        """

        logger.info(f"Making observation {self.result['name']}...")

        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = (
                f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            )
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result, [], []

        switching_points = Observation.get_playback_change_position(mezzanine_qr_codes)
        shift_tolerance = parameters_dict["video_shifts_tolerance"]
        self.result["message"] += f"Video shifts tolerance is {shift_tolerance} pixel. "

        for switching_point in switching_points:
            if switching_point == 0:
                continue

            # get qr codes on both sides of switching point
            # we only want to go back to number_of_qr_codes (defined in config.ini)
            backwards_qr_codes = mezzanine_qr_codes[
                switching_point - self.max_search_frames :: switching_point
            ]
            forwards_qr_codes = mezzanine_qr_codes[
                switching_point :: switching_point + self.max_search_frames
            ]

            # search for four different qr code positions
            backwards_batch = self._get_batch(backwards_qr_codes)
            forwards_batch = self._get_batch(forwards_qr_codes)

            self.result[
                "message"
            ] += f"At switching point {switching_points.index(switching_point)}: "

            forwards_batch_check = self._all_qr_positions_found(
                forwards_batch, "forwards"
            )
            backwards_batch_check = self._all_qr_positions_found(
                backwards_batch, "backwards"
            )

            if forwards_batch_check and backwards_batch_check:
                if not self._compare_batches(
                    backwards_batch, forwards_batch, shift_tolerance
                ):
                    self.result["status"] = "FAIL"
            else:
                # if not all 4 qr codes found on each side not comparing qr code positions
                self.result["status"] = "FAIL"

        if self.result["status"] != "FAIL":
            self.result["status"] = "PASS"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")
        return self.result, [], []
