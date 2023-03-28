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
Licensor: Consumer Technology Association
Contributor: Eurofins Digital Product Testing UK Limited
"""
import csv
import importlib
import json
import logging
import os
from typing import List

import cv2
from configuration_parser import ConfigurationParser
from dpctf_qr_decoder import (DPCTFQrDecoder, MezzanineDecodedQr,
                              PreTestDecodedQr, TestStatusDecodedQr)
from exceptions import ConfigError, ObsFrameTerminate
from global_configurations import GlobalConfigurations
from log_handler import LogManager
from observation_result_handler import ObservationResultHandler
from qr_recognition.qr_decoder import DecodedQr
from qr_recognition.qr_recognition import FrameAnalysis

logger = logging.getLogger(__name__)


class ObservationFrameworkProcessor:
    """Class to handle observation process"""

    do_adaptive_threshold_scan: bool
    """additional adaptiveThreshold in qr code scan"""

    log_manager: LogManager
    """log manager"""

    tests: dict
    """tests codes dictonary to map test code with module and class"""

    last_end_of_test_camera_frame_num: int
    """recording frame number of the last finished event to check the end of session timeout"""
    end_of_session_timeout: int
    """end of session timeout
    when the gap is bigger that this, assume end of session is reached
    process stops and discard following recordings"""

    no_qr_code_frame_num: int
    """recording frame number of the no QR code detected to check the end of session timeout"""
    no_qr_code_timeout: int
    """no qr code timeout
    when the gap is bigger that this assume end of session is reached
    process stops and discard following recordings"""

    decoder: DPCTFQrDecoder
    """WAVE DPCTF QR code decoder to handle QR code translation"""

    global_configurations: GlobalConfigurations
    """Global Configurations"""

    configuration_parser: ConfigurationParser
    """configuration parser to parse configurations"""

    observation_result_handler: ObservationResultHandler
    """Observation result handler to pass result to Test Runner"""
    duplicated_qr_check_count: int
    """qr code list check back count for duplicated qr code detection"""

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

    session_log_path: str
    """session log folder path"""
    qr_list_file: str
    """decodec qr code csv file path"""
    time_diff_file: str
    """time difference csv file path"""

    consecutive_no_qr_threshold: int
    """Consecutive no mezzanine qr code camera frame threshold"""
    consecutive_no_qr_count: int
    """count of consecutive no qr code, stop counter when no  qr is detected
    stop counter when mezzanine qr is detected at any time"""
    first_qr_is_detected: bool
    """start consecutive no qr code count after 1st mezzanine qr is detected
    and stop counting when the status is finished"""
    test_started: bool
    """True when pre_test QR code is detected and False when status is finished"""
    results: list
    """ Holds the results of the observations """

    def __init__(
        self,
        log_manager: LogManager,
        global_configurations: GlobalConfigurations,
        fps: float,
        do_adaptive_threshold_scan: bool,
    ):
        """dict {test_code : (module_name, class_name)}
        test_code: test code from test runner configuration, this mapped from test ID from pre-test QR code
            with the tests.config file
        module_name: file name where the test handler is defined
        class_name: class name to handle each test code
        """
        with open("of_testname_map.json") as f:
            self.tests = json.load(f)

        self.log_manager = log_manager
        self.last_end_of_test_camera_frame_num = 0
        self.no_qr_code_frame_num = 0
        self.global_configurations = global_configurations
        self.end_of_session_timeout = global_configurations.get_end_of_session_timeout()
        self.no_qr_code_timeout = global_configurations.get_no_qr_code_timeout()
        self.decoder = DPCTFQrDecoder()
        self.configuration_parser = ConfigurationParser(self.global_configurations)
        self.observation_result_handler = ObservationResultHandler(
            self.global_configurations
        )

        self.do_adaptive_threshold_scan = do_adaptive_threshold_scan
        self.duplicated_qr_check_count = global_configurations.get_duplicated_qr_check_count()

        self.mezzanine_qr_codes = []
        self.test_status_qr_codes = []
        self.pre_test_qr_code = PreTestDecodedQr("", [], "", "")

        self.test_path = ""
        self.test_class = None

        self.camera_frame_rate = fps
        self.camera_frame_duration_ms = 1000 / fps

        self.session_log_path = ""
        self.qr_list_file = ""
        self.time_diff_file = ""

        self.consecutive_no_qr_threshold = 0
        self.consecutive_no_qr_count = 0
        self.first_qr_is_detected = False
        self.test_started = False
        self.results = []

    def _discard_duplicated_qr_code(self, detected_codes: List[DecodedQr]):
        """discard duplicated qr code by its frame number
        QR codes that are detected on same frame
        sort newly detected mazzanine QR codes on same image
        to avoid false out of order detection
        this function returns QR codes for different type individually
        """
        new_mezzanine_qr_codes = []
        new_test_status_qr_code = None
        new_pre_test_qr_code = None

        for detected_code in detected_codes:
            if isinstance(detected_code, MezzanineDecodedQr):
                check_back_count = 0
                duplicated = False
                for qr_code in self.mezzanine_qr_codes[::-1]:
                    check_back_count += 1
                    if check_back_count > self.duplicated_qr_check_count:
                        # add to list even duplicated frame
                        # duplicated frame normally chack back for duplicated_qr_check_count
                        # default value is 3 becuase we have only 4 QR code position
                        break
                    if qr_code == detected_code:
                        duplicated = True
                        # update last appear frame number
                        index = self.mezzanine_qr_codes.index(qr_code)
                        self.mezzanine_qr_codes[
                            index
                        ].last_camera_frame_num = detected_code.first_camera_frame_num
                        logger.debug(
                            f"Frame Number={self.mezzanine_qr_codes[index].frame_number} "
                            f"updating Last appear Frame={self.mezzanine_qr_codes[index].last_camera_frame_num}"
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
            raise ConfigError("Failed to get api name or test code!")
        logger.info(f"Start a New test: {self.test_path}")

        if self.session_log_path:
            self.time_diff_file = (
                self.session_log_path
                + "/"
                + self.test_path.replace("/", "-").replace(".html", "")
                + "_time_diff.csv"
            )
            # remove existing csv file, only keep the last result
            if os.path.exists(self.time_diff_file):
                os.remove(self.time_diff_file)

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

    def _make_observations(self):
        """make observations when move to next test
        or at the end of the recording
        the observation result is to be posted after
        observations being made
        """
        if self.test_class:
            try:
                results = self.test_class.make_observations(
                    self.mezzanine_qr_codes,
                    self.test_status_qr_codes,
                    self.time_diff_file,
                )
                self._save_results(results)

            except ObsFrameTerminate as e:
                results = []
                result = {
                    "status": "ERROR",
                    "message": f"{e}",
                    "name": "[OF] Too many missing frames are found.",
                }
                results.append(result)
                self.observation_result_handler.post_result(
                    self.pre_test_qr_code.session_token, self.test_path, results
                )
                raise ObsFrameTerminate(result["message"])

    def _save_results(self, results: list) -> None:
        """
        Save results to self.results
        when previous presentation result is not empty merge two results.
        Merge same result and append different result.
        """
        if not self.results:
            self.results = results
        else:
            for new_result in results:
                for result in self.results:
                    if new_result["name"] == result["name"]:
                        result["message"] = result["message"] + new_result["message"]
                        if (
                            new_result["status"] == "PASS"
                            and result["status"] == "PASS"
                        ):
                            result["status"] == "PASS"
                        else:
                            result["status"] = new_result["status"]
                    else:
                        self.results.append(new_result)

    def _post_observation_result(self) -> None:
        """Post observation result to test runner"""
        self.observation_result_handler.post_result(
            self.pre_test_qr_code.session_token, self.test_path, self.results
        )
        self.results = []

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
            f"Status={new_test_status_qr_code.status} "
            f"Last Action={new_test_status_qr_code.last_action} "
            f"Current Time={new_test_status_qr_code.current_time} "
            f"Delay={new_test_status_qr_code.delay} "
            f"Captured on Frame={new_test_status_qr_code.camera_frame_num}"
        )
        self.test_status_qr_codes.append(new_test_status_qr_code)
        if new_test_status_qr_code.status == "finished":
            self.last_end_of_test_camera_frame_num = (
                new_test_status_qr_code.camera_frame_num
            )
            self._make_observations()
            self._post_observation_result()

    def _process_pre_test_qr_code(self, new_pre_test_qr_code: PreTestDecodedQr) -> None:
        """Process newly detected pre-test QR code"""
        # get session token and validation recording should contain only one test session
        if (
            self.pre_test_qr_code.session_token != ""
            and self.pre_test_qr_code.session_token
            != new_pre_test_qr_code.session_token
        ):
            raise Exception(
                f"session_token does not match, recording should contain only one test session! "
                f"previous session={self.pre_test_qr_code.session_token}, "
                f"current session={new_pre_test_qr_code.session_token}"
            )

        if (
            self.pre_test_qr_code.session_token == ""
            and new_pre_test_qr_code.session_token != ""
        ):
            self.session_log_path = (
                self.global_configurations.get_log_file_path()
                + "/"
                + new_pre_test_qr_code.session_token
            )
            if not os.path.exists(self.session_log_path):
                os.makedirs(self.session_log_path)

            session_log_file = self.session_log_path + "/session.log"
            logger.info(f"Entering log file: {session_log_file}")
            self.log_manager.redirect_logfile(session_log_file)

            if logger.getEffectiveLevel() == logging.DEBUG:
                self.qr_list_file = self.session_log_path + "/qr_code_list.csv"
                # remove exsisting csv file, only keep the last result
                if os.path.exists(self.qr_list_file):
                    os.remove(self.qr_list_file)

                with open(self.qr_list_file, "a") as file:
                    file_writer = csv.writer(file)
                    file_writer.writerow(
                        [
                            "Camera Frame",
                            "Content ID",
                            "Media Time",
                            "Frame Number",
                            "Frame Rate",
                            "Test Status",
                            "Last Action",
                            "Current Time",
                            "Delay",
                            "Session ID",
                            "Test ID",
                        ]
                    )
                    file.close()

        # When a new pre test QR code is detected then load next test
        if self.pre_test_qr_code.test_id != new_pre_test_qr_code.test_id:
            self.last_end_of_test_camera_frame_num = 0
            self.pre_test_qr_code = new_pre_test_qr_code
            self._load_new_test()

    def check_timeout(
        self, last_frame_num: int, current_frame_num: int, timeout: int
    ) -> bool:
        """check timeout and log error message when timedout
        this is used to detect ened of sesssion:
            timeout after the last status=finished is recived untill the next pre-test QR code
            and idle time when there is no QR code detected

        Args:
            last_frame_num: last recording frame number to check the timeout from
                this is 0 when it is not set
            current_frame_num: current recording frame
            timeout: configured timeout in seconds from config.ini

        Return:
            True: when timedout
        """
        result = False

        if last_frame_num > 0:
            diff = current_frame_num - last_frame_num
            time_diff = round(diff / self.camera_frame_rate)
            if time_diff > timeout:
                result = True
                logger.info(
                    f"End of recorded session reached. "
                    f"({int(time_diff)} seconds passed while waiting for the next test. "
                    f"Timeout is set to {timeout} seconds)."
                )
        return result

    def extract_qr_data_to_csv(
        self, camera_frame_number: int, detected_qr_codes: List[DecodedQr]
    ) -> None:
        """Extract camera frame number and detected qr code data to a csv file"""
        if not self.qr_list_file:
            return

        with open(self.qr_list_file, "a") as file:
            file_writer = csv.writer(file)

            for detected_code in detected_qr_codes:
                if isinstance(detected_code, MezzanineDecodedQr):
                    file_writer.writerow(
                        [
                            camera_frame_number,
                            detected_code.content_id,
                            detected_code.media_time,
                            detected_code.frame_number,
                            detected_code.frame_rate,
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                        ]
                    )
                elif isinstance(detected_code, TestStatusDecodedQr):
                    file_writer.writerow(
                        [
                            camera_frame_number,
                            "",
                            "",
                            "",
                            "",
                            detected_code.status,
                            detected_code.last_action,
                            detected_code.current_time,
                            detected_code.delay,
                            "",
                            "",
                        ]
                    )
                elif isinstance(detected_code, PreTestDecodedQr):
                    file_writer.writerow(
                        [
                            camera_frame_number,
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            detected_code.session_token,
                            detected_code.test_id,
                        ]
                    )
                else:
                    continue

            file.close()

    def check_consecutive_no_qr_code(
        self, camera_frame_number: int, detected_qr_codes: List[DecodedQr]
    ) -> None:
        """check the detected qr codes and if there are no mezzanine qr code is detected
        count the missing code camera frame number, if it exceed the threshold
        terminate system
        """
        mezzanine_qr_is_detected = False
        for detected_code in detected_qr_codes:
            if isinstance(detected_code, MezzanineDecodedQr):
                self.consecutive_no_qr_count = 0
                mezzanine_qr_is_detected = True
                # update threshold based on detected qr code frame rate
                self.consecutive_no_qr_threshold = round(
                    self.global_configurations.get_consecutive_no_qr_threshold()
                    * self.camera_frame_rate
                    / detected_code.frame_rate
                )
                # first qr is detected when a new test is started
                if self.test_started:
                    self.first_qr_is_detected = True
            if isinstance(detected_code, TestStatusDecodedQr):
                if detected_code.status == "finished":  # changed from ended
                    self.test_started = False
                    self.first_qr_is_detected = False
            if isinstance(detected_code, PreTestDecodedQr):
                self.test_started = True

        if self.first_qr_is_detected and not mezzanine_qr_is_detected:
            self.consecutive_no_qr_count += 1

        if (
            self.consecutive_no_qr_threshold != 0
            and self.consecutive_no_qr_count > self.consecutive_no_qr_threshold
        ):
            raise ObsFrameTerminate(
                f"At camera frame {camera_frame_number} "
                f"there were {self.consecutive_no_qr_count} consecutive camera frames "
                f"where no mezzanine qr codes were detected. "
                f"Device Observation Framework is exiting, and the remaining tests are not observed."
            )

    def iter_qr_codes_in_video(
        self, vidcap, starting_camera_frame_number: int, qr_code_area: list
    ) -> int:
        """Iterate video frame by frame and detect QR codes.

        Args:
            vidcap: VideoCapture instance for the current file.
            starting_camera_frame_number: Camera frame number to begin numbering at.
            qr_code_area: List of QR code cropping areas.

        Returns:
            Last camera frame number in this file +1 (i.e. can be used as input to the next call).
        """
        capture_frame_num = 0
        corrupted_frame_num = 0
        len_frames = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))

        while (len_frames + corrupted_frame_num) > capture_frame_num:
            got_frame, image = vidcap.read()
            if not got_frame:
                if "corrupted" in self.global_configurations.get_ignore():
                    # work around for gopro
                    corrupted_frame_num += 1
                    capture_frame_num += 1
                    continue
                else:
                    break

            camera_frame_number = starting_camera_frame_number + capture_frame_num

            # check timeout after the last test finished event
            if self.check_timeout(
                self.last_end_of_test_camera_frame_num,
                camera_frame_number,
                self.end_of_session_timeout,
            ):
                break

            # check timeout when no qr code is detected
            if self.check_timeout(
                self.no_qr_code_frame_num, camera_frame_number, self.no_qr_code_timeout
            ):
                break

            analysis = FrameAnalysis(camera_frame_number, self.decoder)
            analysis.full_scan(image, qr_code_area, self.do_adaptive_threshold_scan)
            detected_qr_codes = analysis.all_codes()
            if detected_qr_codes:
                self.no_qr_code_frame_num = 0
            else:
                self.no_qr_code_frame_num = camera_frame_number

            # print out where the processing is currently
            if camera_frame_number % 10 == 0:
                print(f"Processed to frame {camera_frame_number}...")

            # extract qr code data to a csv file
            self.extract_qr_data_to_csv(camera_frame_number, detected_qr_codes)
            # check consecutive no qr code detection and
            # terminates the system when exceed the threshold
            self.check_consecutive_no_qr_code(camera_frame_number, detected_qr_codes)

            (
                new_mezzanine_qr_codes,
                new_test_status_qr_code,
                new_pre_test_qr_code,
            ) = self._discard_duplicated_qr_code(detected_qr_codes)

            if new_mezzanine_qr_codes:
                self._process_mezzanine_qr_codes(new_mezzanine_qr_codes)
            if new_test_status_qr_code:
                self._process_test_status_qr_code(new_test_status_qr_code)
            if new_pre_test_qr_code:
                self._process_pre_test_qr_code(new_pre_test_qr_code)

            capture_frame_num += 1

        return capture_frame_num
