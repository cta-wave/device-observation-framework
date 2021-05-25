# -*- coding: utf-8 -*-
"""DPCTF device observation framework configuration parser

Load the configuration files from Test Runner
and parse it to the internal format.

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
from typing import Dict

import requests
import isodate
import json
from global_configurations import GlobalConfigurations


logger = logging.getLogger(__name__)


class ConfigurationParser:
    """Configuration Parsing class"""

    server_url: str
    """test runner server url to get configuration files from"""
    test_config_json: Dict[str, Dict[str, Dict[str, str]]]
    """loaded test_config.json file in string"""
    tests_json: Dict[str, Dict[str, Dict[str, str]]]
    """loaded tests_json file in string"""
    test_config: str
    """configuration part extracted from test.json file"""

    def __init__(self, global_configurations: GlobalConfigurations):
        self.server_url = global_configurations.get_test_runner_url()

        # if conf.ini DEBUG mode is set then read test configuration settings from
        # a local file (used for development), instead of retrieving from Test Runner.
        if (global_configurations.get_system_mode()) == "Debug":
            self.test_config_json = self._get_json_from_local("test-config.json")
            self.tests_json = self._get_json_from_local("tests.json")
        else:
            self.test_config_json = self._get_json_from_tr("test-config.json")
            self.tests_json = self._get_json_from_tr("tests.json")

    def parse_tests_json(self, test_id: str):
        """Parse tests json configuration data
        save content configuration data to parse separately
        """
        try:
            test_path = self.tests_json["tests"][test_id]["path"]
            test_code = self.tests_json["tests"][test_id]["code"]

            self.test_config = self.tests_json["tests"][test_id]["config"]

            return test_path, test_code
        except KeyError as e:
            raise Exception(e)

    def parse_tests_json_content_config(self, parameters: list, test_path: str) -> dict:
        """parse content related config parameters for current test"""
        parameters_dict = {}

        for parameter in parameters:
            if parameter == "period_duration":
                # TODO: hardcode this for now until the configuration is avalible on TR
                # assume the period_duration 2 or 3 if not raise exception here
                parameters_dict[parameter] = [20000, 20000, 20000]
                # parameters_dict[parameter] = [20000, 20000]
            else:
                try:
                    config_value = isodate.parse_duration(self.test_config[parameter])
                    ms = config_value.microseconds / 1000
                    s_to_ms = config_value.seconds * 1000
                    value = ms + s_to_ms
                    parameters_dict[parameter] = value
                except KeyError as e:
                    raise Exception(
                        f"Failed to get a parameter:{e} for the test '{test_path}'"
                    )

        return parameters_dict

    def parse_test_config_json(
        self, parameters: list, test_path: str, test_code: str
    ) -> dict:
        """parse test config parameters"""
        parameters_dict = {}

        for parameter in parameters:
            try:
                value = self.test_config_json[test_path][parameter]
                parameters_dict[parameter] = value
            except KeyError:
                try:
                    value = self.test_config_json[test_code][parameter]
                    parameters_dict[parameter] = value
                except KeyError:
                    try:
                        value = self.test_config_json["all"][parameter]
                        parameters_dict[parameter] = value
                    except KeyError as e:
                        raise Exception(
                            f"Failed to get a parameter:{e} for the test '{test_path}'"
                        )

        return parameters_dict

    def _get_json_from_tr(self, json_name: str) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Get configuration files from test runner"""
        try:
            r = requests.get(self.server_url + "/" + json_name)
            if r.status_code == 200:
                config_data = r.json()
                return config_data
            else:
                raise Exception(
                    f"Error: Failed to get configuration file from test runner {r.status_code}"
                )
        except requests.exceptions.RequestException as e:
            raise Exception(e)

    def _get_json_from_local(
        self, json_name: str
    ) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Get configuration files from local directory
        only for debugging
        """
        try:
            filename = "configuration/" + json_name
            with open(filename) as json_file:
                config_data = json.load(json_file)
                return config_data
        except requests.exceptions.RequestException as e:
            raise Exception(e)
