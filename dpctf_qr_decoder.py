# -*- coding: utf-8 -*-
"""WAVE DPCTF QR code decoder

Translates the detected QR codes into the different QR codes type.
DPCTF specific QR codes - MezzanineDecodedQr, TestStatusDecodedQr and PreTestDecodedQr

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
import re
import logging
import json
from datetime import datetime
from qr_recognition.qr_decoder import DecodedQr, QrDecoder

logger = logging.getLogger(__name__)

_mezzanine_qr_data_re = re.compile(
    r"(.+);(\d{2}:[0-6][0-9]:[0-6][0-9].\d{3});(\d{7});([0-9.]+)"
)


class MezzanineDecodedQr(DecodedQr):
    data: str
    """qr code string"""

    """A decoded QR code from Mezzanine content
    ID;HH:MM:SS.MMM;<frame #>;<frame-rate>
    """
    content_id: str
    """The content id encoded in this QR code"""
    media_time: float
    """The media time encoded in this QR code"""
    frame_number: int
    """The media time encoded in this QR code"""
    frame_rate: float
    """The frame rate encoded in this QR code"""

    first_camera_frame_num: int
    """recorded camera frame number that the QR code is detected on"""
    last_camera_frame_num: int
    """recorded camera frame number that the QR code last appears on"""

    def __init__(
        self,
        data: str,
        content_id: str,
        media_time: float,
        frame_number: int,
        frame_rate: float,
        camera_frame_num: int,
    ):
        super().__init__(data)
        self.data = data
        self.content_id = content_id
        self.media_time = media_time
        self.frame_number = frame_number
        self.frame_rate = frame_rate
        self.first_camera_frame_num = camera_frame_num
        self.last_camera_frame_num = camera_frame_num


class TestStatusDecodedQr(DecodedQr):
    data: str
    """ qr code string"""

    """A decoded QR code for Test Runner status
    QR code in json format contain following info
    """
    status: str
    last_action: str
    current_time: float
    delay: int

    camera_frame_num: int
    """recorded camera frame number that the QR code is detected on"""

    def __init__(
        self,
        data: str,
        status: str,
        last_action: str,
        current_time: float,
        delay: int,
        camera_frame_num: int,
    ):
        super().__init__(data)
        self.data = data
        self.status = status
        self.last_action = last_action
        self.current_time = current_time
        self.delay = delay
        self.camera_frame_num = camera_frame_num


class PreTestDecodedQr(DecodedQr):
    data: str
    """ qr code string"""

    """A decoded QR code for pre test
    QR code in json format contain following info
    """
    session_token: str
    """session token encoded in the test runner QR code.
    """
    test_id: str
    """test id encoded in the test runner QR code.
    """

    def __init__(self, data: str, session_token: str, test_id: str):
        super().__init__(data)
        self.data = data
        self.session_token = session_token
        self.test_id = test_id


class DPCTFQrDecoder(QrDecoder):
    def _translate_qr_test_runner(
        self, data: str, json_data, camera_frame_num: int
    ) -> DecodedQr:
        """translate different type of test runner qr code"""
        code = DecodedQr("")

        try:
            code = TestStatusDecodedQr(
                data,
                json_data["s"],
                json_data["a"],
                float(json_data["ct"]),
                int(json_data["d"]),
                camera_frame_num,
            )
        except Exception:
            try:
                code = TestStatusDecodedQr(
                    data,
                    json_data["s"],
                    json_data["a"],
                    0,
                    int(json_data["d"]),
                    camera_frame_num,
                )
            except Exception:
                try:
                    code = TestStatusDecodedQr(
                        data,
                        json_data["s"],
                        json_data["a"],
                        0,
                        0,
                        camera_frame_num
                    )
                except Exception:
                    try:
                        code = PreTestDecodedQr(
                            data, json_data["session_token"], json_data["test_id"]
                        )
                    except Exception:
                        logger.error(f"Unrecognised QR code detected: {data}")

        return code

    def _media_time_str_to_ms(self, media_time_str: str) -> float:
        """Change media time string to ms
        return media time from mezzanine QR code in milliseconds
        """
        # temp bug fix from content to be removed
        if media_time_str == "00:00:60.000":
            media_time_str = "00:01:00.000"

        media_time_datetime = datetime.strptime(media_time_str, "%H:%M:%S.%f")

        ms = media_time_datetime.microsecond / 1000
        s_to_ms = media_time_datetime.second * 1000
        min_to_ms = media_time_datetime.minute * 60 * 1000
        h_to_ms = media_time_datetime.hour * 60 * 60 * 1000
        media_time = ms + s_to_ms + min_to_ms + h_to_ms

        return media_time

    def translate_qr(self, data: str, camera_frame_num: int) -> DecodedQr:
        """Given a QR code as reported by pyzbar, parse the data and convert it to
        the format we use.

        Returns the translated QR code, or None if it's not a valid QR code.

        Mezzanine QR code is higher priority and test status than the start test QR code.
        """
        code = DecodedQr("")

        match = _mezzanine_qr_data_re.match(data)
        if match:
            # matches a mezzanine signature so decode it as such
            media_time = self._media_time_str_to_ms(match.group(2))
            code = MezzanineDecodedQr(
                data,
                match.group(1),
                media_time,
                int(match.group(3)),
                float(match.group(4)),
                camera_frame_num,
            )
        else:
            try:
                json_data = json.loads(data)
                code = self._translate_qr_test_runner(data, json_data, camera_frame_num)
            except json.decoder.JSONDecodeError as e:
                logger.error(f"Unrecognised QR code JSON detected in '{data}'. JSON err: {e}")

        return code
