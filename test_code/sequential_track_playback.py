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
Contributor: Eurofins Digital Product Testing UK Limited
"""
import importlib
import logging
import math

from .test import TestType
from typing import List, Optional
from configuration_parser import ConfigurationParser
from global_configurations import GlobalConfigurations
from dpctf_qr_decoder import MezzanineDecodedQr, TestStatusDecodedQr


logger = logging.getLogger(__name__)


class SequentialTrackPlayback:
    """SequentialTrackPlayback to handle test 
    sequential-track-playback.html
    regular-playback-of-chunked-content.html
    regular-playback-of-chunked-content-non-aligned-append.html
    out-of-order-loading.html
    fullscreen-playback-of-switching-sets.html
    playback-of-encrypted-content.html
    this is also a base class to other tests"""

    test_type: TestType
    """test type SEQUENTIAL|SWITCHING|SPLICING"""
    global_configurations: GlobalConfigurations
    """OF gloabal configuration"""
    observations: list
    """observations required for the test"""
    parameters: list
    """parameter list required to be read"""
    content_parameters: list
    """content related parameter list required to be read"""
    parameters_dict: dict
    """Built dictionary of all the test_config_parameters required by this test"""

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
            camera_frame_duration_ms: Duration of a single camera frame in msecs.
        """
        self._set_test_type()
        self._init_observations()
        self._init_parameters()
        self._load_parameters_dict(configuration_parser, test_path, test_code)

        self.global_configurations = global_configurations
        self.parameters_dict["camera_frame_rate"] = camera_frame_rate
        self.parameters_dict["camera_frame_duration_ms"] = camera_frame_duration_ms
        
    def _set_test_type(self) -> None:
        """set test type SEQUENTIAL|SWITCHING|SPLICING"""
        self.test_type = TestType.SEQUENTIAL

    def _init_observations(self) -> None:
        """initialise the observations required for the test"""
        self.observations = [
            ("every_sample_rendered", "EverySampleRendered"),
            ("duration_matches_cmaf_track", "DurationMatchesCMAFTrack"),
            ("start_up_delay", "StartUpDelay"),
            ("sample_matches_current_time", "SampleMatchesCurrentTime"),
        ]

    def _init_parameters(self) -> None:
        """initialise the test_config_parameters required for the test"""
        self.parameters = [
            "ts_max",
            "tolerance",
            "frame_tolerance",
            "duration_tolerance",
            "duration_frame_tolerance"
        ]
        self.content_parameters = [
            "cmaf_track_duration"
        ]

    def _load_parameters_dict(
        self, configuration_parser: ConfigurationParser, test_path: str, test_code: str
    ) -> None:
        """load test_config_parameters dictionary from configuration
        get configuration from shared configuration file
        then add the content configuration from tests.json file
        """
        self.parameters_dict = configuration_parser.parse_test_config_json(
            self.parameters, test_path, test_code
        )
        self.parameters_dict.update(
            configuration_parser.parse_tests_json_content_config(
                self.content_parameters, test_path, "video"
            )
        )

    def _get_first_frame_num(self, _) -> int:
        """return first frame number"""
        return 1

    def _get_last_frame_num(self, frame_rate: float) -> int:
        """return last frame number"""
        return math.floor(self.parameters_dict["cmaf_track_duration"] / 1000 * frame_rate)

    def _get_expected_track_duration(self) -> float:
        """return expected track duration"""
        return self.parameters_dict["cmaf_track_duration"]

    def make_observations(
        self,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        test_status_qr_codes: List[TestStatusDecodedQr],
        time_diff_file: str,
    ) -> List[dict]:
        """Make observations for the Test 8.2

        Args:
            mezzanine_qr_codes: Sorted list of detected mezzanine QR codes.
            test_status_qr_codes: Sorted list of detected Test Runner status QR codes.

        Returns:
            List of pass/fail results.
        """
        results = []

        for observation in self.observations:
            # create instance of the relevant observation class
            observation_class = getattr(
                importlib.import_module("observations." + observation[0]),
                observation[1],
            )(self.global_configurations)

            frame_rate = mezzanine_qr_codes[-1].frame_rate
            self.parameters_dict["first_frame_num"] = self._get_first_frame_num(
                frame_rate
            )
            self.parameters_dict["last_frame_num"] = self._get_last_frame_num(
                frame_rate
            )
            self.parameters_dict[
                "expected_track_duration"
            ] = self._get_expected_track_duration()

            result = observation_class.make_observation(
                self.test_type,
                mezzanine_qr_codes,
                test_status_qr_codes,
                self.parameters_dict,
                time_diff_file,
            )
            results.append(result)

        return results
