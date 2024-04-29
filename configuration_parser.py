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
Contributor: Resillion UK Limited
"""
import json
import logging
import math
from fractions import Fraction
from typing import Dict, List, Tuple

import isodate
import requests

from exceptions import ConfigError, ObsFrameTerminate
from global_configurations import GlobalConfigurations
from test_code.test import TestContentType, TestType

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

    def parse_tests_json(self, test_id: str):
        """
        Parse tests json configuration data
        save content configuration data to parse separately
        """
        try:
            test_path = self.tests_json["tests"][test_id]["path"]
            test_code = self.tests_json["tests"][test_id]["code"]
            # set video and audio configuration
            switchingSets_config = self.tests_json["tests"][test_id]["switchingSets"]
            self.video_config = switchingSets_config["video"]
            self.audio_config = switchingSets_config["audio"]
            return test_path, test_code
        except KeyError:
            raise ConfigError(
                f"Unrecognized test id is detected. "
                f'Detected test id({test_id}) is not defined in "tests.json". '
            )

    def get_switchingset_config(self, content_type: str) -> list:
        """Return the list of switchingset configuration"""
        if content_type == "video":
            switchingset_config = self.video_config
        else:
            switchingset_config = self.audio_config
        return switchingset_config

    def get_content_duration(self, test_path: str, content_type: str) -> dict:
        """get content durations from segment timeline or
        from cmaf track durations when segment timeline not defined"""
        results = {}
        if "video" in content_type:
            content_duration = self._get_content_duration(test_path, "video")
            results.update(content_duration)
        if "audio" in content_type:
            content_duration = self._get_content_duration(test_path, "audio")
            results.update(content_duration)
        return results

    def _get_content_duration(self, test_path: str, content_type: str) -> dict:
        """get content duration from audio or video config
        content_type is 'audio' or 'video'"""
        parameter = content_type + "_content_duration"
        track_duration = 0.0
        switchingset_config = self.get_switchingset_config(content_type)[0]
        segment_timeline = self._get_segment_timeline(switchingset_config)
        timescale = self._get_timescale(switchingset_config)

        if segment_timeline and timescale != 0:
            track_duration = self._calculate_track_duration_from_timeline(
                segment_timeline, timescale
            )
        else:
            # when segment_timelines or timescales not defined
            # get the duration from the CMAF track duration
            track_duration = self._get_cmaf_track_duration(test_path, content_type)
        return {parameter: track_duration}

    def _calculate_track_duration_from_timeline(
        self, segment_timeline: list, timescale: int
    ) -> float:
        """Calculate content duration in ms from timeline and timescale"""
        # Note: not parsing t we assume for 1st timeline t is always 0 and for others t not present
        total_duration = 0
        for segment in segment_timeline:
            # parse repeat r:repeat default is 1
            repeat = 1
            try:
                repeat += segment["r"]
            except KeyError:
                repeat = 1
            total_duration += repeat * segment["d"]
        total_duration_in_ms = (total_duration / timescale) * 1000
        return total_duration_in_ms

    def _get_segment_timeline(self, switchingset_config: dict) -> list:
        """get segment timeline for 1st switchingSets"""
        timeline = []
        try:
            timeline = switchingset_config["segmentTimeline"]
        except KeyError as e:
            return timeline
        return timeline

    def _get_timescale(self, switchingset_config: dict) -> list:
        """get list of timescales for 1st switchingSets"""
        timescale = 0
        try:
            timescale = switchingset_config["timescale"]
        except KeyError as e:
            return timescale
        return timescale

    def _get_source(self, test_path: str) -> dict:
        """Extracts the audio content id from 'source' values defined in
        tests.json file. Only required for audio source."""
        source_list = []
        # loop through each content and extract source
        for i in range(len(self.audio_config)):
            try:
                test_config = self.audio_config[i]
            except KeyError as error:
                raise ConfigError(
                    f"Failed to get a parameter:source for the test '{test_path}'"
                ) from error
            # Extracting mezzanine from 'source' string <sourceid_xxxxxx>
            source = test_config["source"].split("_")[0]
            source_list.append(source)
        return {"audio_content_ids": source_list}

    def get_source(self, test_path: str, content_type: str) -> dict:
        """Function called by test cases to set the source value within the parameter dict
        Only required for audio for now"""
        results = {}
        if "audio" in content_type:
            results.update(self._get_source(test_path))
        return results

    def _get_sample_rate(self) -> dict:
        """Extracts the audio sample rate in kHZ from tests.json"""
        sample_rate_list = []
        # audio switching not in scope only extract for the 1st representations
        for i in range(len(self.audio_config)):
            rep_id = next(iter(self.audio_config[i]["representations"]))
            audioSamplingRate = self.audio_config[i]["representations"][rep_id][
                "audioSamplingRate"
            ]
            # sample rate is in kHZ
            sample_rate_list.append(int(audioSamplingRate / 1000))
        # assume audio sample rate are same for splicing test main and ad
        sample_rate = sample_rate_list[0]
        return {"sample_rate": sample_rate}

    def get_sample_rate(self, content_type: str) -> dict:
        """Function called by test cases to set the sample rate value within the parameter dict"""
        results = {}
        if "audio" in content_type:
            results.update(self._get_sample_rate())
        return results

    def _get_cmaf_track_duration(self, test_path: str, content_type: str) -> float:
        """get the cmaf track duration from config
        only parse the 1st switching set, multiple switching sets handled separately"""
        result = 0
        switchingset_config = self.get_switchingset_config(content_type)[0]
        try:
            if (
                switchingset_config != []
                and "cmaf_track_duration" in switchingset_config
            ):
                video_config_value = isodate.parse_duration(
                    switchingset_config["cmaf_track_duration"]
                )
                ms = video_config_value.microseconds / 1000
                s_to_ms = video_config_value.seconds * 1000
                result = ms + s_to_ms
        except KeyError as e:
            raise ConfigError(
                f"Failed to get a parameter:{e} for the test '{test_path}'"
            )
        return result

    def get_fragment_durations(
        self, test_path: str, content_type: str, test_type: TestType
    ) -> Tuple[dict, bool, bool]:
        """returns a dictionary with relevant fragment durations
        _get_fragment_duration_multi_contents for SPLICING or TRUNCATED test
        _get_fragment_duration_multi_reps for SWITCHING test
        _get_fragment_duration for other test
        """
        results = {}
        if test_type == TestType.SPLICING or test_type == TestType.TRUNCATED:
            if "video" in content_type:
                results.update(
                    self._get_fragment_duration_multi_contents("video", test_path)
                )
            if "audio" in content_type:
                results.update(
                    self._get_fragment_duration_multi_contents("audio", test_path)
                )
        elif test_type == TestType.SWITCHING:
            if "video" in content_type:
                results.update(
                    self._get_fragment_duration_multi_reps("video", test_path)
                )
            if "audio" in content_type:
                results.update(
                    self._get_fragment_duration_multi_reps("audio", test_path)
                )
        else:
            if "video" in content_type:
                results.update(self._get_fragment_duration("video", test_path))
            if "audio" in content_type:
                results.update(self._get_fragment_duration("audio", test_path))
        return results

    def _get_fragment_duration(self, content_type: str, test_path: str) -> dict:
        """get the fragment duration for general playback
        set video_fragment_durations or audio_fragment_durations"""
        fragment_durations = []
        switchingset_config = self.get_switchingset_config(content_type)[0]
        segment_timeline = self._get_segment_timeline(switchingset_config)
        timescale = self._get_timescale(switchingset_config)
        parameter = content_type + "_fragment_durations"

        if segment_timeline and timescale != 0:
            # for general playback only parse segment_timeline from switchingSets level
            # not parse the representation level, assumed they are same
            fragment_durations = self._convert_timeline_to_fragment_duration_list(
                segment_timeline, timescale
            )
        else:
            fragment_durations = self._get_fragment_duration_from_mpd(
                content_type, test_path
            )
        return {parameter: fragment_durations}

    def _convert_timeline_to_fragment_duration_list(
        self, segment_timeline: list, timescale: int
    ) -> list:
        """get the fragment durations from segment timeline"""
        fragment_durations = []
        if segment_timeline and timescale != 0:
            for segment in segment_timeline:
                # parse repeat r:repeat default is 1
                repeat = 1
                try:
                    repeat += segment["r"]
                except KeyError:
                    repeat = 1
                for r in range(repeat):
                    fragment_durations.append(Fraction(segment["d"], timescale) * 1000)
        return fragment_durations

    def _get_fragment_durations_from_timeline(
        self, representation: dict, segment_timeline: list, timescale: int
    ) -> list:
        """read fragment_durations from timeline and timescale"""
        fragment_durations = []
        try:
            if not representation["segmentTimeline"] or not representation["timescale"]:
                raise TypeError
            # use own representation_segmentTimeline:
            fragment_durations = self._convert_timeline_to_fragment_duration_list(
                representation["segmentTimeline"], representation["timescale"]
            )
        except (TypeError, KeyError):
            fragment_durations = self._convert_timeline_to_fragment_duration_list(
                segment_timeline, timescale
            )
        return fragment_durations

    def _convert_fragment_duration_to_list(
        self, representation: dict, test_path: str
    ) -> list:
        """read representation fragment duration and cover to list"""
        fragment_duration_list = []
        try:
            if representation["fragment_duration"] is None:
                raise TypeError
            fragment_duration = (
                Fraction(str(representation["fragment_duration"])) * 1000
            )
            repeat = math.ceil(representation["duration"] / fragment_duration)
            for r in range(repeat):
                fragment_duration_list.append(fragment_duration)
        except (TypeError, KeyError) as e:
            raise ConfigError(
                f"Failed to get a parameter:{e} for the test '{test_path}'"
            )
        return fragment_duration_list

    def _get_fragment_duration_from_mpd(
        self, content_type: str, test_path: str
    ) -> list:
        """get the video fragment durations"""
        # fragment_duration is used for test when only one representation is used
        # for example: sequential playback
        fragment_duration_list = []
        switchingset_config = self.get_switchingset_config(content_type)[0]
        # we are interested just about the first video representations fragment duration
        for representation in switchingset_config["representations"].values():
            if representation["type"] == content_type:
                fragment_duration_list = self._convert_fragment_duration_to_list(
                    representation, test_path
                )
        return fragment_duration_list

    def _get_fragment_duration_multi_reps(
        self, content_type: str, test_path: str
    ) -> dict:
        """get the fragment duration lists for switching tests
        set video_fragment_duration_multi_reps or audio_fragment_duration_multi_reps"""
        # fragment_duration_list is used for tests when more then one representation is used
        # for example: switching set
        # this list is needed to identify the switching points, and to calculate durations
        results = {}
        parameter = content_type + "_fragment_duration_multi_reps"
        results[parameter] = {}

        switchingset_config = self.get_switchingset_config(content_type)[0]
        segment_timeline = self._get_segment_timeline(switchingset_config)
        timescale = self._get_timescale(switchingset_config)

        rep_index = 1
        for representation in switchingset_config["representations"].values():
            fragment_durations = []
            if representation["type"] == content_type:
                if timescale != 0 and segment_timeline:
                    fragment_durations = self._get_fragment_durations_from_timeline(
                        representation, segment_timeline, timescale
                    )
                else:
                    fragment_durations = self._convert_fragment_duration_to_list(
                        representation, test_path
                    )
                for i in range(len(fragment_durations)):
                    fragment_index = i + 1
                    results[parameter][(rep_index, fragment_index)] = (
                        fragment_durations[i]
                    )
                rep_index += 1

        return results

    def _get_fragment_duration_multi_contents(
        self, content_type: str, test_path: str
    ) -> dict:
        """get the video fragment duration multi mpds
        set video_fragment_duration_multi_mpd or audio_fragment_duration_multi_mpd
        return dictionary of fragment duration
            {(content_index, rep_index, fragment_index): fragment_duration}
        """
        results = {}
        parameter = content_type + "_fragment_duration_multi_mpd"
        results[parameter] = {}
        switchingset_config_list = self.get_switchingset_config(content_type)

        content_index = 1
        for switchingset_config in switchingset_config_list:
            segment_timeline = self._get_segment_timeline(switchingset_config)
            timescale = self._get_timescale(switchingset_config)

            rep_index = 1
            for representation in switchingset_config["representations"].values():
                fragment_durations = []
                if representation["type"] == content_type:
                    if timescale != 0 and segment_timeline:
                        fragment_durations = self._get_fragment_durations_from_timeline(
                            representation, segment_timeline, timescale
                        )
                    else:
                        fragment_durations = self._convert_fragment_duration_to_list(
                            representation, test_path
                        )
                for i in range(len(fragment_durations)):
                    fragment_index = i + 1
                    results[parameter][(content_index, rep_index, fragment_index)] = (
                        fragment_durations[i]
                    )
                rep_index += 1
            content_index += 1

        return results

    def get_test_content_type(self, test_content_type: TestContentType) -> str:
        """
        returns str with "content_type"
            videoaudio: for combined test in section 9
            video or audio: for single test in section 8
                when video configuration is defined returns 'video'
                else returns 'audio'
        """
        content_type = "video"
        if not self.video_config and not self.audio_config:
            raise ConfigError(
                "Failed to get content parameters from test configuration. "
                "Both video and audio are not defined."
            )
        if test_content_type == TestContentType.COMBINED:
            if not self.video_config or not self.video_config:
                raise ConfigError(
                    "Failed to get video or audio content parameters from test configuration. "
                    "Both video and audio should be defined."
                )
            content_type += "audio"
        else:
            if not self.video_config:
                content_type = "audio"
        return content_type

    def parse_test_config_json(
        self, parameters: list, test_path: str, test_code: str
    ) -> dict:
        """Parse shared configurations between test runner and observation framework
        Such as tolerances. Which are defined in 'test-config.json' file."""
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
                raise ObsFrameTerminate(
                    f"Failed to get configuration file from test runner {r.status_code}"
                )
        except requests.exceptions.RequestException as e:
            raise ObsFrameTerminate(
                f"Failed to get configuration file from test runner. {e}"
            )

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
        except FileNotFoundError as e:
            raise ObsFrameTerminate(
                f"Failed to get configuration file from local directory. {e}"
            )


class PlayoutParser:
    """Playout Utility Parsing class"""

    @staticmethod
    def get_playout_sequence(playout: list):
        """for switching set return playout sequence
        playout_sequence: a list of track number to identify different track changes
        """
        playout_sequence = [playout[0][1]]
        for i in range(1, len(playout)):
            # when track change
            if playout[i][1] != playout[i - 1][1]:
                playout_sequence.append(playout[i][1])
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
            current_period += fragment_duration_multi_mpd[tuple(playout)]
        period_list.append(current_period)
        return period_list

    @staticmethod
    def get_change_type_list(playouts: List[List[int]]) -> List[str]:
        """save each change type in a list"""
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
