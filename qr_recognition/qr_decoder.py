# -*- coding: utf-8 -*-
"""qr decoder base class

stores the detected QR code in string 
this is the base class to inherit other classes
to handle more complex qr code translation

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

logger = logging.getLogger(__name__)


class DecodedQr:
    """Base class for decoded QR codes."""

    data: str
    """ qr code string"""

    location: list
    """qr code location"""

    def __init__(self, data: str, location: list):
        self.data = data
        self.location = location

    def __eq__(self, other) -> bool:
        if isinstance(other, DecodedQr):
            return self.data == other.data


class QrDecoder:
    """Qr decoder - base class"""

    def translate_qr(
        self, data: str, location: list, camera_frame_num: int
    ) -> DecodedQr:
        """Base function for translate_qr"""
        decoded_qr = DecodedQr(data, location)
        return decoded_qr
