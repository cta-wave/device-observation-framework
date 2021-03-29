# -*- coding: utf-8 -*-
"""DPCTF device observation framework processor

Handle the main process of the observation framework
detecting QR codes frame by frame
define the test class and make observations and send results

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
import importlib
import cv2
import logging

from typing import List
from dpctf_qr_decoder import (
    DPCTFQrDecoder,
    MezzanineDecodedQr,
    TestStatusDecodedQr,
    PreTestDecodedQr,
)
from configuration_parser import ConfigurationParser
from global_configurations import GlobalConfigurations
from qr_recognition.qr_decoder import DecodedQr
from qr_recognition.qr_recognition import FrameAnalysis
from observation_result_handler import ObservationResultHandler

logger = logging.getLogger(__name__)


class ObservationFrameworkProcessor:
    """Class to handle observation process"""

    tests: dict

    decoder: DPCTFQrDecoder
    """WAVE DPCTF QR code decoder to handle QR code translation"""

    global_configurations: GlobalConfigurations
    """Global Configurations"""

    configuration_parser: ConfigurationParser
    """configuration parser to parse configurations"""

    observation_result_handler: ObservationResultHandler
    """Observation result handler to pass result to Test Runner"""

    mezzanine_qr_codes: List[MezzanineDecodedQr]
    """detected list of mezzanine qr codes for current test"""
    test_status_qr_codes: List[TestStatusDecodedQr]
    """detected test runner status qr codes for current test"""
    pre_test_qr_code: PreTestDecodedQr
    """detected test runner pre test qr codes for current test"""

    test_path: str
    """test path of current test
    this is used to post result to test runner"""
    test_class: None
    """test module for current test
    assigned dynamically based on the detected test code"""

    camera_frame_rate: float
    """recording frame rate"""
    camera_frame_duration_ms: float
    """camera frame duration in ms based on captured frame rate"""

    def __init__(self, global_configurations: GlobalConfigurations, fps: float):
        """dict {test_code : (module_name, class_name)}
        test_code: test code from test runner configuration, this mapped from test ID from pre-test QR code
            with the tests.config file
        module_name: file name where the test handler is defined
        class_name: class name to handle each test code
        """
        self.tests = {
            "sequential-track-playback-manual.html": (
                "sequential_track_playback_manual",
                "SequentialTrackPlaybackManual",
            ),
            "random-access-to-fragment-manual.html": (
                "random_access_to_fragment_manual",
                "RandomAccessToFragmentManual",
            ),
            "random-access-to-time-manual.html": (
                "random_access_to_time_manual",
                "RandomAccessToTimeManual",
            ),
            "regular-playback-of-chunked-content-manual.html": (
                "regular_playback_of_chunked_content_manual",
                "RegularPlaybackOfChunkedContentManual",
            ),
            "regular-playback-of-chunked-content-non-aligned-append-manual.html": (
                "regular_playback_of_chunked_content_non_aligned_append_manual",
                "RegularPlaybackOfChunkedContentNonAlignedAppendManual",
            ),
            "out-of-order-loading-manual.html": (
                "out_of_order_loading_manual",
                "OutOfOrderLoadingManual",
            ),
            "fullscreen-playback-of-switching-sets-manual.html": (
                "fullscreen_playback_of_switching_sets_manual",
                "FullscreenPlaybackOfSwitchingSetsManual",
            ),
            "playback-of-encrypted-content-manual.html": (
                "playback_of_encrypted_content_manual",
                "PlaybackOfEncryptedContentManual",
            ),
        }

        self.global_configurations = global_configurations
        self.decoder = DPCTFQrDecoder()
        self.configuration_parser = ConfigurationParser(self.global_configurations)
        self.observation_result_handler = ObservationResultHandler(
            self.global_configurations
        )

        self.mezzanine_qr_codes = []
        self.test_status_qr_codes = []
        self.pre_test_qr_code = PreTestDecodedQr("", "", "")

        self.test_path = ""
        self.test_class = None

        self.camera_frame_rate = fps
        self.camera_frame_duration_ms = 1000 / fps

    def _discard_duplicated_qr_code(self, detected_codes: List[DecodedQr]):
        """discard duplicated qr code by its frame number
        QR codes that are detected on same frame
        sort it to avoid out of order
        this function returns QR codes for different type individually
        """
        new_mezzanine_qr_codes = []
        new_test_status_qr_code = None
        new_pre_test_qr_code = None

        for detected_code in detected_codes:
            if isinstance(detected_code, MezzanineDecodedQr):
                duplicated = False
                for qr_code in self.mezzanine_qr_codes[::-1]:
                    if qr_code == detected_code:
                        duplicated = True
                        # update last appear frame number
                        index = self.mezzanine_qr_codes.index(qr_code)
                        self.mezzanine_qr_codes[
                            index
                        ].last_camera_frame_num = detected_code.first_camera_frame_num
                        logger.debug(
                            f"Last appear on Frame={self.mezzanine_qr_codes[index].last_camera_frame_num}"
                        )
                        break
                if not duplicated:
                    new_mezzanine_qr_codes.append(detected_code)

            elif isinstance(detected_code, TestStatusDecodedQr):
                if not self.test_status_qr_codes:
                    new_test_status_qr_code = detected_code
                elif self.test_status_qr_codes[-1] != detected_code:
                    new_test_status_qr_code = detected_code

            elif isinstance(detected_code, PreTestDecodedQr):
                if self.pre_test_qr_code != detected_code:
                    new_pre_test_qr_code = detected_code

            else:
                continue

        new_mezzanine_qr_codes = sorted(
            new_mezzanine_qr_codes,
            key=lambda mezzanine_decoded_qr: mezzanine_decoded_qr.frame_number,
        )
        return new_mezzanine_qr_codes, new_test_status_qr_code, new_pre_test_qr_code

    def _load_new_test(self) -> None:
        """When a new test is detected load a new test
        import a test module and load test parameters
        """
        self.mezzanine_qr_codes = []
        self.test_status_qr_codes = []
        self.test_class = None
        self.test_path, test_code = self.configuration_parser.parse_tests_json(
            self.pre_test_qr_code.test_id
        )
        if self.test_path is None or test_code is None:
            raise Exception("Failed to get api name or test code!")
        logger.info(f"Start a New test: {self.test_path}")

        try:
            module_name = self.tests[test_code][0]
            class_name = self.tests[test_code][1]
            test_module = importlib.import_module("test_code." + module_name)
            self.test_class = getattr(test_module, class_name)(
                self.configuration_parser,
                self.global_configurations,
                self.test_path,
                test_code,
                self.camera_frame_rate,
                self.camera_frame_duration_ms,
            )
        except KeyError:
            raise Exception(f"Test '{test_code}' not supported!")

    def _make_observations(self) -> None:
        """make observations when move to next test
        or at the end of the recording
        the observation result is to be posted after
        observations being made
        """
        if self.test_class:
            results = self.test_class.make_observations(
                self.mezzanine_qr_codes, self.test_status_qr_codes
            )
            self.observation_result_handler.post_result(
                self.pre_test_qr_code.session_token, self.test_path, results
            )

        if len(self.mezzanine_qr_codes) > 1:
            percentage = (
                len(self.mezzanine_qr_codes)
                / self.mezzanine_qr_codes[-1].frame_number
                * 100
            )
            lost_num = self.mezzanine_qr_codes[-1].frame_number - len(
                self.mezzanine_qr_codes
            )
            logger.debug(f"{percentage}'%' frames captured, and {lost_num} frames lost")

    def _process_mezzanine_qr_codes(
        self, new_mezzanine_qr_codes: List[MezzanineDecodedQr]
    ) -> None:
        """Process newly detected Mezzanine content QR code"""
        self.mezzanine_qr_codes.extend(new_mezzanine_qr_codes)
        for new_code in new_mezzanine_qr_codes:
            logger.debug(
                f"Content ID={new_code.content_id} "
                f"Media Time={new_code.media_time} "
                f"Frame Number={new_code.frame_number} "
                f"Frame Rate={new_code.frame_rate} "
                f"Captured on Frame={new_code.first_camera_frame_num}"
            )

    def _process_test_status_qr_code(
        self, new_test_status_qr_code: TestStatusDecodedQr
    ) -> None:
        """Process newly detected Test Runner status QR code"""
        logger.debug(
            f"status={new_test_status_qr_code.status} "
            f"last_action={new_test_status_qr_code.last_action} "
            f"current_time={new_test_status_qr_code.current_time} "
            f"delay={new_test_status_qr_code.delay} "
            f"Captured on Frame={new_test_status_qr_code.camera_frame_num}"
        )
        self.test_status_qr_codes.append(new_test_status_qr_code)

    def _process_pre_test_qr_code(self, new_pre_test_qr_code: PreTestDecodedQr) -> None:
        """Process newly detected pre-test QR code"""
        # get session token and validation recording should contain only one test session
        if (
            self.pre_test_qr_code.session_token != ""
            and self.pre_test_qr_code.session_token != new_pre_test_qr_code.session_token
        ):
            raise Exception(
                f"session_token does not match, recording should contain only one test session! "
                f"previous session={self.pre_test_qr_code.session_token}, "
                f"current session={new_pre_test_qr_code.session_token}"
            )

        # When a new pre test QR code is detected make current observation then load next test
        if self.pre_test_qr_code.test_id != new_pre_test_qr_code.test_id:
            self._make_observations()
            self.pre_test_qr_code = new_pre_test_qr_code
            self._load_new_test()

    def iter_qr_codes_in_video(self, vidcap) -> None:
        """Iterate video frame by frame and detect QR codes"""
        capture_frame_num = 0
        len_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))

        while len_frames > capture_frame_num:
            got_frame, image = vidcap.read()
            if not got_frame:
                # work around for gopro
                continue
                # break

            analysis = FrameAnalysis(capture_frame_num, self.decoder)
            analysis.scan_all(image)

            (
                new_mezzanine_qr_codes,
                new_test_status_qr_code,
                new_pre_test_qr_code,
            ) = self._discard_duplicated_qr_code(analysis.all_codes())

            if new_mezzanine_qr_codes:
                self._process_mezzanine_qr_codes(new_mezzanine_qr_codes)
            if new_test_status_qr_code:
                self._process_test_status_qr_code(new_test_status_qr_code)
            if new_pre_test_qr_code:
                self._process_pre_test_qr_code(new_pre_test_qr_code)

            capture_frame_num += 1

        # Make observations when recording reached the end
        self._make_observations()
