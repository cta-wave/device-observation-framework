# -*- coding: utf-8 -*-
"""DPCTF device observation framework Global Configurations

loads global configurations form config.ini file
default values are used when file not found or value not defined 

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
import os
import configparser
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class GlobalConfigurations:
    """Global Configurations class"""

    config: configparser.RawConfigParser
    ignore_corrupted: str
    """special condition to ignore,
    used to ignore corrupted frames for some camera (e.g.: GoPro9)"""
    system_mode: str
    """system mode for debugging purpose only"""
    qr_search_range: List[int]
    """Runs the test runner over a specific range"""

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read("config.ini", "UTF-8")
        self.ignore = ""
        self.system_mode = ""
        self.qr_search_range = []
        self.ignore_corrupted = ""
        self.calibration_file_path = ""

    def set_qr_search_range(self, qr_search_range: str):
        """Set range"""
        if qr_search_range:
            temp_range = qr_search_range.split(":")
            if len(temp_range) != 3:
                raise ValueError("Not enough arguments specified for range")
            if (
                int(temp_range[0]) < 0
                or int(temp_range[1]) < 0
                or int(temp_range[2]) < 0
            ):
                raise ValueError("Input arguments for range must be positive integers")
            test_range = [int(num) for num in temp_range]
            self.qr_search_range = test_range

    def get_qr_search_range(self) -> List[int]:
        """Get range"""
        return self.qr_search_range

    def set_calibration_file_path(self, file_path: str):
        """Set calibration file path"""
        if file_path:
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            self.calibration_file_path = file_path

    def get_calibration_file_path(self) -> str:
        """Get calibration file path"""
        return self.calibration_file_path

    def set_ignore_corrupted(self, ignore_corrupted: str):
        """Set ignore"""
        self.ignore_corrupted = ignore_corrupted

    def get_ignore_corrupted(self) -> str:
        """Get ignore"""
        return self.ignore_corrupted

    def set_system_mode(self, mode: str):
        """Set system_mode"""
        self.system_mode = mode

    def get_system_mode(self) -> str:
        """Get system_mode"""
        return self.system_mode

    def get_sort_input_files_by(self) -> str:
        """Get sort_input_files_by"""
        try:
            sort_input_files_by = self.config["GENERAL"]["sort_input_files_by"]
        except KeyError:
            sort_input_files_by = ""

        return sort_input_files_by

    def get_log_file_path(self) -> str:
        """Get log_file_path"""
        try:
            log_file_path = self.config["GENERAL"]["log_file_path"]
        except KeyError:
            log_file_path = "logs"
        return log_file_path

    def get_result_file_path(self) -> str:
        """Get result_file_path"""
        try:
            result_file_path = self.config["GENERAL"]["result_file_path"]
        except KeyError:
            result_file_path = "results"
        return result_file_path

    def get_audio_mezzanine_file_path(self) -> str:
        """Get audio_mezzanine_file_path"""
        try:
            audio_mezzanine_file_path = self.config["GENERAL"][
                "audio_mezzanine_file_path"
            ]
        except KeyError:
            audio_mezzanine_file_path = "audio_mezzanine"
        return audio_mezzanine_file_path

    def get_session_log_threshold(self) -> int:
        """Get session_log_threshold"""
        try:
            session_log_threshold = int(self.config["GENERAL"]["session_log_threshold"])
        except KeyError:
            session_log_threshold = 100
        return session_log_threshold

    def set_test_runner_url(self, test_runner_url: str):
        """Set test_runner_url"""
        self.config["GENERAL"]["test_runner_url"] = test_runner_url

    def get_test_runner_url(self) -> str:
        """Get test_runner_url"""
        try:
            test_runner_url = self.config["GENERAL"]["test_runner_url"]
            if not test_runner_url.endswith("/"):
                test_runner_url += "/"
        except KeyError:
            test_runner_url = "http://web-platform.test:8000/_wave/"
        return test_runner_url

    def get_missing_frame_threshold(self) -> int:
        """Get missing_frame_threshold"""
        try:
            missing_frame_threshold = int(
                self.config["GENERAL"]["missing_frame_threshold"]
            )
        except KeyError:
            missing_frame_threshold = 0
        return missing_frame_threshold

    def get_consecutive_no_qr_threshold(self) -> int:
        """Get consecutive_no_qr_threshold"""
        try:
            consecutive_no_qr_threshold = int(
                self.config["GENERAL"]["consecutive_no_qr_threshold"]
            )
        except KeyError:
            consecutive_no_qr_threshold = 0
        return consecutive_no_qr_threshold

    def get_end_of_session_timeout(self) -> int:
        """Get end_of_session_timeout"""
        try:
            end_of_session_timeout = int(
                self.config["GENERAL"]["end_of_session_timeout"]
            )
        except KeyError:
            end_of_session_timeout = 10
        return end_of_session_timeout

    def get_no_qr_code_timeout(self) -> int:
        """Get no_qr_code_timeout"""
        try:
            no_qr_code_timeout = int(self.config["GENERAL"]["no_qr_code_timeout"])
        except KeyError:
            no_qr_code_timeout = 5
        return no_qr_code_timeout

    def get_search_qr_area_to(self) -> int:
        """Get search_qr_area_to"""
        try:
            search_qr_area_to = int(self.config["GENERAL"]["search_qr_area_to"])
        except KeyError:
            search_qr_area_to = 60
        return search_qr_area_to

    def get_qr_area_margin(self) -> int:
        """Get qr_area_margin"""
        try:
            qr_area_margin = int(self.config["GENERAL"]["qr_area_margin"])
        except KeyError:
            qr_area_margin = 50
        return qr_area_margin

    def get_duplicated_qr_check_count(self) -> int:
        """Get duplicated_qr_check_count"""
        try:
            duplicated_qr_check_count = int(
                self.config["GENERAL"]["duplicated_qr_check_count"]
            )
        except KeyError:
            duplicated_qr_check_count = 3
        return duplicated_qr_check_count

    def get_audio_alignment_tolerance(self) -> int:
        """Get audio_alignment_tolerance"""
        try:
            audio_alignment_tolerance = int(
                self.config["GENERAL"]["audio_alignment_tolerance"]
            )
        except KeyError:
            audio_alignment_tolerance = 5
        return audio_alignment_tolerance

    def get_audio_observation_neighborhood(self) -> int:
        """Get audio_observation_neighborhood"""
        try:
            audio_observation_neighborhood = int(
                self.config["GENERAL"]["audio_observation_neighborhood"]
            )
        except KeyError:
            audio_observation_neighborhood = 500
        return audio_observation_neighborhood

    def get_audio_alignment_check_count(self) -> int:
        """Get audio_alignment_check_count"""
        try:
            audio_alignment_check_count = int(
                self.config["GENERAL"]["audio_alignment_check_count"]
            )
        except KeyError:
            audio_alignment_check_count = 10
        return audio_alignment_check_count

    def get_max_search_frames_for_video_shift(self) -> int:
        """Get max_search_frames_for_video_shift"""
        try:
            max_search_frames_for_video_sift = int(
                self.config["GENERAL"]["max_search_frames_for_video_shift"]
            )
        except KeyError:
            max_search_frames_for_video_sift = 16
        return max_search_frames_for_video_sift

    def get_enable_cropped_scan_for_pre_test_qr(self) -> bool:
        """Get enable_cropped_scan_for_pre_test_qr"""
        try:
            config_value = self.config["GENERAL"]["enable_cropped_scan_for_pre_test_qr"]
            if config_value == "True":
                enable_cropped_scan_for_pre_test_qr = True
            else:
                enable_cropped_scan_for_pre_test_qr = False
        except KeyError:
            enable_cropped_scan_for_pre_test_qr = False
        return enable_cropped_scan_for_pre_test_qr

    def get_tolerances(self) -> Dict[str, int]:
        """Get tolerances"""
        tolerances = {
            "start_frame_num_tolerance": 0,
            "end_frame_num_tolerance": 0,
            "mid_frame_num_tolerance": 0,
            "splice_start_frame_num_tolerance": 0,
            "splice_end_frame_num_tolerance": 0,
            "start_segment_num_tolerance": 0,
            "end_segment_num_tolerance": 0,
            "mid_segment_num_tolerance": 0,
            "splice_start_segment_num_tolerance": 0,
            "splice_end_segment_num_tolerance": 0,
            "earliest_sample_alignment_tolerance": 0,
            "av_sync_start_tolerance": 0,
            "av_sync_end_tolerance": 0,
            "av_sync_pass_rate": 100,
        }
        try:
            tolerances["start_frame_num_tolerance"] = int(
                self.config["TOLERANCES"]["start_frame_num_tolerance"]
            )
            tolerances["end_frame_num_tolerance"] = int(
                self.config["TOLERANCES"]["end_frame_num_tolerance"]
            )
            tolerances["mid_frame_num_tolerance"] = int(
                self.config["TOLERANCES"]["mid_frame_num_tolerance"]
            )
            tolerances["splice_start_frame_num_tolerance"] = int(
                self.config["TOLERANCES"]["splice_start_frame_num_tolerance"]
            )
            tolerances["splice_end_frame_num_tolerance"] = int(
                self.config["TOLERANCES"]["splice_end_frame_num_tolerance"]
            )
            tolerances["start_segment_num_tolerance"] = int(
                self.config["TOLERANCES"]["start_segment_num_tolerance"]
            )
            tolerances["end_segment_num_tolerance"] = int(
                self.config["TOLERANCES"]["end_segment_num_tolerance"]
            )
            tolerances["mid_segment_num_tolerance"] = int(
                self.config["TOLERANCES"]["mid_segment_num_tolerance"]
            )
            tolerances["splice_start_segment_num_tolerance"] = int(
                self.config["TOLERANCES"]["splice_start_segment_num_tolerance"]
            )
            tolerances["splice_end_segment_num_tolerance"] = int(
                self.config["TOLERANCES"]["splice_end_segment_num_tolerance"]
            )
            tolerances["earliest_sample_alignment_tolerance"] = int(
                self.config["TOLERANCES"]["earliest_sample_alignment_tolerance"]
            )
            tolerances["av_sync_start_tolerance"] = int(
                self.config["TOLERANCES"]["av_sync_start_tolerance"]
            )
            tolerances["av_sync_end_tolerance"] = int(
                self.config["TOLERANCES"]["av_sync_end_tolerance"]
            )
            tolerances["av_sync_pass_rate"] = int(
                self.config["TOLERANCES"]["av_sync_pass_rate"]
            )
        except KeyError:
            pass
        return tolerances

    def get_calibration(self) -> Dict[str, float]:
        """Get camera calibration configuration settings"""
        calibration = {
            "flash_and_beep_count": 60,
            "max_allowed_offset": 200,
            "allowed_offset": 40,
            "flash_threshold": 150,
            "x_ratio": 0.5,
            "y_ratio": 0.25,
            "window_size": 50,
            "fade_out_frames": 5,
            "beep_threshold": 0.3,
            "min_silence_duration": 0.9,
        }
        try:
            calibration["start_frame_num_tolerance"] = float(
                self.config["CALIBRATION"]["flash_and_beep_count"]
            )
            calibration["max_allowed_offset"] = float(
                self.config["CALIBRATION"]["max_allowed_offset"]
            )
            calibration["allowed_offset"] = float(
                self.config["CALIBRATION"]["allowed_offset"]
            )
            calibration["flash_threshold"] = float(
                self.config["CALIBRATION"]["flash_threshold"]
            )
            calibration["x_ratio"] = float(self.config["CALIBRATION"]["x_ratio"])
            calibration["y_ratio"] = float(self.config["CALIBRATION"]["y_ratio"])
            calibration["fade_out_frames"] = float(
                self.config["CALIBRATION"]["fade_out_frames"]
            )
            calibration["beep_threshold"] = float(
                self.config["CALIBRATION"]["beep_threshold"]
            )
            calibration["min_silence_duration"] = float(
                self.config["CALIBRATION"]["min_silence_duration"]
            )
        except KeyError:
            pass
        return calibration
