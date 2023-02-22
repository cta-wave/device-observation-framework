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
import json
import logging
from typing import Dict, List
from fractions import Fraction

import isodate
import requests
from exceptions import ConfigError
from global_configurations import GlobalConfigurations

logger = logging.getLogger(__name__)


class ConfigurationParser:
    """Configuration Parsing class"""

    server_url: str
    """test runner server url to get configuration files from"""
    test_config_json: Dict[str, Dict[str, Dict[str, str]]]
    """loaded test_config.json file in string"""
    tests_json: Dict[str, Dict[str, List[Dict[str, Dict[str, str]]]]]
    """loaded tests_json file in string"""
    video_config: List[Dict[str, Dict[str, str]]]
    """video configuration part extracted from test.json file"""
    audio_config: List[Dict[str, Dict[str, str]]]
    """audio configuration part extracted from test.json file"""

    def __init__(self, global_configurations: GlobalConfigurations):
        self.server_url = global_configurations.get_test_runner_url()

        # if debug mode is set then read test configuration settings from
        # a local file (used for development), instead of retrieving from Test Runner.
        if (global_configurations.get_system_mode()) == "debug":
            self.test_config_json = self._get_json_from_local("test-config.json")
            self.tests_json = self._get_json_from_local("tests.json")
        else:
            self.test_config_json = self._get_json_from_tr("test-config.json")
            self.tests_json = self._get_json_from_tr("tests.json")

    def parse_config(self, content_type: str) -> List[Dict[str, Dict[str, str]]]:
        if content_type == "audio":
            test_config = self.audio_config
        else:
            test_config = self.video_config
        return test_config

    def parse_tests_json(self, test_id: str):
        """Parse tests json configuration data
        save content configuration data to parse separately
        """
        try:
            test_path = self.tests_json["tests"][test_id]["path"]
            test_code = self.tests_json["tests"][test_id]["code"]

            self.video_config = self.tests_json["tests"][test_id]["switchingSets"][
                "video"
            ]
            self.audio_config = self.tests_json["tests"][test_id]["switchingSets"][
                "audio"
            ]

            return test_path, test_code
        except KeyError as e:
            raise ConfigError(
                f"Unrecognised test id is detected. "
                f'Detected test id({test_id}) is not defined in "tests.json". '
            )

    def parse_fragment_duration(
        self,
        test_path: str,
        content_type: str,
        parameter: str,
        test_config: List[Dict[str, str]],
    ) -> dict:
        """parse fragment duration
        fragment_duration: single track playback
        fragment_duration_list: switching set
        fragment_duration_multi_mpd: multi-mpd switching sets
        """
        parameters_dict = {}
        if parameter == "fragment_duration":
            # fragment_duration is used for test when only one representation is used
            # for example: sequential playback
            for representation in test_config[0]["representations"].values():
                if representation["type"] == content_type:
                    try:
                        if representation["fragment_duration"] == None:
                            raise TypeError
                        # the multiplication happens so that we get the fragment duration in ms
                        # we are interested just about the first video representation's fragment duration
                        parameters_dict[parameter] = (
                            Fraction(str(representation["fragment_duration"])) * 1000
                        )
                        break
                    except (TypeError, KeyError) as e:
                        raise ConfigError(
                            f"Failed to get a parameter:{e} for the test '{test_path}'"
                        )
        elif parameter == "fragment_duration_list":
            # fragment_duration_list is used for tests when more then one representation is used
            # for example: switching set
            # this list is needed to identify the switching points, and to calculate durations
            parameters_dict[parameter] = {}
            rep_index = 1
            for representation in test_config[0]["representations"].values():
                if representation["type"] == content_type:
                    try:
                        if representation["fragment_duration"] == None:
                            raise TypeError
                        # the multiplication happens so that we get the fragment duration in ms
                        parameters_dict[parameter][rep_index] = (
                            representation["fragment_duration"] * 1000
                        )
                        rep_index += 1
                    except (TypeError, KeyError) as e:
                        raise ConfigError(
                            f"Failed to get a parameter:{e} for the test '{test_path}'"
                        )
        elif parameter == "fragment_duration_multi_mpd":
            # fragment_duration_multi_mpd is used for tests when more then one mpd is used
            # for splicing set. This is an 2D array, this list is needed to identify
            # the switching points and splicing point, and to calculate durations
            parameters_dict[parameter] = {}
            content_index = 1
            rep_index = 1
            for config in test_config:
                for representation in config["representations"].values():
                    if representation["type"] == content_type:
                        try:
                            if representation["fragment_duration"] == None:
                                raise TypeError
                            # the multiplication happens so that we get the fragment duration in ms
                            parameters_dict[parameter][(content_index, rep_index)] = (
                                representation["fragment_duration"] * 1000
                            )
                            rep_index += 1
                        except (TypeError, KeyError) as e:
                            raise ConfigError(
                                f"Failed to get a parameter:{e} for the test '{test_path}'"
                            )
                content_index += 1
                rep_index = 1

        return parameters_dict

    def parse_cmaf_track_duration(
        self, test_path: str, test_config: Dict[str, Dict[str, str]]
    ):
        """parse cmaf track duration to ms"""
        parameters_dict = {}
        try:
            config_value = isodate.parse_duration(test_config["cmaf_track_duration"])
            ms = config_value.microseconds / 1000
            s_to_ms = config_value.seconds * 1000
            value = ms + s_to_ms
            parameters_dict["cmaf_track_duration"] = value
        except KeyError as e:
            raise ConfigError(
                f"Failed to get a parameter:{e} for the test '{test_path}'"
            )
        return parameters_dict

    def parse_tests_json_content_config(
        self, parameters: list, test_path: str, content_type: str
    ) -> dict:
        """parse content related config parameters for current test"""
        parameters_dict = {}

        # parse video/audio configuration
        # TODO: audio parsing, audio observation not implemented
        test_config = self.parse_config(content_type)

        # parse parameter one by one
        for parameter in parameters:
            if parameter == "cmaf_track_duration":
                # cmaf_track_duration is only required in single mpd
                parameters_dict.update(
                    self.parse_cmaf_track_duration(test_path, test_config[0])
                )
            else:
                # parse fragment duration handled differently for single mpd and mutiple
                parameters_dict.update(
                    self.parse_fragment_duration(
                        test_path, content_type, parameter, test_config
                    )
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
                        # gap_duration by default is fragment_duration
                        # when undefined seek fragment_duration
                        if parameter == "gap_duration":
                            continue
                        else:
                            raise ConfigError(
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
                raise ConfigError(
                    f"Error: Failed to get configuration file from test runner {r.status_code}"
                )
        except requests.exceptions.RequestException as e:
            raise ConfigError(e)

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
            raise ConfigError(e)


class PlayoutParser:
    """Playout Utility Parsing class"""

    @staticmethod
    def get_switching_playout(playout: List[List[int]]) -> List[int]:
        """for switching set to extract track ID list
        switching set ID column 0 and the fragment ID column 2
        are ignored for swithing set tests
        """
        switching_playout = [i[1] for i in playout]
        return switching_playout

    @staticmethod
    def get_playout_sequence(switching_playout: List[int]):
        """for switching set return playout sequence
        playout_sequence: a list of track number to identify different track changes
        """
        playout_sequence = [switching_playout[0]]
        for i in range(1, len(switching_playout)):
            # when track change
            if switching_playout[i] != switching_playout[i - 1]:
                playout_sequence.append(switching_playout[i])
        return playout_sequence

    @staticmethod
    def get_splicing_period_list(
        playouts: List[List[int]], fragment_duration_multi_mpd: dict
    ) -> List[float]:
        """return period duration list of splicing
        e.g: [main duration, ad duration, main duration]
        """
        period_list = []
        current_period = 0
        switching_set = playouts[0][0]
        for playout in playouts:
            if playout[0] != switching_set:
                period_list.append(current_period)
                current_period = 0
                switching_set = playout[0]
            current_period += fragment_duration_multi_mpd[(playout[0], playout[1])]
        period_list.append(current_period)
        return period_list

    @staticmethod
    def get_change_type_list(playouts: List[List[int]]) -> List[str]:
        """save ecah change type in a list"""
        change_type_list = []
        switching_set = playouts[0][0]
        track_num = playouts[0][1]
        for playout in playouts:
            if playout[0] != switching_set:
                change_type_list.append("splicing")
            elif playout[1] != track_num:
                change_type_list.append("switching")
            switching_set = playout[0]
            track_num = playout[1]
        return change_type_list

    @staticmethod
    def get_ending_playout_list(playouts: List[List[int]]) -> List[List[int]]:
        """when content change save each previous ending playout"""
        ending_playout_list = []
        switching_set = playouts[0][0]
        track_num = playouts[0][1]
        for i, playout in enumerate(playouts):
            if playout[0] != switching_set or playout[1] != track_num:
                ending_playout_list.append(playouts[i - 1])
                switching_set = playout[0]
                track_num = playout[1]
        return ending_playout_list

    @staticmethod
    def get_starting_playout_list(playouts: List[List[int]]) -> List[List[int]]:
        """when content change save each current starting playout"""
        starting_playout_list = []
        switching_set = playouts[0][0]
        track_num = playouts[0][1]
        for playout in playouts:
            if playout[0] != switching_set or playout[1] != track_num:
                starting_playout_list.append(playout)
                switching_set = playout[0]
                track_num = playout[1]
        return starting_playout_list
