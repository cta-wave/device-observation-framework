# -*- coding: utf-8 -*-
"""qr recognision

contains fucntions to extract QR codes from a video frame.

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
import cv2
import logging
import numpy as np

from typing import Any, List
from pyzbar.pyzbar import decode, ZBarSymbol, Decoded
from .qr_decoder import DecodedQr, QrDecoder


logger = logging.getLogger(__name__)


OpenCvImageHint = Any
"""Type hint for an OpenCV image"""

QR_CODE_NUM_IN_FRAME = 2
"""Number of QR code suposed to be detected in a frame"""

THRESHOLD_VALUE = 127
"""Threshold value for thresholding image"""


def decode_qrs_in_image(image: OpenCvImageHint, decoder: QrDecoder, camera_frame_num: int) -> List[DecodedQr]:
    """Given an image, do a basic QR code recognition pass using pyzbar.
    """
    results = []

    for qr in decode(image, symbols=[ZBarSymbol.QRCODE]):
        data = qr.data.decode("ISO-8859-1")
        code = decoder.translate_qr(data, camera_frame_num)
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

    def __init__(
        self,
        capture_frame_num: int,
        decoder: QrDecoder
    ):
        self.capture_frame_num = capture_frame_num
        self.decoder = decoder
        self.qr_codes = []


    def add_code(self, code: DecodedQr) -> None:
        """Add a QR code to the list.
        """
        for qr_code in self.qr_codes:
            if qr_code == code:
                return
        self.qr_codes.append(code)


    def all_codes(self) -> List[DecodedQr]:
        """Get a list of all found QR codes.
        """
        return self.qr_codes


    def _scan_image(self, image: OpenCvImageHint) -> bool:
        """Do a basic initial scan for QR codes in the image.
        """
        number_of_qr = 0
        for code in decode_qrs_in_image(image, self.decoder, self.capture_frame_num):
            self.add_code(code)
            number_of_qr +=1
        
        if number_of_qr < QR_CODE_NUM_IN_FRAME:
            return False
        else:
            return True


    def scan_all(
        self,
        webcam_image: OpenCvImageHint
    ) -> None:
        """Do a full scan of the specified webcam capture video frame.
        """

        image = cv2.cvtColor(webcam_image, cv2.COLOR_BGR2GRAY)
        np.bitwise_not(image, out=image)
        qr_found = self._scan_image(image)
        
        if not qr_found:
            _, thresholded_image = cv2.threshold(
                image, THRESHOLD_VALUE, 255, cv2.THRESH_BINARY
            )
            qr_found = self._scan_image(thresholded_image)

        if not qr_found:
            _, thresholded_image2 = cv2.threshold(
                image, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU
            )
            self._scan_image(thresholded_image2)