# -*- coding: utf-8 -*-
# pylint: disable=import-error
"""observation audio_video_synchronization

make observation of audio_video_synchronization

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
import logging
import statistics
import sys
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt

from dpctf_audio_decoder import AudioSegment
from global_configurations import GlobalConfigurations
from dpctf_qr_decoder import MezzanineDecodedQr
from output_file_handler import write_data_to_csv_file

from .observation import Observation


class AudioVideoSynchronization(Observation):
    """AudioVideoSynchronization class
    The mediaTime of the presented audio sample matches the one reported by
    the video currentTime value within the tolerance.
    """

    def __init__(self, global_configurations: GlobalConfigurations):
        super().__init__(
            "[OF] Audio-Video Synchronization.",
            global_configurations,
        )

    def _calculate_video_offsets(
        self,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        camera_frame_duration_ms: float,
        observation_data_export_file: str,
    ) -> List[Tuple]:
        """calculate video offsets"""
        video_data = []
        video_offsets = []

        for j in range(0, len(mezzanine_qr_codes)):
            # calculate mean detection time based on 1st and last qr code detection time
            first_detection_time = (
                mezzanine_qr_codes[j].first_camera_frame_num * camera_frame_duration_ms
            )
            last_detection_time = (
                mezzanine_qr_codes[j].last_camera_frame_num * camera_frame_duration_ms
            )
            video_frame_duration = 1000 / mezzanine_qr_codes[j].frame_rate

            if j == 0:
                # 1st frame might rendered before play so take the last detection time
                mean_detection_time = last_detection_time
                video_media_time = mezzanine_qr_codes[j].media_time
            elif j == len(mezzanine_qr_codes) - 1:
                # last frame might rendered after play stopped so take the first detection time
                mean_detection_time = first_detection_time
                video_media_time = (
                    mezzanine_qr_codes[j].media_time - video_frame_duration
                )
            else:
                mean_detection_time = (
                    first_detection_time
                    + (last_detection_time - first_detection_time) / 2
                )
                # covert media time to show half position of each media
                video_media_time = (
                    mezzanine_qr_codes[j].media_time - video_frame_duration / 2
                )

            # calculate offset of each detection frames
            video_offset = mean_detection_time - video_media_time
            clean_video_offset = int(
                round(video_offset / video_frame_duration, 0) * video_frame_duration
            )
            video_offsets.append((video_media_time, clean_video_offset))

            # debugging only remove this when done
            video_data.append(
                (
                    mezzanine_qr_codes[j].frame_number,
                    video_media_time,
                    mean_detection_time,
                    first_detection_time,
                    last_detection_time,
                    video_offset,
                    clean_video_offset,
                )
            )

        if (
            self.logger.getEffectiveLevel() == logging.DEBUG
            and observation_data_export_file
        ):
            write_data_to_csv_file(
                observation_data_export_file + "video_data.csv",
                [
                    "frame_number",
                    "mean_media_time",
                    "mean_detection mean",
                    "first",
                    "last",
                    "offset",
                    "clean_offset",
                ],
                video_data,
            )

        return video_offsets

    def _calculate_audio_offsets(
        self,
        audio_segments: List[AudioSegment],
        parameters_dict: dict,
        observation_data_export_file: str,
    ) -> List[Tuple]:
        """calculate audio offsets"""
        audio_offsets = []
        audio_sample_length = parameters_dict["audio_sample_length"]
        test_start_time = parameters_dict["audio_test_start_time"]

        for i in range(0, len(audio_segments)):
            # audio mean time set to half position of each sample
            mean_time = audio_segments[i].media_time + audio_sample_length / 2
            # calculate offset of half position of each audio sample
            audio_offset = (
                test_start_time
                + audio_segments[i].audio_segment_timing
                - audio_segments[i].media_time
            )
            audio_offsets.append(
                (
                    audio_segments[i].audio_content_id,
                    audio_segments[i].media_time,
                    mean_time,
                    audio_offset,
                )
            )

        if (
            self.logger.getEffectiveLevel() == logging.DEBUG
            and observation_data_export_file
        ):
            write_data_to_csv_file(
                observation_data_export_file + "audio_data.csv",
                ["content id", "media time", "mean_time", "offsets"],
                audio_offsets,
            )
        return audio_offsets

    def make_observation(
        self,
        _test_type,
        mezzanine_qr_codes: List[MezzanineDecodedQr],
        audio_segments: List[AudioSegment],
        _test_status_qr_codes,
        parameters_dict: dict,
        observation_data_export_file: str,
    ) -> Tuple[Dict[str, str], list, list]:
        """make observation

        Args:
            test_type: defined in test.py
            mezzanine_qr_codes: detected QR codes list from Mezzanine.
            audio_segments: Ordered list of audio segment found.
            parameters_dict: parameters are from test runner config file
            and some are generated from OF.

        Returns:
            Result status and message.
        """
        self.logger.info("Making observation %s.", self.result["name"])

        if not mezzanine_qr_codes:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = "No mezzanine QR code is detected."
            self.logger.info("[%s] %s", self.result["status"], self.result["message"])
            return self.result, [], []

        if not audio_segments:
            self.result["status"] = "NOT_RUN"
            self.result["message"] = "No audio segment is detected."
            self.logger.info("[%s] %s", self.result["status"], self.result["message"])
            return self.result, [], []

        audio_offsets = []
        video_offsets = []
        time_differences = []
        # unrounded, so the tolerance check is exact
        filtered_diffs = []

        camera_frame_duration_ms = parameters_dict["camera_frame_duration_ms"]
        audio_sample_length = parameters_dict["audio_sample_length"]
        av_sync_tolerance = parameters_dict["av_sync_tolerance"]
        av_sync_start_tolerance = self.tolerances["av_sync_start_tolerance"]
        av_sync_end_tolerance = self.tolerances["av_sync_end_tolerance"]
        av_sync_pass_rate = self.tolerances["av_sync_pass_rate"]
        self.result["message"] += (
            f"The allowed AV sync tolerance is {av_sync_tolerance} ms. "
            f"The starting tolerance is {av_sync_start_tolerance}ms and "
            f"the ending tolerance is {av_sync_end_tolerance}ms. "
            f"The required pass rate is {av_sync_pass_rate}%. "
        )
        check_from = parameters_dict["audio_starting_time"] + av_sync_start_tolerance
        check_to = parameters_dict["audio_ending_time"] - av_sync_end_tolerance

        # calculate video offsets
        video_offsets = self._calculate_video_offsets(
            mezzanine_qr_codes, camera_frame_duration_ms, observation_data_export_file
        )
        audio_offsets = self._calculate_audio_offsets(
            audio_segments, parameters_dict, observation_data_export_file
        )

        for i in range(0, len(audio_offsets)):
            # set time_diff to max
            time_diff = sys.float_info.max
            for j in range(0, len(video_offsets)):
                # find the matching audio / video based on the same media time
                # the differences should be less than an audio sample length
                # if longer the matches not found
                # ignore the audio samples which failed to find matching audio
                # where the sync is not measurable
                if abs(audio_offsets[i][2] - video_offsets[j][0]) < audio_sample_length:
                    # check next video in case its media time is a better match
                    if j < len(video_offsets) - 1 and abs(
                        audio_offsets[i][2] - video_offsets[j + 1][0]
                    ) < abs(audio_offsets[i][2] - video_offsets[j][0]):
                        j += 1
                    # positive when audio leads video, as in ITU-R BT.1359
                    time_diff = video_offsets[j][1] - audio_offsets[i][3]
                    break

            # ignore those failing audio and video matches
            if time_diff == sys.float_info.max:
                continue

            time_differences.append((audio_offsets[i][2], round(time_diff, 2)))
            if check_from <= audio_offsets[i][2] <= check_to:
                filtered_diffs.append(time_diff)

        lead_failure_count = sum(1 for diff in filtered_diffs if diff > av_sync_tolerance[0])
        lag_failure_count = sum(1 for diff in filtered_diffs if diff < av_sync_tolerance[1])
        matched_count = len(filtered_diffs)
        in_sync_count = matched_count - lead_failure_count - lag_failure_count
        expected_count = max(0, int((check_to - check_from) / audio_sample_length))

        # matched_count is 0 when no audio/video matches were found in the checked
        # range; avoid a division by zero and fall through to "unable to detect"
        pass_rate = 0.0
        if matched_count > 0:
            pass_rate = in_sync_count / matched_count * 100
        coverage = 0.0
        if expected_count > 0:
            coverage = matched_count / expected_count * 100
        self.result["message"] += (
            f"AV Sync was checked from {check_from}ms to {check_to}ms. "
            f"{in_sync_count} of {matched_count} matched samples were in sync "
            f"({round(pass_rate, 2)}%). {matched_count} of {expected_count} expected "
            f"samples were matched ({round(coverage, 2)}%). "
            f"{lead_failure_count} samples had audio leading by more than "
            f"{av_sync_tolerance[0]}ms and {lag_failure_count} had audio lagging by "
            f"more than {-av_sync_tolerance[1]}ms. "
        )

        if filtered_diffs:
            self.result["message"] += (
                f"The AV Sync median offset is {round(statistics.median(filtered_diffs), 2)}ms "
                f"and the offset range is [{round(min(filtered_diffs), 2)}, "
                f"{round(max(filtered_diffs), 2)}] ms."
            )
            if pass_rate >= av_sync_pass_rate:
                self.result["status"] = "PASS"
            else:
                self.result["status"] = "FAIL"
        elif expected_count == 0:
            self.result["status"] = "FAIL"
            self.result["message"] += (
                " The checked range is empty: playback is shorter than the "
                "start and end tolerances."
            )
        else:
            self.result["status"] = "FAIL"
            self.result["message"] += " Unable to detect any audio and video matches."

        # Exporting time diff data to a CSV file and png file
        if self.logger.getEffectiveLevel() == logging.DEBUG:
            file_name = observation_data_export_file + "av_sync_diff.csv"
            write_data_to_csv_file(
                file_name,
                ["audio media time (ms)", "audio lead (ms)"],
                time_differences,
            )

            if time_differences:
                audio_sample, time_diff = zip(*time_differences)
                plt.figure(figsize=(20, 15))
                plt.xlabel("Audio Segment Media Time (ms)")
                plt.ylabel("Audio lead (ms), negative when audio lags")
                plt.title("Detected Audio Video Synchronization")
                file_name = file_name.replace(".csv", ".png")
                plt.plot(audio_sample, time_diff, color="b")
                plt.axhline(y=av_sync_tolerance[0], color="g", linestyle="dashed")
                plt.axhline(y=av_sync_tolerance[1], color="g", linestyle="dashed")
                plt.savefig(file_name)
                plt.close()

        self.logger.debug("[%s] %s", self.result["status"], self.result["message"])
        return self.result, [], []
