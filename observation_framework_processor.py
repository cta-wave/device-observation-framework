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
Contributor: Resillion UK Limited
"""
import importlib
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple

import cv2

import utils
from audio_file_reader import extract_audio_to_wav_file, read_audio_recording
from configuration_parser import ConfigurationParser
from dpctf_qr_decoder import (
    DPCTFQrDecoder,
    MezzanineDecodedQr,
    PreTestDecodedQr,
    TestStatusDecodedQr,
)
from exceptions import ConfigError, ObsFrameTerminate
from global_configurations import GlobalConfigurations
from log_handler import LogManager
from observation_result_handler import ObservationResultHandler
from output_file_handler import extract_qr_data_to_csv, write_header_to_csv_file
from qr_recognition.qr_decoder import DecodedQr
from qr_recognition.qr_recognition import FrameAnalysis
from observations.observation import Observation
from test_code.long_duration_playback import (
    LongDurationPlayback,
    LongDurationPlaybackData,
)

# test finish delay in ms after 1st status "finished" status
TEST_FINISH_DELAY = 2000

# number of frames read ahead per scanning thread
# the read ahead frames are held in memory until the batch is drained,
# so this trades memory for the ability to keep every scanning thread busy
QR_SCAN_READ_AHEAD_FACTOR = 2

# how the frames of the gap between tests are scanned
# only the pre-test QR code ends the gap, so until that code appears, or the
# wait for it runs out, only the area that code is drawn in is scanned;
# every frame is still scanned, and a gap is narrowed only while the state
# below says the area holds that code
SCAN_FULL_FRAME = 0
SCAN_BETWEEN_TESTS = 1

# whether this recording draws its pre-test QR code inside the area the gap
# between tests would be narrowed to
# the area is a fraction of the frame rather than anything measured, so it is
# used only once a pre-test QR code decoded from this recording has been seen
# inside it, and never again once one has been seen outside it
PRE_TEST_AREA_UNKNOWN = 0
PRE_TEST_AREA_INSIDE = 1
PRE_TEST_AREA_OUTSIDE = 2

# failed reads in a row tolerated before reading stops
# an isolated corrupted frame is skipped, but a recording that has run out
# gives back nothing but failures, and skipping each one would never end
MAX_CONSECUTIVE_CORRUPTED_FRAMES = 3


class _ReadAheadFrame:
    """A frame read ahead of the drain, held until its scan has been drained.

    The image is kept so that the frame can be scanned again, without being
    re-read from the capture, when a new test changes the QR code limit, or the
    gap between tests begins or ends, after the frame was read.
    """

    __slots__ = (
        "camera_frame_number",
        "frame_num_after_read",
        "image",
        "scanned_with",
        "scan_mode",
        "pre_test_screen_seen",
        "scan",
    )

    def __init__(
        self,
        camera_frame_number,
        frame_num_after_read,
        image,
        scanned_with,
        scan_mode,
        pre_test_screen_seen,
        scan,
    ):
        self.camera_frame_number = camera_frame_number
        self.frame_num_after_read = frame_num_after_read
        self.image = image
        self.scanned_with = scanned_with
        self.scan_mode = scan_mode
        self.pre_test_screen_seen = pre_test_screen_seen
        self.scan = scan


class _ReadFrame:
    """A frame read from the recording, with the numbering it was read at."""

    __slots__ = ("camera_num", "capture_num", "image")

    def __init__(self, camera_num, capture_num, image):
        self.camera_num = camera_num
        self.capture_num = capture_num
        self.image = image


class _FrameReader:
    """Reads a recording frame by frame, in order, for either scanning loop.

    Owns the frame numbering, the corrupted frame workaround and the checks that
    end a read, so both loops share one copy of them. next() hands back the next
    frame to scan, or None once reading has finished.

    Nothing in a failed read says whether it is a corrupted frame or the end of
    the recording. Skipping one raises the allowance and the frame counter
    together, so the allowance can never end the read on its own; up to
    MAX_CONSECUTIVE_CORRUPTED_FRAMES failures in a row are skipped and the next
    one ends the read.
    """

    def __init__(
        self,
        processor,
        vid_cap,
        starting_camera_frame_number: int,
        print_processed_frame: bool,
    ):
        self.processor = processor
        self.vid_cap = vid_cap
        self.starting_camera_frame_number = starting_camera_frame_number
        self.print_processed_frame = print_processed_frame
        self.capture_frame_num = 0
        self.corrupted_frame_num = 0
        self.consecutive_corrupted_frame_num = 0
        self.len_frames = int(vid_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.stopped = False

    @property
    def finished(self) -> bool:
        """True once there is nothing further to read."""
        return (
            self.stopped
            or (self.len_frames + self.corrupted_frame_num) <= self.capture_frame_num
        )

    def reposition(self, capture_frame_num: int) -> None:
        """Carry on from where processing a frame left the capture."""
        self.capture_frame_num = capture_frame_num

    def next(self) -> Optional[_ReadFrame]:
        """The next frame to scan, or None once reading has finished."""
        while not self.finished:
            got_frame, image = self.vid_cap.read()
            if not got_frame:
                if self._skip_corrupted_frame():
                    continue
                return None

            self.consecutive_corrupted_frame_num = 0
            camera_frame_number = (
                self.starting_camera_frame_number + self.capture_frame_num
            )
            if self._timed_out(camera_frame_number):
                self.stopped = True
                return None

            if self.print_processed_frame and camera_frame_number % 50 == 0:
                print(f"Processed to frame {camera_frame_number}...")

            self.capture_frame_num += 1
            return _ReadFrame(camera_frame_number, self.capture_frame_num, image)
        return None

    def _skip_corrupted_frame(self) -> bool:
        """True when a failed read is a corrupted frame to be skipped past."""
        self.consecutive_corrupted_frame_num += 1
        ignore_corrupted = self.processor.global_configurations.get_ignore_corrupted()
        if (
            "video" in ignore_corrupted
            and self.consecutive_corrupted_frame_num
            <= MAX_CONSECUTIVE_CORRUPTED_FRAMES
        ):
            # work around for GoPro corrupted frames
            self.corrupted_frame_num += 1
            self.capture_frame_num += 1
            return True

        self.processor.logger.warning(
            "Recording frame %d is corrupted. Total recording frame number is %d. "
            "If this is not close to the end of recording, observation process will be "
            "terminating early.",
            self.capture_frame_num,
            self.len_frames,
        )
        self.stopped = True
        return False

    def _timed_out(self, camera_frame_number: int) -> bool:
        """True when either read timeout has been reached."""
        processor = self.processor
        return processor.check_timeout(
            processor.last_end_of_test_camera_frame_num,
            camera_frame_number,
            processor.end_of_session_timeout,
        ) or processor.check_timeout(
            processor.no_qr_code_frame_num,
            camera_frame_number,
            processor.no_qr_code_timeout,
        )


class ObservationFrameworkProcessor:
    """Class to handle observation process"""

    calibration_offset: float
    """camera calibration audio/video offset"""

    do_adaptive_threshold_scan: bool
    """additional adaptiveThreshold in qr code scan"""

    max_qr_code_num_in_frame: int
    """maximum possible qr code in a frame"""

    log_manager: LogManager
    """log manager"""
    logger: logging.Logger
    """logger"""

    tests: dict
    """tests codes dictionary to map test code with module and class"""

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
    qr_scan_thread_count: int
    """number of worker threads used for the QR code full scan
    1 means frames are scanned sequentially on the reading thread"""

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
    """decoded qr code csv file path"""
    observation_data_export_file: str
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

    input_audio_path_list: list
    """list of input audio file path"""

    ld_playback_data: LongDurationPlaybackData
    """Long duration playback data"""

    pre_test_qr_code_area: Optional[list]
    """area the pre-test qr code is expected in, the only area scanned between
    tests once it is known to hold that code, None when the scan between tests
    is not narrowed"""
    pre_test_area_state: int
    """whether pre_test_qr_code_area holds this recording's pre-test qr code,
    see PRE_TEST_AREA_UNKNOWN"""
    scan_mode: int
    """how the frames being scanned now are scanned, see SCAN_FULL_FRAME"""
    reduced_scan_between_tests_frames: int
    """frames of a gap scanned in the pre-test qr code area before the rest of
    that gap is scanned in full"""
    pre_test_area_margin: int
    """percentage of the pre-test qr code's own width/height added on each
    side when fitting pre_test_qr_code_area to it, see
    _update_pre_test_area_state"""
    scan_between_tests_frame_count: int
    """frames processed since the test reported finished"""
    pre_test_screen_seen: bool
    """whether a pre-test QR code has been decoded in the current gap between
    tests, see _update_scan_mode"""

    def __init__(
        self,
        calibration_offset: float,
        log_manager: LogManager,
        logger: logging.Logger,
        global_configurations: GlobalConfigurations,
        fps: float,
        do_adaptive_threshold_scan: bool,
        pre_test_qr_code_area: Optional[list] = None,
    ):
        """dict {test_code : (module_name, class_name)}
        test_code: test code from test runner configuration, this mapped from test ID
             from pre-test QR code with the tests.config file
        module_name: file name where the test handler is defined
        class_name: class name to handle each test code
        """
        with open("of_testname_map.json", encoding="utf-8") as f:
            self.tests = json.load(f)

        self.calibration_offset = calibration_offset
        self.log_manager = log_manager
        self.logger = logger
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
        self.max_qr_code_num_in_frame = 3
        self.duplicated_qr_check_count = (
            global_configurations.get_duplicated_qr_check_count()
        )
        self.qr_scan_thread_count = global_configurations.get_qr_scan_thread_count()

        self.mezzanine_qr_codes = []
        self.test_status_qr_codes = []
        self.pre_test_qr_code = PreTestDecodedQr("", [], "", "", 0)

        self.test_path = ""
        self.test_class = None

        self.camera_frame_rate = fps
        self.camera_frame_duration_ms = 1000 / fps

        self.session_log_path = ""
        self.qr_list_file = ""
        self.observation_data_export_file = ""

        self.consecutive_no_qr_threshold = 0
        self.consecutive_no_qr_count = 0
        self.first_qr_is_detected = False
        self.test_started = False
        self.results = []

        self.input_audio_path_list = []

        self.ld_playback_data = LongDurationPlaybackData()

        self.pre_test_qr_code_area = pre_test_qr_code_area
        self.pre_test_area_state = PRE_TEST_AREA_UNKNOWN
        self.scan_mode = SCAN_FULL_FRAME
        self.reduced_scan_between_tests_frames = int(
            global_configurations.get_reduced_scan_between_tests_timeout() * fps
        )
        self.scan_between_tests_frame_count = 0
        self.pre_test_screen_seen = False
        self.pre_test_area_margin = (
            global_configurations.get_reduced_scan_between_tests_margin()
        )

    def extract_audio(
        self, input_video_path_str: str, starting_camera_frame_number: int
    ):
        """
        Extract audio to a wav file and save file name in string
        and starting camera frame number
        """
        input_audio_path_str = extract_audio_to_wav_file(
            self.logger, input_video_path_str
        )
        self.input_audio_path_list.append(
            [input_audio_path_str, starting_camera_frame_number]
        )

    def sort_new_mezzanine(
        self, new_mezzanine_qr_codes: List[DecodedQr]
    ) -> List[DecodedQr]:
        """
        sort newly detected mezzanine QR codes on same image
        to avoid false out of order detection.
        sort by frame number if content not changed,
        else same content appended first.
        """
        if self.mezzanine_qr_codes:
            last_qr_code_id = self.mezzanine_qr_codes[-1].content_id
        else:
            last_qr_code_id = ""

        # mezzanine_1 group of codes has same id as previous content
        # mezzanine_2 group of codes has different id
        mezzanine_1 = []
        mezzanine_2 = []
        for code in new_mezzanine_qr_codes:
            if not last_qr_code_id:
                mezzanine_1.append(code)
            else:
                if last_qr_code_id == code.content_id:
                    mezzanine_1.append(code)
                else:
                    mezzanine_2.append(code)

        mezzanine_1 = sorted(
            mezzanine_1,
            key=lambda mezzanine_decoded_qr: mezzanine_decoded_qr.frame_number,
        )
        mezzanine_2 = sorted(
            mezzanine_2,
            key=lambda mezzanine_decoded_qr: mezzanine_decoded_qr.frame_number,
        )
        sorted_new_mezzanine = mezzanine_1 + mezzanine_2

        return sorted_new_mezzanine

    def _discard_duplicated_qr_code(self, detected_codes: List[DecodedQr]):
        """discard duplicated qr code by its frame number
        QR codes that are detected on same frame
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
                        # duplicated frame normally check back for duplicated_qr_check_count
                        # default value is 3 because we have only 4 QR code position
                        break
                    if qr_code == detected_code:
                        duplicated = True
                        # update last appear frame number
                        index = self.mezzanine_qr_codes.index(qr_code)
                        self.mezzanine_qr_codes[index].last_camera_frame_num = (
                            detected_code.first_camera_frame_num
                        )

                        # adds up location values
                        self.mezzanine_qr_codes[index].location = [
                            self.mezzanine_qr_codes[index].location[x]
                            + detected_code.location[x]
                            for x in range(len(detected_code.location))
                        ]

                        # increment detection count
                        self.mezzanine_qr_codes[index].detection_count += 1

                        self.logger.debug(
                            "Frame Number=%d Last Frame=%d Location sum=%s Detection count=%d.",
                            self.mezzanine_qr_codes[index].frame_number,
                            self.mezzanine_qr_codes[index].last_camera_frame_num,
                            self.mezzanine_qr_codes[index].location,
                            self.mezzanine_qr_codes[index].detection_count,
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
                    # update last appear frame number
                    self.pre_test_qr_code.last_camera_frame_num = (
                        detected_code.first_camera_frame_num
                    )
                # discard all QR codes that are detected at the same time with PreTestDecodedQr
                for log_code in detected_codes:
                    if not isinstance(log_code, PreTestDecodedQr):
                        self.logger.debug(
                            "Discarded QR code %s detected simultaneously with Pre-Test QR code.",
                            log_code.data,
                        )
                return [], None, new_pre_test_qr_code

            else:
                continue

        sorted_new_mezzanine = self.sort_new_mezzanine(new_mezzanine_qr_codes)

        return sorted_new_mezzanine, new_test_status_qr_code, new_pre_test_qr_code

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
        self.logger.info("Start a New test: %s", self.test_path)

        if self.session_log_path:
            self.observation_data_export_file = (
                self.session_log_path
                + "/"
                + self.test_path.replace("/", "-").replace(".html", "")
                + "_"
            )

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
        except KeyError as exc:
            raise ConfigError(f"Test '{test_code}' not supported!") from exc

        if self.test_class:
            content_type = self.test_class.get_content_type()
            if content_type == "audio":
                self.max_qr_code_num_in_frame = 1
            else:
                self.max_qr_code_num_in_frame = 3

            # Detect long-duration playback test and set flag to optimize QR detection
            # periodic detection is what makes the scan skip ahead; with it
            # turned off the test is a plain linear scan, so it is not reduced
            # detection and its frames can be read ahead like any other test's
            long_duration_configs = (
                self.global_configurations.get_long_duration_config()
            )
            self.ld_playback_data.is_reduced_detection = (
                isinstance(self.test_class, LongDurationPlayback)
                and long_duration_configs["check_interval_seconds"] != 0
            )

    def _read_audio_data_from_single_file(
        self,
        current_audio_path_str: str,
        time_current_recording_starts: float,
        play_found: bool,
        play_ct: float,
    ) -> list:
        if play_found:
            test_start_time = play_ct - time_current_recording_starts
        else:
            test_start_time = (
                self.pre_test_qr_code.last_camera_frame_num
                * self.camera_frame_duration_ms
                - time_current_recording_starts
            )
        test_finish_time = (
            self.last_end_of_test_camera_frame_num * self.camera_frame_duration_ms
            - time_current_recording_starts
        ) + TEST_FINISH_DELAY
        audio_subject_data = read_audio_recording(
            current_audio_path_str, test_start_time, test_finish_time
        )
        return audio_subject_data

    def _read_audio_data_from_multiple_files(
        self,
        current_audio_path_str: str,
        time_current_recording_starts: float,
        play_found: bool,
        play_ct: float,
    ) -> list:
        audio_subject_data = []
        pre_test_time_ms = (
            self.pre_test_qr_code.last_camera_frame_num * self.camera_frame_duration_ms
        )

        mid_audio_path_str_list = []
        for audio_path, start_frame_index in reversed(self.input_audio_path_list[:-1]):
            audio_start_time = start_frame_index * self.camera_frame_duration_ms
            if audio_start_time <= pre_test_time_ms:
                beginning_audio_path_str = audio_path
                break
            else:
                mid_audio_path_str_list.append(audio_path)

        # read 1st audio file for the test
        if play_found:
            test_start_time = play_ct - audio_start_time
        else:
            test_start_time = pre_test_time_ms - audio_start_time
        audio_subject_data.extend(
            read_audio_recording(beginning_audio_path_str, test_start_time, None)
        )

        # read middle audio files for the test
        for audio_path in reversed(mid_audio_path_str_list):
            audio_subject_data.extend(read_audio_recording(audio_path, 0, None))

        # read last audio files for the test
        test_finish_time = (
            self.last_end_of_test_camera_frame_num * self.camera_frame_duration_ms
            - time_current_recording_starts
        ) + TEST_FINISH_DELAY
        audio_subject_data.extend(
            read_audio_recording(current_audio_path_str, 0, test_finish_time)
        )
        return audio_subject_data

    def process_audio_data(self, content_type: str) -> Tuple[float, list]:
        """Process audio data for audio observation
        returns audio_test_start_time and audio_subject_data"""
        # if video only test returns empty audio data
        if "audio" not in content_type:
            return 0.0, []

        try:
            current_audio_path_str = self.input_audio_path_list[-1][0]
            time_current_recording_starts = (
                self.input_audio_path_list[-1][1] * self.camera_frame_duration_ms
            )

            # Get time when test status = play
            play_found, play_ct = Observation.find_event(
                "play", self.test_status_qr_codes, self.camera_frame_duration_ms
            )

            if (
                time_current_recording_starts
                <= self.pre_test_qr_code.last_camera_frame_num
                * self.camera_frame_duration_ms
            ):
                # audio data can be read from single file
                audio_subject_data = self._read_audio_data_from_single_file(
                    current_audio_path_str,
                    time_current_recording_starts,
                    play_found,
                    play_ct,
                )
            else:
                # audio data separated into multiple files
                audio_subject_data = self._read_audio_data_from_multiple_files(
                    current_audio_path_str,
                    time_current_recording_starts,
                    play_found,
                    play_ct,
                )

            # audio recording time is relative time to audio_test_start_time
            # and also adjust audio and video sync on camera
            if play_found:
                audio_test_start_time = play_ct
            else:
                audio_test_start_time = (
                    self.pre_test_qr_code.last_camera_frame_num
                    * self.camera_frame_duration_ms
                )
            # apply camera recording calibration offset
            audio_test_start_time -= self.calibration_offset
            return audio_test_start_time, audio_subject_data
        except:
            return 0.0, []

    def _make_observations(self):
        """make observations when move to next test
        or at the end of the recording
        the observation result is to be posted after
        observations being made
        """
        if self.test_class:
            content_type = self.test_class.get_content_type()
            audio_test_start_time, audio_subject_data = self.process_audio_data(
                content_type
            )

            try:
                results = self.test_class.make_observations(
                    audio_test_start_time,
                    audio_subject_data,
                    self.mezzanine_qr_codes,
                    self.test_status_qr_codes,
                    self.observation_data_export_file,
                )
                self._save_results(results)

            except ObsFrameTerminate as exc:
                results = []
                result = {
                    "status": "NOT_RUN",
                    "message": f"{exc}",
                    "name": "[OF] Observations are not run.",
                }
                results.append(result)
                self.observation_result_handler.post_result(
                    self.pre_test_qr_code.session_token, self.test_path, results
                )
                raise ObsFrameTerminate(result["message"]) from exc
        else:
            self.logger.warning(
                "Unable to identify current test. Observation will not be made."
            )

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
                            result["status"] = "PASS"
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
            self.logger.debug(
                "Content ID=%s Media Time=%f Frame Number=%d Frame Rate=%s Captured on Frame=%d",
                new_code.content_id,
                new_code.media_time,
                new_code.frame_number,
                str(new_code.frame_rate),
                new_code.first_camera_frame_num,
            )

    def _process_test_status_qr_code(
        self, new_test_status_qr_code: TestStatusDecodedQr
    ) -> None:
        """Process newly detected Test Runner status QR code"""
        self.logger.debug(
            "Status=%s Last Action=%s Current Time=%f Delay=%d Captured on Frame=%d",
            new_test_status_qr_code.status,
            new_test_status_qr_code.last_action,
            new_test_status_qr_code.current_time,
            new_test_status_qr_code.delay,
            new_test_status_qr_code.camera_frame_num,
        )
        self.test_status_qr_codes.append(new_test_status_qr_code)
        if new_test_status_qr_code.status == "finished":
            self.last_end_of_test_camera_frame_num = (
                new_test_status_qr_code.camera_frame_num
            )
            self._make_observations()
            self._post_observation_result()
            self.test_class = None
            if self.pre_test_qr_code_area and self.scan_mode == SCAN_FULL_FRAME:
                # this test's observations are made here, so nothing but the
                # next test's pre-test QR code is used until it is decoded or
                # the scan gives up waiting for it; whether the frames of this
                # gap are narrowed as well is _scan_mode_in_force's to say
                self.scan_mode = SCAN_BETWEEN_TESTS
                self.scan_between_tests_frame_count = 0
                self.pre_test_screen_seen = False

    def _process_pre_test_qr_code(self, new_pre_test_qr_code: PreTestDecodedQr) -> None:
        """Process newly detected pre-test QR code"""
        # get session token and validation recording should contain only one test session
        if (
            self.pre_test_qr_code.session_token != ""
            and self.pre_test_qr_code.session_token
            != new_pre_test_qr_code.session_token
        ):
            raise ConfigError(
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

            if self.log_manager:
                session_log_file = self.session_log_path + "/session.log"
                self.logger.info("Entering log file: %s", session_log_file)
                self.log_manager.redirect_logfile(session_log_file)

            if self.logger.getEffectiveLevel() == logging.DEBUG:
                self.qr_list_file = self.session_log_path + "/qr_code_list.csv"
                write_header_to_csv_file(
                    self.qr_list_file,
                    [
                        "Camera Frame",
                        "Content ID",
                        "Media Time",
                        "Frame Number",
                        "Frame Rate",
                        "Location",
                        "Test Status",
                        "Last Action",
                        "Current Time",
                        "Delay",
                        "Session ID",
                        "Test ID",
                    ],
                )

        # When a new pre test QR code is detected then load next test
        if self.pre_test_qr_code.test_id != new_pre_test_qr_code.test_id:
            self.last_end_of_test_camera_frame_num = 0
            self.pre_test_qr_code = new_pre_test_qr_code
            self._load_new_test()

    def check_timeout(
        self, last_frame_num: int, current_frame_num: int, timeout: int
    ) -> bool:
        """check timeout and log error message when timed out
        this is used to detect end of session:
            timeout after the last status=finished is received until the next pre-test QR code
            and idle time when there is no QR code detected

        Args:
            last_frame_num: last recording frame number to check the timeout from
                this is 0 when it is not set
            current_frame_num: current recording frame
            timeout: configured timeout in seconds from config.ini

        Return:
            True: when timed out
        """
        result = False

        if last_frame_num > 0:
            diff = current_frame_num - last_frame_num
            time_diff = round(diff / self.camera_frame_rate)
            if time_diff > timeout:
                result = True
                self.logger.info(
                    "End of recorded session reached. (%d seconds passed while waiting for "
                    "the next test. Timeout is set to %d seconds).",
                    int(time_diff),
                    timeout,
                )
        return result

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
                if detected_code.status == "finished":
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
                f"Device Observation Framework is exiting, "
                f"and the remaining tests are not observed."
            )

    def process_ld_test_optimizations(
        self, last_mezzanine_qr_code, vid_cap, capture_frame_num
    ) -> int:
        """
        Process Long Duration Playback test optimizations by skipping frames
        between detection intervals to reduce processing time.

        The logic for handling the end of the observation window when jumping frames
        ensures that the frame jump does not exceed the bounds of the observation window.
        Specifically, before performing a jump, the method predicts whether the
        next jump would move past the last valid frame for the observation window.
        If so, it adjusts the jump to land exactly at the start of the ending check window,
        ensuring all required frames are processed.
        At this point, reduced detection is disabled to allow for full scanning
        of the final segment of the observation window, guaranteeing that no relevant QR codes
        are missed near the end of the observation window.
        This may cause more frames to be processed than the last observation window
        duration, but it ensures the integrity of the observation observations.

        Args:
            last_mezzanine_qr_code: The last detected Mezzanine QR code.
            vid_cap: VideoCapture instance for the current file.
            capture_frame_num: Current capture frame number.

        Returns:
            Updated capture frame number after processing optimizations.
            If no optimization (frame jump) is applied, the returned value may be
            unchanged from the input.
        """
        long_duration_configs = self.global_configurations.get_long_duration_config()
        starting_check_duration = long_duration_configs["starting_check_duration"]
        mid_check_duration = long_duration_configs["mid_check_duration"]
        ending_check_duration = long_duration_configs["ending_check_duration"]
        check_interval_seconds = long_duration_configs["check_interval_seconds"]

        # If check_interval_seconds is 0, disable PeriodicQrDetection.
        if check_interval_seconds == 0:
            return capture_frame_num

        mezzanine_frame_rate = last_mezzanine_qr_code.frame_rate
        starting_check_duration_in_frame = utils.seconds_to_frame_num(
            starting_check_duration, mezzanine_frame_rate
        )
        mid_check_duration_in_frame = utils.seconds_to_frame_num(
            mid_check_duration, mezzanine_frame_rate
        )
        ending_check_duration_in_frame = utils.seconds_to_frame_num(
            ending_check_duration, mezzanine_frame_rate
        )

        if self.ld_playback_data.is_initial_detection:
            detection_window_frames = starting_check_duration_in_frame
        else:
            detection_window_frames = mid_check_duration_in_frame

        # next interval in recording based on camera frame rate that we skip the detection
        # we can not jump based on mezzanine frame rate because mezzanine qr code detection
        # is not available in every frame as we skip frames
        next_interval_in_recording = utils.seconds_to_frame_num(
            (
                check_interval_seconds
                - utils.frame_num_to_seconds(
                    detection_window_frames, mezzanine_frame_rate
                )
            ),
            self.camera_frame_rate,
        )

        # Set the starting detection interval
        if self.ld_playback_data.ready_for_next_interval:
            self.ld_playback_data.ld_last_qr_detection_start_at = (
                last_mezzanine_qr_code.frame_number
            )
            self.test_class.set_observation_window(
                self.ld_playback_data.ld_last_qr_detection_start_at, is_start=True
            )
            self.ld_playback_data.ready_for_next_interval = False

        # Check if current detection window is completed
        if last_mezzanine_qr_code.frame_number >= (
            self.ld_playback_data.ld_last_qr_detection_start_at
            + detection_window_frames
        ):
            jump_frames = capture_frame_num + next_interval_in_recording

            # End of observation window handling to ensure we do not skip past the observation end
            last_test_win_start_frame_num = (
                self.test_class.get_last_frame_num(mezzanine_frame_rate)
                - ending_check_duration_in_frame
            )
            # Predict if the next jump will exceed the observation window
            predicted_jump_to_mezzanine_frame_num = (
                last_mezzanine_qr_code.frame_number
                + utils.seconds_to_frame_num(
                    check_interval_seconds, mezzanine_frame_rate
                )
                - detection_window_frames
            )
            # If exceeding, adjust jump to end of observation window
            if predicted_jump_to_mezzanine_frame_num > last_test_win_start_frame_num:
                remaining_window_seconds = utils.frame_num_to_seconds(
                    last_test_win_start_frame_num - last_mezzanine_qr_code.frame_number,
                    mezzanine_frame_rate,
                )
                jump_frames = capture_frame_num + utils.seconds_to_frame_num(
                    remaining_window_seconds, self.camera_frame_rate
                )
                # End of observation window reached, disable reduced detection
                # to allow full scanning of final segment
                self.ld_playback_data.is_reduced_detection = False
                self.ld_playback_data.is_last_detection = True

            # handle the case when jump_frames exceed total frame count of the video
            last_frame = int(vid_cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
            jump_frames = min(jump_frames, last_frame)
            self.logger.debug(
                f"Jumping to frame {jump_frames} as time "
                f"{utils.frame_num_to_seconds(jump_frames, self.camera_frame_rate)} seconds"
            )
            vid_cap.set(cv2.CAP_PROP_POS_FRAMES, jump_frames)
            capture_frame_num = jump_frames
            self.test_class.set_observation_window(
                last_mezzanine_qr_code.frame_number,
                is_start=False,
            )
            self.ld_playback_data.ready_for_next_interval = True
            self.ld_playback_data.is_initial_detection = False
        return capture_frame_num

    def _scan_mode_in_force(self) -> int:
        """how the frames being scanned now are to be scanned

        The gap between tests is narrowed only where this recording has been
        seen to draw its pre-test QR code in the area the gap is narrowed to,
        so the gap's own mode counts for nothing until then. Both scanning
        loops take the mode from here, so neither can scan a frame in a mode
        the other would not have given it.
        """
        if self.pre_test_area_state == PRE_TEST_AREA_INSIDE:
            return self.scan_mode
        return SCAN_FULL_FRAME

    def _fit_pre_test_area(self, location: list) -> list:
        """narrow pre_test_qr_code_area to the pre-test qr code's own location

        Called once, on the first pre-test qr code judged inside the coarse
        guard area, so later gaps are scanned against where this recording
        actually draws the code rather than the whole guard area.

        Args:
            location: [x, y, w, h] of the pre-test qr code that settled it
        Returns:
            [x0, y0, x1, y1] of location expanded by pre_test_area_margin
            percent of its own width/height on every side
        """
        x, y, width, height = location
        margin_x = int(width * self.pre_test_area_margin / 100)
        margin_y = int(height * self.pre_test_area_margin / 100)
        # x1/y1 are never clamped to the frame: they come from a location
        # already decoded inside it, so an over-large upper bound is truncated
        # safely by numpy slicing rather than wrapping, unlike a negative one
        return [
            max(0, x - margin_x),
            max(0, y - margin_y),
            x + width + margin_x,
            y + height + margin_y,
        ]

    def _update_pre_test_area_state(self, detected_qr_codes: list) -> None:
        """learn where this recording draws its pre-test QR code

        Must be called on the reading thread, once per frame, in recording
        order. Between tests the pre-test QR code area is the only area
        scanned, so a code drawn outside it could not be read there and the gap
        would be held open until the wait for it ran out. The evidence is the
        location of a pre-test QR code decoded from this recording, which is
        the same evidence the gap already ends on.

        A code seen outside the area settles it for the rest of the recording.
        A gap narrowed against a location the code is not drawn in is narrowed
        against nothing.

        Args:
            detected_qr_codes: list of detected qr codes in this frame
        """
        if (
            not self.pre_test_qr_code_area
            or self.pre_test_area_state == PRE_TEST_AREA_OUTSIDE
        ):
            return

        for detected_code in detected_qr_codes:
            if not isinstance(detected_code, PreTestDecodedQr):
                continue

            location = detected_code.location
            if (
                location[0] >= self.pre_test_qr_code_area[0]
                and location[0] + location[2] <= self.pre_test_qr_code_area[2]
                and location[1] >= self.pre_test_qr_code_area[1]
                and location[1] + location[3] <= self.pre_test_qr_code_area[3]
            ):
                if self.pre_test_area_state == PRE_TEST_AREA_UNKNOWN:
                    self.pre_test_area_state = PRE_TEST_AREA_INSIDE
                    self.pre_test_qr_code_area = self._fit_pre_test_area(location)
                    self.logger.info(
                        "Pre-test QR code was detected at %s, inside the cropped "
                        "area %s, so the gaps between the tests that follow are "
                        "scanned in that area alone.",
                        location,
                        self.pre_test_qr_code_area,
                    )
                continue

            self.pre_test_area_state = PRE_TEST_AREA_OUTSIDE
            self.logger.info(
                "Pre-test QR code was detected at %s, outside the cropped area "
                "%s, so the QR code scan between tests is not narrowed for the "
                "rest of this session.",
                location,
                self.pre_test_qr_code_area,
            )
            return

    def _scan_frame(
        self,
        camera_frame_number: int,
        image,
        qr_code_areas: list,
        max_qr_code_num_in_frame: int,
        scan_mode: int = SCAN_FULL_FRAME,
        *,
        pre_test_screen_seen: bool,
    ) -> list:
        """scan a single frame for qr codes

        This holds no observation state and is safe to call from a worker thread.
        max_qr_code_num_in_frame, scan_mode and pre_test_screen_seen are passed
        in rather than read from self so that the values in force when the
        frame was read are the values used to scan it. pre_test_qr_code_area is
        the exception: it is still read from self here, since it is only ever
        reassigned once, on the reading thread, in _fit_pre_test_area.

        Once a pre-test QR code has already been seen in the current gap
        (pre_test_screen_seen), an empty cropped scan falls back to a full
        scan of the same frame, on the assumption that the pre-test screen is
        still showing and worth the full scan's cost to keep reading; before
        it has been seen the crop is trusted alone, bounded only by
        reduced_scan_between_tests_frames.

        Args:
            camera_frame_number: current camera frame number
            image: current frame image
            qr_code_areas: list of qr code cropping areas
            max_qr_code_num_in_frame: maximum possible qr code in this frame
            scan_mode: how this frame is to be scanned, see SCAN_FULL_FRAME
            pre_test_screen_seen: whether a pre-test QR code has already been
                decoded in the current gap between tests, see _update_scan_mode
        Returns:
            detected_qr_codes: list of detected qr codes in this frame
        """
        analysis = FrameAnalysis(
            camera_frame_number, self.decoder, max_qr_code_num_in_frame
        )
        if scan_mode == SCAN_FULL_FRAME or not self.pre_test_qr_code_area:
            analysis.full_scan(image, qr_code_areas, self.do_adaptive_threshold_scan)
            return analysis.all_codes()

        analysis.cropped_scan(
            image, self.pre_test_qr_code_area, self.do_adaptive_threshold_scan
        )
        detected_qr_codes = analysis.all_codes()
        if not detected_qr_codes and pre_test_screen_seen:
            analysis.full_scan(image, qr_code_areas, self.do_adaptive_threshold_scan)
            return analysis.all_codes()

        return detected_qr_codes

    def _record_frame_analysis(
        self, camera_frame_number: int, detected_qr_codes: list
    ) -> None:
        """record the result of scanning a single frame

        Must be called on the reading thread, once per frame, in recording order.

        Args:
            camera_frame_number: current camera frame number
            detected_qr_codes: list of detected qr codes in this frame
        """
        if detected_qr_codes:
            self.no_qr_code_frame_num = 0
        else:
            self.no_qr_code_frame_num = camera_frame_number

        # extract qr code data to a csv file
        extract_qr_data_to_csv(
            self.qr_list_file, camera_frame_number, detected_qr_codes
        )
        # check consecutive no qr code detection and
        # terminates the system when exceed the threshold
        self.check_consecutive_no_qr_code(camera_frame_number, detected_qr_codes)

    def analysis_frame(
        self, camera_frame_number: int, image, qr_code_areas: list
    ) -> list:
        """analyze a single frame for qr code detection
        Args:
            camera_frame_number: current camera frame number
            image: current frame image
            qr_code_areas: list of qr code cropping areas
        Returns:
            detected_qr_codes: list of detected qr codes in this frame
        """
        detected_qr_codes = self._scan_frame(
            camera_frame_number,
            image,
            qr_code_areas,
            self.max_qr_code_num_in_frame,
            self._scan_mode_in_force(),
            pre_test_screen_seen=self.pre_test_screen_seen,
        )
        self._record_frame_analysis(camera_frame_number, detected_qr_codes)

        return detected_qr_codes

    def process_detected_qr_codes(
        self, detected_qr_codes, vid_cap, capture_frame_num
    ) -> int:
        """process detected qr codes in the current frame
        Args:
            detected_qr_codes: list of detected qr codes in this frame
            vid_cap: VideoCapture instance for the current file.
            capture_frame_num: Current capture frame number
        Returns:
            Updated capture frame number after processing detected QR codes
        """
        (
            new_mezzanine_qr_codes,
            new_test_status_qr_code,
            new_pre_test_qr_code,
        ) = self._discard_duplicated_qr_code(detected_qr_codes)

        if new_pre_test_qr_code:
            self._process_pre_test_qr_code(new_pre_test_qr_code)

        if new_mezzanine_qr_codes:
            if not self.test_class:
                self.logger.warning(
                    "Mezzanine QR code is detected before identifying the test. "
                    "observations won't be made, stop process if you want."
                )
            self._process_mezzanine_qr_codes(new_mezzanine_qr_codes)

            # Long Duration Playback test optimizations
            if self.ld_playback_data.is_last_detection:
                self.test_class.set_observation_window(
                    new_mezzanine_qr_codes[-1].frame_number, is_start=True
                )
                self.test_class.set_observation_window(
                    self.test_class.get_last_frame_num(
                        new_mezzanine_qr_codes[-1].frame_rate
                    ),
                    is_start=False,
                )
                self.ld_playback_data.is_last_detection = False
            if self.ld_playback_data.is_reduced_detection:
                capture_frame_num = self.process_ld_test_optimizations(
                    new_mezzanine_qr_codes[-1], vid_cap, capture_frame_num
                )

        if new_test_status_qr_code:
            if not self.test_class:
                self.logger.warning(
                    "Test status QR code is detected before identifying the test. "
                    "observations won't be made, stop process if you want."
                )
            self._process_test_status_qr_code(new_test_status_qr_code)

        self._update_pre_test_area_state(detected_qr_codes)
        self._update_scan_mode(detected_qr_codes)
        return capture_frame_num

    def _update_scan_mode(self, detected_qr_codes: list) -> None:
        """end the narrowed scan of the gap between tests

        Must be called on the reading thread, once per frame, in recording
        order. The first pre-test QR code decoded in the gap sets
        pre_test_screen_seen, but does not by itself end the gap: the pre-test
        screen can still be showing on later frames, and _scan_frame's
        full-scan fallback is there to keep reading it while the crop alone
        is not enough. Once pre_test_screen_seen is set, the gap instead ends
        on the frame a mezzanine or test status QR code is decoded in, since
        that is what shows the next test has started; a status code repeating
        the same test's finished report, decoded before the pre-test screen
        has been seen, is not that signal and is left to the frame count
        below.

        Before the first pre-test QR code, the gap also ends after
        reduced_scan_between_tests_frames frames without one, because nothing
        else leaves it there: a pre-test QR code the crop cannot read then
        costs at most the one test it announces. The count is of frames
        processed, never of what any frame was found to hold, and stops being
        advanced once pre_test_screen_seen is set, since the wait it bounds is
        over.

        The exit check above is evaluated against pre_test_screen_seen as it
        stood before this same call's pre-test QR code update below, so a
        frame whose detected_qr_codes carries both a pre-test code and a
        mezzanine/status code cannot end the gap on that frame; the exit is
        deferred to the next frame that carries a mezzanine/status code.

        Args:
            detected_qr_codes: list of detected qr codes in this frame
        """
        if self.scan_mode == SCAN_FULL_FRAME:
            return

        if self.pre_test_screen_seen and any(
            isinstance(code, (MezzanineDecodedQr, TestStatusDecodedQr))
            for code in detected_qr_codes
        ):
            self.scan_mode = SCAN_FULL_FRAME
            return

        if any(isinstance(code, PreTestDecodedQr) for code in detected_qr_codes):
            self.pre_test_screen_seen = True

        if self.pre_test_screen_seen:
            return

        self.scan_between_tests_frame_count += 1
        if self.scan_between_tests_frame_count > self.reduced_scan_between_tests_frames:
            # a gap that was never narrowed has nothing to report
            report = self._scan_mode_in_force() == SCAN_BETWEEN_TESTS
            self.scan_mode = SCAN_FULL_FRAME
            if report:
                self.logger.info(
                    "No pre-test QR code was detected in the %d frames since "
                    "the test reported finished, so the scan is widened to the "
                    "full frame. It is narrowed again on the next status QR "
                    "code reporting finished.",
                    self.scan_between_tests_frame_count,
                )

    def iter_qr_codes_in_video(
        self,
        vid_cap,
        starting_camera_frame_number: int,
        qr_code_areas: list,
        print_processed_frame: bool,
    ) -> int:
        """Iterate video frame by frame and detect QR codes.

        The scan is shared across qr_scan_thread_count worker threads when more
        than one is configured. Both paths read through _FrameReader and record
        and process frames in recording order. They differ only in that the
        threaded path reads ahead, so its timeout checks can see a counter that
        a frame still in flight has yet to update.

        Args:
            vid_cap: VideoCapture instance for the current file.
            starting_camera_frame_number: Camera frame number to begin numbering at.
            qr_code_area: List of QR code cropping areas.

        Returns:
            Last camera frame number in this file +1 (i.e. can be used as input to the next call).
        """
        if self.qr_scan_thread_count > 1:
            return self._iter_qr_codes_threaded(
                vid_cap,
                starting_camera_frame_number,
                qr_code_areas,
                print_processed_frame,
            )
        return self._iter_qr_codes_sequential(
            vid_cap,
            starting_camera_frame_number,
            qr_code_areas,
            print_processed_frame,
        )

    def _iter_qr_codes_sequential(
        self,
        vid_cap,
        starting_camera_frame_number: int,
        qr_code_areas: list,
        print_processed_frame: bool,
    ) -> int:
        """Read, scan and process one frame at a time on the calling thread.

        Args:
            vid_cap: VideoCapture instance for the current file.
            starting_camera_frame_number: Camera frame number to begin numbering at.
            qr_code_area: List of QR code cropping areas.

        Returns:
            Last camera frame number in this file +1 (i.e. can be used as input to the next call).
        """
        reader = _FrameReader(
            self, vid_cap, starting_camera_frame_number, print_processed_frame
        )

        while True:
            read = reader.next()
            if read is None:
                break

            detected_qr_codes = self.analysis_frame(
                read.camera_num, read.image, qr_code_areas
            )
            reader.reposition(
                self.process_detected_qr_codes(
                    detected_qr_codes, vid_cap, read.capture_num
                )
            )

        return reader.capture_frame_num

    def _iter_qr_codes_threaded(
        self,
        vid_cap,
        starting_camera_frame_number: int,
        qr_code_areas: list,
        print_processed_frame: bool,
    ) -> int:
        """Read frames ahead and scan them on worker threads.

        Frames are read on this thread only, because VideoCapture is not safe to
        share. Up to QR_SCAN_READ_AHEAD_FACTOR frames per worker are read ahead
        and their scans submitted, then the batch is drained in the order it was
        read so that everything downstream of the scan still sees frames in
        recording order. Each frame read ahead is held in memory until its scan
        has been drained, which is roughly 6MB at 1080p and 25MB at 4K.

        Processing a frame can invalidate the frames read behind it, so where
        that can happen nothing is read ahead. A long duration playback test
        jumps the capture forward between its detection windows, and for as long
        as it is doing so frames are read one at a time and the scan runs on the
        reading thread's batch of one. Its ending check window is a plain linear
        scan and is read ahead like any other test. A new test can also change
        how many QR codes a frame is expected to hold; that is not known before
        the frame is drained, so there the frames still held from the batch are
        scanned again with the setting that applies to them. They are never read
        again: the capture is only ever repositioned by the long duration
        playback jump, exactly as on the sequential path, because a frame seek
        is not frame accurate on every recording.

        The two timeout checks read counters that a frame still in flight has yet
        to update, so a timeout can be noticed up to one batch of frames later
        than on the sequential path. Both timeouts are measured in seconds, so
        this is well inside the frames they allow for.

        Args:
            vid_cap: VideoCapture instance for the current file.
            starting_camera_frame_number: Camera frame number to begin numbering at.
            qr_code_area: List of QR code cropping areas.

        Returns:
            Last camera frame number in this file +1 (i.e. can be used as input to the next call).
        """
        reader = _FrameReader(
            self, vid_cap, starting_camera_frame_number, print_processed_frame
        )

        with ThreadPoolExecutor(max_workers=self.qr_scan_thread_count) as executor:
            while not reader.finished:
                # a long duration playback test jumps the capture from inside
                # the drain, so while it is doing that a frame is read, scanned
                # and drained on its own and nothing is ever read ahead of a jump
                read_ahead = (
                    1
                    if self.ld_playback_data.is_reduced_detection
                    else self.qr_scan_thread_count * QR_SCAN_READ_AHEAD_FACTOR
                )

                # read ahead and submit a scan for each frame read
                batch = []
                while len(batch) < read_ahead:
                    read = reader.next()
                    if read is None:
                        break

                    max_qr_code_num_in_frame = self.max_qr_code_num_in_frame
                    scan_mode = self._scan_mode_in_force()
                    pre_test_screen_seen = self.pre_test_screen_seen
                    batch.append(
                        _ReadAheadFrame(
                            read.camera_num,
                            read.capture_num,
                            read.image,
                            max_qr_code_num_in_frame,
                            scan_mode,
                            pre_test_screen_seen,
                            executor.submit(
                                self._scan_frame,
                                read.camera_num,
                                read.image,
                                qr_code_areas,
                                max_qr_code_num_in_frame,
                                scan_mode,
                                pre_test_screen_seen=pre_test_screen_seen,
                            ),
                        )
                    )

                # drain the batch in the order the frames were read
                for index, frame in enumerate(batch):
                    if (
                        self.max_qr_code_num_in_frame != frame.scanned_with
                        or self._scan_mode_in_force() != frame.scan_mode
                        or self.pre_test_screen_seen != frame.pre_test_screen_seen
                    ):
                        # a new test, or the gap between tests beginning or
                        # ending, has changed how the frames must be scanned;
                        # the frames still held are scanned again with the new
                        # setting rather than re-read, so the capture is not moved
                        for held in batch[index:]:
                            # the superseded scan is queued ahead of its
                            # replacement, so drop it rather than wait for it
                            held.scan.cancel()
                            held.scanned_with = self.max_qr_code_num_in_frame
                            held.scan_mode = self._scan_mode_in_force()
                            held.pre_test_screen_seen = self.pre_test_screen_seen
                            held.scan = executor.submit(
                                self._scan_frame,
                                held.camera_frame_number,
                                held.image,
                                qr_code_areas,
                                held.scanned_with,
                                held.scan_mode,
                                pre_test_screen_seen=held.pre_test_screen_seen,
                            )

                    detected_qr_codes = frame.scan.result()
                    self._record_frame_analysis(
                        frame.camera_frame_number, detected_qr_codes
                    )
                    new_capture_frame_num = self.process_detected_qr_codes(
                        detected_qr_codes, vid_cap, frame.frame_num_after_read
                    )

                    if new_capture_frame_num != frame.frame_num_after_read:
                        # processing this frame has already moved the capture, so
                        # the frames read behind it are stale and are discarded;
                        # reading resumes from where the capture now is
                        for discarded in batch[index + 1 :]:
                            # nothing reads these results, and each holds its
                            # frame in memory until its scan is off the queue
                            discarded.scan.cancel()
                        reader.reposition(new_capture_frame_num)
                        break

        return reader.capture_frame_num
