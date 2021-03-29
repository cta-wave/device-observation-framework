# -*- coding: utf-8 -*-
"""observation every_sample_rendered

make observation of every_sample_rendered

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
Licensor: Eurofins Digital Product Testing UK Limited
"""
import logging

from typing import List, Dict
from dpctf_qr_decoder import MezzanineDecodedQr
from global_configurations import GlobalConfigurations

logger = logging.getLogger(__name__)

REPORT_NUM_OF_MISSING_FRAME = 50


class EverySampleRendered:
    """EverySampleRendered class
    Every sample S[k,s] shall be rendered and the samples shall be rendered in increasing presentation time order.
    """

    result: Dict[str, str]
    tolerances: Dict[str, int]

    def __init__(self, global_configurations: GlobalConfigurations):
        self.result = {
            "status": "NOT_RUN",
            "message": "",
            "name": "[OF] Every sample S[k,s] shall be rendered and the samples shall be rendered in "
            "increasing presentation time order.",
        }
        self.tolerances = global_configurations.get_tolerances()

    def _check_first_frame(
        self, first_frame_num: int, first_qr_code: MezzanineDecodedQr
    ) -> bool:
        """Check 1st expected frame is present,
        except a start_frame_num_tolerance of missing frames is allowed.

        Args:
            first_frame_num: expected frame number of the first frame
            first_qr_code: first MezzanineDecodedQr from MezzanineDecodedQr lists

        Returns:
            bool: True if the 1st is present.
        """
        result = True
        start_frame_num_tolerance = self.tolerances["start_frame_num_tolerance"]
        if abs(first_qr_code.frame_number - first_frame_num) > start_frame_num_tolerance:
            result = False
            self.result["message"] += " [FAIL]:"

        self.result["message"] += (
            f" First frame found is {first_qr_code.frame_number}, "
            f"expected to start from {first_frame_num}."
            f" First frame number tolerance is {start_frame_num_tolerance}."
        )
        return result

    def _check_last_frame(
        self, last_frame_num: int, last_qr_code: MezzanineDecodedQr
    ) -> bool:
        """Check 1st expected frame is present,
        except an end_frame_num_tolerance of missing frames is allowed.

        Args:
            last_frame_num: expected frame number of the last frame
            last_qr_code: last  MezzanineDecodedQr from MezzanineDecodedQr lists

        Returns:
            bool: True if the last is present.
        """
        result = True
        end_frame_num_tolerance = self.tolerances["end_frame_num_tolerance"]
        if abs(last_frame_num - last_qr_code.frame_number) > end_frame_num_tolerance:
            result = False
            self.result["message"] += " [FAIL]:"

        self.result["message"] += (
            f" Last frame found is {last_qr_code.frame_number}, "
            f"expected to end at {last_frame_num}."
            f" Last frame number tolerance is {end_frame_num_tolerance}."
        )
        return result

    def _check_every_frame(self, mezzanine_qr_codes: List[MezzanineDecodedQr]) -> bool:
        """Check all intervening frames. All frames must be present and in ascending order,
        except a mid_frame_num_tolerance of missing frames is allowed.

        Args:
            mezzanine_qr_codes: lists of MezzanineDecodedQr

        Returns:
            bool: True if all the mid frames are present
        """
        check = True
        missing_frame_count = 0
        mid_frame_num_tolerance = self.tolerances["mid_frame_num_tolerance"]
        self.result[
            "message"
        ] += f" Mid frame number tolerance is {mid_frame_num_tolerance}."

        for i in range(1, len(mezzanine_qr_codes)):
            if (
                mezzanine_qr_codes[i - 1].frame_number + 1
                != mezzanine_qr_codes[i].frame_number
            ):
                check = False
                previous_frame = mezzanine_qr_codes[i - 1].frame_number
                current_frame = mezzanine_qr_codes[i].frame_number
                for frame in range(previous_frame, current_frame - 1):
                    if missing_frame_count < REPORT_NUM_OF_MISSING_FRAME:
                        self.result["message"] += f" Frame {frame + 1} is missing."
                missing_frame_count += current_frame - previous_frame - 1

        if missing_frame_count >= REPORT_NUM_OF_MISSING_FRAME:
            self.result["message"] += (
                f"... too many missing frames, reporting truncated. "
                f"Total of missing frames is {missing_frame_count}."
            )

        if missing_frame_count <= mid_frame_num_tolerance:
            check = True

        return check

    def make_observation(
        self, mezzanine_qr_codes: List[MezzanineDecodedQr], _, parameters_dict: dict
    ) -> Dict[str, str]:
        """
        check 1st frame is present
        QRa.mezzanine_frame_num == first_frame_num

        check the last frame is present
        QRn.mezzanine_frame_num == round(cmaf_track_duration * mezzanine_frame_rate)

        check that the samples shall be rendered in increasing order:
        for QRb to QRn: QR[i-1].mezzanine_frame_num + 1 == QR[i].mezzanine_frame_num
        """
        logger.info(f"Making observation {self.result['name']}...")

        if len(mezzanine_qr_codes) < 2:
            self.result["status"] = "FAIL"
            self.result[
                "message"
            ] = f"Too few mezzanine QR codes detected ({len(mezzanine_qr_codes)})."
            logger.info(f"[{self.result['status']}] {self.result['message']}")
            return self.result

        first_frame_result = self._check_first_frame(
            parameters_dict["first_frame_num"], mezzanine_qr_codes[0]
        )
        last_frame_result = self._check_last_frame(
            parameters_dict["last_frame_num"], mezzanine_qr_codes[-1]
        )
        every_frame_result = self._check_every_frame(mezzanine_qr_codes)

        if first_frame_result and last_frame_result and every_frame_result:
            self.result["status"] = "PASS"
        else:
            self.result["status"] = "FAIL"

        logger.debug(f"[{self.result['status']}]: {self.result['message']}")
        return self.result
