# -*- coding: utf-8 -*-
"""WAVE DPCTF result handler

Handles the observation result using the Test Runner API:
download current result from the Test Runner
add the observation result
and post the result back the Test Runner

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
import json
import logging
import os
from datetime import datetime
from json.decoder import JSONDecodeError
from typing import List

import requests

from exceptions import ConfigError, ObsFrameError
from global_configurations import GlobalConfigurations

logger = logging.getLogger(__name__)
OF_RESULT_PREFIX = "[OF]"


class ObservationResultHandler:
    """Class to handle observation results"""

    result_url: str
    """test runner server url to download and post result"""
    global_configurations: GlobalConfigurations
    observation_config: List[dict]
    """list of OF configuration dictionary"""

    def __init__(self, global_configurations: GlobalConfigurations):
        self.result_url = (
            global_configurations.get_test_runner_url() + "/_wave/api/results/"
        )
        self.global_configurations = global_configurations
        self.observation_config = global_configurations.get_tolerances()

    def _download_result(self, url: str, filename: str) -> None:
        """Get session result from the Test Runner

        Args:
            url: GET URL.
            filename: Results filename.

        Raises:
            ObsFrameError: if cannot open Results file or if error occurred while handling the request.
        """
        try:
            r = requests.request("GET", url)
        except requests.exceptions.RequestException as e:
            raise ObsFrameError(
                "Error: Request for session result from Test Runner failed."
            ) from e
        if r.status_code != 200:
            raise ObsFrameError(
                f"Error: Failed to get session result from Test Runner. Status= {r.status_code}"
            )
        try:
            with open(filename, "wb") as f:
                f.write(r.content)
        except IOError as e:
            raise ObsFrameError(
                f"Error: Unable to write the result file {filename}"
            ) from e

    def _write_json(self, data, filename: str) -> None:
        """write json data to the file"""
        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            raise ObsFrameError(
                f"Error: Unable to open the result file {filename}."
            ) from e

    def _update_subtest(self, subtests_data: list, observation_results: list) -> list:
        """return updated subtest field
        remove previous OF result - remove results that has observation framework prefix
        extend with new result
        """
        for subtest_result in subtests_data[:]:
            try:
                subtest_name = subtest_result["name"]
            except KeyError:
                continue

            if OF_RESULT_PREFIX in subtest_name:
                subtests_data.remove(subtest_result)

        subtests_data.extend(observation_results)
        return subtests_data

    def _save_result_to_file(
        self, filename: str, observation_results: List[dict], observation_time: str
    ) -> None:
        """save observation result to a result file"""
        try:
            with open(filename, "w") as f:
                data = {}
                data.update({"meta": {}})
                data["meta"].update({"datetime_observation": observation_time})
                data["meta"].update({"observation_config": self.observation_config})
                data.update({"results": observation_results})
                json.dump(data, f, indent=4)
        except IOError as e:
            raise ObsFrameError(
                f"Error: Unable to write the result file {filename}."
            ) from e

    def _update_result_file(
        self,
        filename: str,
        test_path: str,
        observation_results: List[dict],
        observation_time: str,
    ) -> None:
        """Update result json file to add observation result to subtest section"""
        try:
            matching_test_found = False
            with open(filename) as json_file:
                data = json.load(json_file)

                # add meta when it is not defined
                if not "meta" in data:
                    data.update({"meta": {}})
                data["meta"].update({"datetime_observation": observation_time})
                data["meta"].update({"observation_config": self.observation_config})

                for result_data in data["results"]:
                    if ("/" + test_path) == result_data["test"]:
                        result_data["subtests"] = self._update_subtest(
                            result_data["subtests"], observation_results
                        )
                        self._write_json(data, filename)
                        matching_test_found = True
                        break

            if not matching_test_found:
                raise ConfigError(
                    f"Failed to find matching test from test result file, observation results cannot be updated. "
                    f"Test path from tests.json is /{test_path}."
                )
        except IOError as e:
            raise ObsFrameError(
                f"Error: Unable to open the result file {filename}"
            ) from e
        except JSONDecodeError as e:
            raise ObsFrameError(f"Error: Unable to decode JSON from {filename}") from e
        except KeyError as e:
            raise KeyError(
                f"Error: Failed to get key from result file {filename}"
            ) from e

    def _import_result(self, url: str, filename: str) -> None:
        """Post session result to the Test Runner

        Args:
            url: POST URL.
            filename: Results filename.

        Raises:
            ObsFrameError: if cannot open Results file or  if error occurred while handling the request.
        """
        try:
            contents = open(filename, "rb").read()
        except IOError as e:
            raise ObsFrameError(
                f"Error: Unable to open the result file {filename}"
            ) from e

        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, data=contents)
        if response.status_code != 200:
            raise ObsFrameError(
                f"Error: Failed to post result to Test Runner. Status= {response.status_code}"
            )

    def _create_results_dir(self, filename: str) -> None:
        """Create a results directory if not already there"""
        if not os.path.exists(os.path.dirname(filename)):
            try:
                os.makedirs(os.path.dirname(filename))
            except OSError as e:
                raise ObsFrameError(
                    f"Error: Unable to create a results directory {filename}"
                ) from e

    def post_result(
        self, session_token: str, test_path: str, observation_results: List[dict]
    ) -> None:
        """Prepare post observation result by downloading current test result
        modify it to add new observation result
        and post it to the test runner
        """
        if session_token and test_path and observation_results:
            api_name = test_path.split("/")[0]
            result_file_path = self.global_configurations.get_result_file_path()

            filename = result_file_path + "/" + session_token + "/" + api_name + ".json"
            self._create_results_dir(filename)
            observation_time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            # if debug mode then just save results to a file
            # (only used for development)
            if (self.global_configurations.get_system_mode()) == "debug":
                debug_result_filename = (
                    result_file_path
                    + "/"
                    + session_token
                    + "/"
                    + test_path.replace("/", "-").replace(".html", "")
                    + "_debug.json"
                )
                self._save_result_to_file(
                    debug_result_filename, observation_results, observation_time_str
                )
            else:
                url = self.result_url + session_token + "/" + api_name + "/json"
                self._download_result(url, filename)
                self._update_result_file(
                    filename, test_path, observation_results, observation_time_str
                )
                self._import_result(url, filename)
