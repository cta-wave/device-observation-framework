# -*- coding: utf-8 -*-
"""DPCTF device observation test code sequential_track_playback

test random_access_to_fragment

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
import logging
import math
from fractions import Fraction
from typing import List, Tuple

from audio_file_reader import read_audio_mezzanine
from configuration_parser import ConfigurationParser
from dpctf_audio_decoder import decode_audio_segments
from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr
from exceptions import AudioAlignError
from global_configurations import GlobalConfigurations
from output_file_handler import audio_data_to_csv

from .test import TestContentType, TestType

logger = logging.getLogger(__name__)

# Capturing frame rate shall be close to twice the test frame rate
# add warning if frame rate of recording is less than 1.5 of test content
RECORDING_FRAME_RATE_RATIO = 1.5


class SequentialTrackPlayback:
    """SequentialTrackPlayback to handle test
    sequential-track-playback.html
    regular-playback-of-chunked-content.html
    regular-playback-of-chunked-content-non-aligned-append.html
    out-of-order-loading.html
    fullscreen-playback-of-switching-sets.html
    playback-of-encrypted-content.html
    this is also a base class to other tests"""

    error_message: str
    """System error message"""
    test_type: TestType
    """test type SEQUENTIAL|SWITCHING|SPLICING"""
    test_content_type: TestContentType
    """test type SINGLE|COMBINED"""
    global_configurations: GlobalConfigurations
    """OF global configuration"""
    observations: list
    """observations required for the test"""
    parameters: list
    """parameter list required to be read"""
    content_parameters: list
    """content related parameter list required to be read"""
    content_type: str
    """test content type is determined by the linked content"""
    parameters_dict: dict
    """Built dictionary of all the test_config_parameters required by this test"""
    concat_list: list
    """List of file names that will be concatenated"""

    def __init__(
        self,
        configuration_parser: ConfigurationParser,
        global_configurations: GlobalConfigurations,
        test_path: str,
        test_code: str,
        camera_frame_rate: float,
        camera_frame_duration_ms: float,
    ):
        """
        Args:
            configuration_parser: Handler to parse the test-specific config test_config_parameters.
            global_configurations: Generic config test_config_parameters.
            test_path: Test's path as read from Test Runner's tests.json.
            test_code: Test's code as read from Test Runner's tests.json.
            camera_frame_rate: Frames per second that the camera was recording at.
            camera_frame_duration_ms: Duration of a single camera frame in milliseconds.
        """
        self.error_message = ""

        self._set_test_type()
        self._set_test_content_type()
        self._set_content_type(configuration_parser)
        self._check_frame_rate_is_sufficient(configuration_parser, camera_frame_rate)
        self._init_parameters()
        self._load_parameters_dict(configuration_parser, test_path, test_code)
        self._load_contents_parameters(configuration_parser, test_path)
        self._init_observations()

        self.global_configurations = global_configurations
        self.parameters_dict["camera_frame_rate"] = camera_frame_rate
        self.parameters_dict["camera_frame_duration_ms"] = camera_frame_duration_ms

    def _set_test_type(self) -> None:
        """set test type SEQUENTIAL|SWITCHING|SPLICING"""
        self.test_type = TestType.SEQUENTIAL

    def _set_test_content_type(self) -> None:
        """set test type SINGLE|COMBINED"""
        self.test_content_type = TestContentType.SINGLE

    def _set_content_type(self, configuration_parser: ConfigurationParser) -> None:
        """either video or audio test is determined by the linked content"""
        self.content_type = configuration_parser.get_test_content_type(
            self.test_content_type
        )

    def _check_frame_rate_is_sufficient(
        self,
        configuration_parser: ConfigurationParser,
        camera_frame_rate: float,
    ) -> None:
        """check if frame rate of recording is sufficient for test being run"""
        frame_rates = configuration_parser.get_frame_rates(self.content_type)
        for frame_rate in frame_rates:
            if camera_frame_rate < frame_rate * RECORDING_FRAME_RATE_RATIO:
                self.error_message += (
                    f"Frame rate of recording {round(camera_frame_rate, 2)} fps "
                    f"is insufficient for test being run. "
                    f"Capturing frame rate shall be close to twice the test frame rate. "
                )
                logger.error(self.error_message)
                break

    def _init_observations(self) -> None:
        """initialise the observations required for the test"""
        if "video" in self.content_type:
            self.observations = [
                ("every_sample_rendered", "EverySampleRendered"),
                ("duration_matches_cmaf_track", "DurationMatchesCMAFTrack"),
                ("start_up_delay", "StartUpDelay"),
                ("sample_matches_current_time", "SampleMatchesCurrentTime"),
            ]
        else:
            self.observations = [
                ("audio_every_sample_rendered", "AudioEverySampleRendered"),
                ("audio_duration_matches_cmaf_track", "AudioDurationMatchesCMAFTrack"),
                ("audio_start_up_delay", "AudioStartUpDelay"),
            ]

    def _init_parameters(self) -> None:
        """initialise the test_config_parameters required for the test"""
        self.parameters = [
            "ts_max",
            "tolerance",
            "frame_tolerance",
            "duration_tolerance",
            "duration_frame_tolerance",
            "audio_sample_length",
            "audio_tolerance",
            "audio_sample_tolerance",
        ]

    def _load_parameters_dict(
        self,
        configuration_parser: ConfigurationParser,
        test_path: str,
        test_code: str,
    ) -> None:
        """load test_config_parameters dictionary from configuration
        get configuration from shared configuration file
        then add the content configuration from tests.json file
        """
        # Parse shared configurations
        self.parameters_dict = configuration_parser.parse_test_config_json(
            self.parameters, test_path, test_code
        )

    def _load_contents_parameters(
        self, configuration_parser: ConfigurationParser, test_path: str
    ) -> None:
        """loads content parameters from parsing content configuration file"""
        # set defined content_duration
        self.parameters_dict.update(
            configuration_parser.get_content_duration(
                test_path, self.get_content_type()
            )
        )

        # set defined fragment durations
        self.parameters_dict.update(
            configuration_parser.get_fragment_durations(
                test_path, self.get_content_type(), self.test_type
            )
        )

        # set defined source for audio tests
        self.parameters_dict.update(
            configuration_parser.get_source(test_path, self.get_content_type())
        )

        # getting audio sample rate
        self.parameters_dict.update(
            configuration_parser.get_sample_rate(self.get_content_type())
        )

    def get_content_type(self) -> str:
        """
        return content type of the test
            video: only video content is provided
            videoaudio: both video and audio content is provided
            audio: only audio content is provided
        """
        return self.content_type

    def _get_first_frame_num(self, _frame_rate: Fraction) -> int:
        """return first frame number"""
        return 1

    def _get_last_frame_num(self, frame_rate: Fraction) -> int:
        """return last frame number"""
        half_frame_duration = (1000 / frame_rate) / 2
        return math.floor(
            (self.parameters_dict["video_content_duration"] + half_frame_duration)
            / 1000
            * frame_rate
        )

    def _get_gap_from_and_to_frames(self, _frame_rate: Fraction):
        """return gap from and to frames"""
        # no gap in playback is expected for this test
        return []

    def _save_expected_video_track_duration(self) -> None:
        """save expected video track duration"""
        self.parameters_dict["expected_video_track_duration"] = self.parameters_dict[
            "video_content_duration"
        ]

    def _save_expected_audio_track_duration(self) -> None:
        """save expected audio track duration"""
        self.parameters_dict["expected_audio_track_duration"] = self.parameters_dict[
            "audio_content_duration"
        ]

    def _save_audio_data(self, _unused, _unused2, _unused3) -> None:
        """Does nothing in sequential. Override methods exist in random access
        to time and to fragment"""
        del _unused, _unused2, _unused3

    def _get_audio_segment_data(
        self, audio_content_ids: list
    ) -> Tuple[float, list, list]:
        """
        get expected audio mezzanine data for the test
            start_media_time: start time of expected audio
            expected_audio_segment_data: list of expected audio data
            unexpected_audio_segment_data: unexpected audio data
        """
        expected_audio_segment_data = read_audio_mezzanine(
            self.global_configurations, audio_content_ids[0]
        )
        return (0.0, [expected_audio_segment_data], [])

    def _save_audio_starting_time(self) -> None:
        """save audio starting time"""
        self.parameters_dict["audio_starting_time"] = 0.0

    def _save_audio_ending_time(self) -> None:
        """save audio ending time"""
        self.parameters_dict["audio_ending_time"] = self.parameters_dict[
            "audio_content_duration"
        ]

    def _get_audio_segments(
        self,
        audio_content_ids: list,
        audio_subject_data: list,
        observation_data_export_file: str,
    ) -> tuple:
        """Calculate the offset timings for an each audio segment"""
        if not audio_subject_data:
            raise AudioAlignError("The recorded audio data is empty.")

        sample_rate = self.parameters_dict["sample_rate"]
        audio_sample_length = self.parameters_dict["audio_sample_length"]
        self.parameters_dict["observation_period"] = sample_rate * audio_sample_length

        (
            start_media_time,
            expected_audio_segment_data_list,
            unexpected_audio_segment_data,
        ) = self._get_audio_segment_data(audio_content_ids)

        offset, audio_segments = decode_audio_segments(
            start_media_time,
            expected_audio_segment_data_list,
            audio_subject_data,
            sample_rate,
            audio_sample_length,
            self.global_configurations,
            observation_data_export_file,
        )

        self.parameters_dict["offset"] = offset
        self._save_audio_starting_time()
        self._save_audio_ending_time()
        self._save_audio_data(
            audio_subject_data,
            expected_audio_segment_data_list[0],
            unexpected_audio_segment_data,
        )

        return audio_segments

    def make_observations(
        self,
        audio_test_start_time: int,
        audio_subject_data: list,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        test_status_qr_codes: List[TestStatusDecodedQr],
        observation_data_export_file: str,
    ) -> List[dict]:
        """Make observations for the Test 8.2

        Args:
            audio_test_start_time: test start time in msec.
            audio_subject_data: recorded audio data.
            mezzanine_qr_codes: Sorted list of detected mezzanine QR codes.
            test_status_qr_codes: Sorted list of detected Test Runner status QR codes.

        Returns:
            List of pass/fail results.
        """
        results = []
        audio_segments = []
        self.concat_list = []
        self.parameters_dict["mid_missing_frame_duration"] = []

        if "video" in self.content_type:
            self._save_expected_video_track_duration()
            if mezzanine_qr_codes:
                frame_rate = mezzanine_qr_codes[-1].frame_rate
                self.parameters_dict["first_frame_num"] = self._get_first_frame_num(
                    frame_rate
                )
                self.parameters_dict["last_frame_num"] = self._get_last_frame_num(
                    frame_rate
                )
                self.parameters_dict["gap_from_and_to_frames"] = (
                    self._get_gap_from_and_to_frames(frame_rate)
                )

        if "audio" in self.content_type:
            self._save_expected_audio_track_duration()
            self.parameters_dict["audio_test_start_time"] = audio_test_start_time
            try:
                audio_segments = self._get_audio_segments(
                    self.parameters_dict["audio_content_ids"],
                    audio_subject_data,
                    observation_data_export_file,
                )
            except AudioAlignError as exc:
                logger.error("Unable to get audio segments: %s", exc)

            # Exporting time diff data to a CSV file
            if logger.getEffectiveLevel() == logging.DEBUG:
                if observation_data_export_file and audio_segments:
                    audio_data_to_csv(
                        observation_data_export_file + "_audio_segment_data.csv",
                        audio_segments,
                        self.parameters_dict,
                    )

        for observation in self.observations:
            # create instance of the relevant observation class
            observation_class = getattr(
                importlib.import_module("observations." + observation[0]),
                observation[1],
            )(self.global_configurations)

            result, updated_audio_segments, mid_missing_frame_duration = (
                observation_class.make_observation(
                    self.test_type,
                    mezzanine_qr_codes,
                    audio_segments,
                    test_status_qr_codes,
                    self.parameters_dict,
                    observation_data_export_file,
                )
            )
            # update mid_missing_frame_duration to use it on duration check
            if mid_missing_frame_duration:
                self.parameters_dict["mid_missing_frame_duration"] = (
                    mid_missing_frame_duration
                )
            # update audio segment to remove out of order segments
            if updated_audio_segments:
                audio_segments = updated_audio_segments
            results.append(result)

        if self.error_message:
            for result in results:
                result["message"] = self.error_message + result["message"]

        return results
