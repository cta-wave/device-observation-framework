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
Licensor: Eurofins Digital Product Testing UK Limited
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
        self.config.read("config.ini")

    def get_system_mode(self) -> str:
        try:
            system_mode = self.config["GENERAL"]["system_mode"]
        except KeyError:
            system_mode = ""

        return system_mode

    def get_log_file(self) -> str:
        try:
            log_file = self.config["GENERAL"]["log_file"]
        except KeyError:
            log_file = "logs/observation_framework.log"
        return log_file

    def get_test_runner_url(self) -> str:
        try:
            test_runner_url = self.config["GENERAL"]["test_runner_url"]
        except KeyError:
            test_runner_url = "http://web-platform.test:8000"
        return test_runner_url

    def get_tolerances(self) -> Dict[str, int]:
        tolerances = {
            "start_frame_num_tolerance": 0,
            "end_frame_num_tolerance": 0,
            "mid_frame_num_tolerance": 0,
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
        except KeyError:
            pass
        return tolerances
