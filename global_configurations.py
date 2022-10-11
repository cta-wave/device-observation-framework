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
Contributor: Eurofins Digital Product Testing UK Limited
"""
import configparser
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class GlobalConfigurations:
    """Global Configurations class"""

    config: configparser.RawConfigParser

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read("config.ini", "UTF-8")

    def get_system_mode(self) -> str:
        """Get system_mode"""
        try:
            system_mode = self.config["GENERAL"]["system_mode"]
        except KeyError:
            system_mode = ""

        return system_mode

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

    def get_session_log_threshold(self) -> int:
        """Get session_log_threshold"""
        try:
            session_log_threshold = int(self.config["GENERAL"]["session_log_threshold"])
        except KeyError:
            session_log_threshold = 100
        return session_log_threshold

    def get_test_runner_url(self) -> str:
        """Get test_runner_url"""
        try:
            test_runner_url = self.config["GENERAL"]["test_runner_url"]
        except KeyError:
            test_runner_url = "http://web-platform.test:8000"
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
            duplicated_qr_check_count = int(self.config["GENERAL"]["duplicated_qr_check_count"])
        except KeyError:
            duplicated_qr_check_count = 3
        return duplicated_qr_check_count

    def get_tolerances(self) -> Dict[str, int]:
        """Get tolerances"""
        tolerances = {
            "start_frame_num_tolerance": 0,
            "end_frame_num_tolerance": 0,
            "mid_frame_num_tolerance": 0,
            "splice_start_frame_num_tolerance": 0,
            "splice_end_frame_num_tolerance": 0,
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
        except KeyError:
            pass
        return tolerances
