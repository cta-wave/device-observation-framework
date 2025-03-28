# -*- coding: utf-8 -*-
"""DPCTF device observation test code 
splicing_of_wave_program_with_baseline_constraints

test splicing_of_wave_program_with_baseline_constraints

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
import math
from typing import Tuple

from audio_file_reader import read_audio_mezzanine

from .playback_over_wave_baseline_splice_constraints import (
    PlaybackOverWaveBaselineSpliceConstraints,
)
from .test import TestContentType


class SplicingOfWaveProgramWithBaselineConstraints(
    PlaybackOverWaveBaselineSpliceConstraints
):
    """SplicingOfWaveProgramWithBaselineConstraints to handle test
    splicing-of-wave-program-with-baseline-constraints.html.
    This class is derived from PlaybackOverWaveBaselineSpliceConstraints
    and uses the same observations logic.
    """

    def _init_parameters(self) -> None:
        """initialise the test_config_parameters required for the test"""
        self.parameters = [
            "ts_max",
            "tolerance",
            "frame_tolerance",
            "playout",
            "duration_tolerance",
            "duration_frame_tolerance",
            "audio_sample_length",
            "audio_tolerance",
            "audio_sample_tolerance",
            "av_sync_tolerance",
        ]

    def _init_observations(self) -> None:
        """initialise the observations required for the test"""
        self.observations = [
            ("every_sample_rendered", "EverySampleRendered"),
            ("audio_every_sample_rendered", "AudioEverySampleRendered"),
            ("start_up_delay", "StartUpDelay"),
            ("audio_start_up_delay", "AudioStartUpDelay"),
            ("duration_matches_cmaf_track", "DurationMatchesCMAFTrack"),
            ("audio_duration_matches_cmaf_track", "AudioDurationMatchesCMAFTrack"),
            ("sample_matches_current_time", "SampleMatchesCurrentTime"),
            (
                "earliest_sample_same_presentation_time",
                "EarliestSampleSamePresentationTime",
            ),
            ("audio_video_synchronization", "AudioVideoSynchronization"),
        ]

    def _set_test_content_type(self) -> None:
        """set test type SINGLE|COMBINED"""
        self.test_content_type = TestContentType.COMBINED

    def _save_expected_audio_track_duration(self) -> None:
        """save expected audio track duration"""
        # audio should match video
        self.parameters_dict["expected_audio_track_duration"] = self.parameters_dict[
            "expected_video_track_duration"
        ]

    def _get_audio_segment_data(
        self, audio_content_ids: list
    ) -> Tuple[float, list, list]:
        """
        get expected audio mezzanine data for splicing test
        start_media_time: start time of expected audio
        expected_audio_segment_data: list of expected audio data
        unexpected_audio_segment_data: unexpected audio data
        """
        sample_rate = self.parameters_dict["sample_rate"]
        fragment_duration_multi_mpd = self.parameters_dict[
            "video_fragment_duration_multi_mpd"
        ]
        playouts = self.parameters_dict["playout"]
        audio_segment_data_list = []
        audio_mezzanine_data = []

        # loop through content ids getting audio mezzanine
        for i in range(len(audio_content_ids)):
            audio_mezzanine_data.append(
                read_audio_mezzanine(self.global_configurations, audio_content_ids[i])
            )

        # loop through playout fragments getting audio segment data
        pre_audio_mezzanine_id = playouts[0][0] - 1
        audio_segment_data = []
        for playout in playouts:
            fragment_id = playout[2]
            frag_start = 0
            for i in range(fragment_id - 1):
                key = (playout[0], playout[1], i + 1)
                frag_start += fragment_duration_multi_mpd[key]

            frag_end = 0
            for i in range(fragment_id):
                key = (playout[0], playout[1], i + 1)
                frag_end += fragment_duration_multi_mpd[key]

            start = math.floor(frag_start * sample_rate)
            end = math.floor(frag_end * sample_rate) - 1

            audio_mezzanine_id = playout[0] - 1
            if audio_mezzanine_id != pre_audio_mezzanine_id:
                audio_segment_data_list.append(audio_segment_data)
                audio_segment_data = []
            audio_segment_data.extend(
                audio_mezzanine_data[audio_mezzanine_id][start:end]
            )
            pre_audio_mezzanine_id = audio_mezzanine_id
        audio_segment_data_list.append(audio_segment_data)

        return 0.0, audio_segment_data_list, []

    def _save_audio_ending_time(self) -> None:
        """save audio ending time"""
        # audio should match video
        self.parameters_dict["audio_ending_time"] = self.parameters_dict[
            "expected_video_track_duration"
        ]
