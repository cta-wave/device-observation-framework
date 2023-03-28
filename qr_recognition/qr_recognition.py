# -*- coding: utf-8 -*-
"""qr recognision

contains functions to extract QR codes from a video frame.

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
from typing import Any, List

import cv2
import numpy as np
from pyzbar.pyzbar import ZBarSymbol, decode

from .qr_decoder import DecodedQr, QrDecoder

logger = logging.getLogger(__name__)


OpenCvImageHint = Any
"""Type hint for an OpenCV image"""

MAX_QR_CODE_NUM_IN_FRAME = 3
"""Maximum number of QR code can be detected in a frame"""


def decode_qrs_in_image(
    image: OpenCvImageHint, decoder: QrDecoder, camera_frame_num: int
) -> List[DecodedQr]:
    """Given an image, do a basic QR code recognition pass using pyzbar."""
    results = []

    for qr in decode(image, symbols=[ZBarSymbol.QRCODE]):
        data = qr.data.decode("ISO-8859-1")
        code = decoder.translate_qr(data, qr.rect, camera_frame_num)
        if code is not None:
            results.append(code)
    return results


class FrameAnalysis:
    """Extract QR codes from a video frame.

    Normal usage: scan_all() to scan the image, then call all_codes() to get
    the QR codes.
    """

    capture_frame_num: int
    """Frame number - 0 for first captured frame, goes up by 1 each frame."""
    decoder: QrDecoder
    """decoder - suitable decoder will be selected when creating FrameAnalysis."""

    def __init__(self, capture_frame_num: int, decoder: QrDecoder):
        self.capture_frame_num = capture_frame_num
        self.decoder = decoder
        self.qr_codes = []

    def add_code(self, code: DecodedQr) -> None:
        """Add a QR code to the list."""
        for qr_code in self.qr_codes:
            if qr_code == code:
                return
        self.qr_codes.append(code)

    def all_codes(self) -> List[DecodedQr]:
        """Get a list of all found QR codes."""
        return self.qr_codes

    def all_code_found(self) -> bool:
        """Check all QR codes are found."""
        if len(self.qr_codes) < MAX_QR_CODE_NUM_IN_FRAME:
            return False
        else:
            return True

    def _scan_image(self, image: OpenCvImageHint) -> None:
        """Do a basic initial scan for QR codes in the image."""
        for code in decode_qrs_in_image(image, self.decoder, self.capture_frame_num):
            self.add_code(code)

    def scan_cropped_image(self, image: OpenCvImageHint, qr_code_area: list):
        """scan cropped area"""
        crop = image[
            qr_code_area[1] : qr_code_area[3], qr_code_area[0] : qr_code_area[2]
        ]
        self._scan_image(crop)

    def full_scan(
        self,
        webcam_image: OpenCvImageHint,
        qr_code_areas: list,
        do_adaptive_threshold_scan: bool,
    ) -> None:
        """Do a full scan of the specified webcam capture video frame."""
        image = cv2.cvtColor(webcam_image, cv2.COLOR_BGR2GRAY)
        np.bitwise_not(image, out=image)
        self._scan_image(image)

        if not self.all_code_found():
            if qr_code_areas:
                if isinstance(qr_code_areas[0], list):
                    for qr_code_area in qr_code_areas:
                        self.scan_cropped_image(image, qr_code_area)
                else:
                    self.scan_cropped_image(image, qr_code_areas)

        # do adaptiveThreshold scan when it is defined to do so
        if do_adaptive_threshold_scan and not self.all_code_found():
            thresholded_image = cv2.adaptiveThreshold(
                image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            self._scan_image(thresholded_image)
