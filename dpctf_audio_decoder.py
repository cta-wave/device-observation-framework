# -*- coding: utf-8 -*-
"""WAVE DPCTF Audio decoder

Translates the detected Audio Segemnts into AudioSegment object

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
import math
from typing import Tuple

from audio_file_reader import get_time_from_segment
from global_configurations import GlobalConfigurations
from exceptions import AudioAlignError

import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)
logging.getLogger('matplotlib.font_manager').disabled = True


class AudioSegment:
    audio_content_id: str
    """The content id from audio mezzanine"""
    media_time: float
    """The media time of audio segment"""
    audio_segment_timing: float
    """timings in where audio segment found"""

    def __init__(
        self,
        audio_content_id: str,
        media_time: float,
        audio_segment_timing: float,
    ):
        self.audio_content_id = audio_content_id
        self.media_time = media_time
        self.audio_segment_timing = audio_segment_timing


def get_trim_from(
        subject_data: list, segment_data: list, observation_period: int,
        global_configurations: GlobalConfigurations
    ) -> int:
    """
    Accepts
    1) subjectdata: a first audio file that was presumably recorded with some dead time before the audio of interest,
    2) segmentdata:  a segment of PN audio that should mark the end of the audio of interest,
    Returns: trim audio from position
    To trim off the leading audio based on first occurance of matching segmentdata.
    Align the archived copy of PN data (segmentdata) with the PN data in the recorded audio (subjectdata)
    """
    alignment_count = 0
    check_count = global_configurations.get_audio_alignment_check_count()
    for count in range (0, check_count):
        alignment_count = 0
        # Checking if last 3 segments are aligned within the tolerance of segment duration.
        segments_to_check = count + 2
        for i in range(count, segments_to_check):
            segment_data_1_start = observation_period*(i)
            segment_data_1_end = observation_period*(i + 1)
            segment_data_1 = segment_data[segment_data_1_start:segment_data_1_end]

            segment_data_2_start = observation_period*(i + 1)
            segment_data_2_end = observation_period*(i + 2)
            segment_data_2 = segment_data[segment_data_2_start:segment_data_2_end]

            offset1 = get_time_from_segment(subject_data, segment_data_1)
            offset2 = get_time_from_segment(subject_data, segment_data_2)

            if i == count:
                offset = offset1 + observation_period * count
            diff = offset2 - offset1
            if diff < 0 or diff > observation_period * 2:
                break
            else:
                alignment_count += 1

        # break when alignment found where 3 adjacent segments are aligned
        if alignment_count > 1:
            break

    # raise exception unable to align recording with PN file
    if alignment_count < 2:
        raise AudioAlignError(
            f"Unable to align the archived copy of PN data (segmentdata) "
            f"with the PN data in the recorded audio (subjectdata)"
        )

    trim_from = offset
    if trim_from < 0:
        trim_from = 0

    return trim_from


def get_trim_to(
        subject_data: list, segment_data: list, observation_period: int,
        global_configurations: GlobalConfigurations
    ) -> int:
    """
    Accepts
    1) subjectdata: a first audio file that was presumably recorded with some dead time before the audio of interest,
    2) segmentdata:  a segment of PN audio that should mark the end of the audio of interest,
    Returns: trim audio to position
    To trim off the trailing audio based on last occurance of matching segmentdata.
    Align the archived copy of PN data (segmentdata) with the PN data in the recorded audio (subjectdata)
    """
    segment_len = len(segment_data)

    alignment_count = 0
    check_count = global_configurations.get_audio_alignment_check_count() + 1
    for count in range (1, check_count):
        alignment_count = 0
        # Checking if last 3 segments are aligned within the tolerance of segment duration.
        segments_to_check = count + 2
        for i in range(count, segments_to_check):
            segment_data_1_start = segment_len-(observation_period*i)
            segment_data_1_end = segment_len-(observation_period*(i-1))
            segment_data_1 = segment_data[segment_data_1_start:segment_data_1_end]

            segment_data_2_start = segment_len-(observation_period*(i+1))
            segment_data_2_end = segment_len-(observation_period*i)
            segment_data_2 = segment_data[segment_data_2_start:segment_data_2_end]

            offset1 = get_time_from_segment(subject_data, segment_data_1)
            offset2 = get_time_from_segment(subject_data, segment_data_2)

            if i == count:
                offset = offset1 + observation_period * count
            diff = offset1 - offset2
            if diff < 0 or diff > observation_period * 2:
                break
            else:
                alignment_count += 1

        # break when alignment found where 3 adjacent segments are aligned
        if alignment_count > 1:
            break

    # raise exception unable to align recording with PN file
    if alignment_count < 2:
        raise AudioAlignError(
            f"Unable to align the archived copy of PN data (segmentdata) "
            f"with the PN data in the recorded audio (subjectdata)"
        )

    # no margin added to trim_to as last segement is corrected detected
    trim_to = offset
    if trim_to > len(subject_data):
        trim_to = len(subject_data)

    return trim_to


def trim_audio(
        index: int, subject_data: list, segment_data: list,
        observation_period: int, global_configurations: GlobalConfigurations,
        observation_data_export_file:str
    ) -> Tuple[list, int]:
    """
    Accepts
    1) subjectdata: a first audio file that was presumably recorded with some dead time before the audio of interest,
    2) segmentdata:  a segment of PN audio that should mark the end of the audio of interest,
    Returns: a shorter copy of subjectdata with leading and trailing audio trimmed and offset of mezzanine from recording
    prior to first occurance of segmentdata.
    """
    trim_from = get_trim_from(subject_data, segment_data, observation_period, global_configurations)
    trim_to = get_trim_to(subject_data, segment_data, observation_period, global_configurations)
    trimmed_data = subject_data[trim_from:trim_to].copy()

    if (
        logger.getEffectiveLevel() == logging.DEBUG
        and observation_data_export_file
    ):
        plt.figure(index)
        plt.figure(figsize=(30,6))
        plt.xlabel("Time")
        plt.ylabel("Audio Wave")
        subject_data_file = (
            observation_data_export_file +
            "_subject_data_" + str(index) + ".png"
        )
        plt.title("subject_data")
        plt.plot(subject_data)
        plt.axvline(x = trim_from, color = 'b')
        plt.axvline(x = trim_to, color = 'g')
        plt.savefig(subject_data_file)

    return trimmed_data, trim_from


def decode_audio_segments(
    start_media_time: float,
    audio_segment_data_list: list,
    audio_subject_data: list,
    sample_rate: int,
    audio_sample_length: int,
    global_configurations: GlobalConfigurations,
    observation_data_export_file: str
) -> list:
    """Decode audio segemetn and return starting offset and audio segment data"""
    audio_segments = []
    observation_period = sample_rate * audio_sample_length
    neighborhood = (
        sample_rate * global_configurations.get_audio_observation_neighborhood()
    )

    first_offset = None
    index = 0
    for audio_segment_data in audio_segment_data_list:
        # Trim off any leading (useless) audio prior to the watermarked portion
        trimed_data, offset = trim_audio(
            index, audio_subject_data, audio_segment_data,
            observation_period, global_configurations, observation_data_export_file
        )
        if not first_offset:
            first_offset = offset

        trimed_data_len = len(trimed_data)
        duration = math.floor((len(audio_segment_data)) / sample_rate)
        max_segments = math.floor(duration * sample_rate / observation_period)
        # To speed things up, only check in the expected neighborhood of the segment (e.g., +/- 500mS).
        for i in range(0, max_segments):
            if trimed_data_len < neighborhood:
                # when too little data in recording raise exception
                raise AudioAlignError(
                    f"Too little valid data in recording the recorded audio (subjectdata)"
                )
            else:
                neighbor_start = (i * observation_period) - (neighborhood // 2)
                neighbor_end = (i * observation_period) + (neighborhood // 2)
                if neighbor_start < 0:
                    neighbor_start = 0
                    neighbor_end = neighborhood
                if neighbor_end > trimed_data_len:
                    neighbor_start = trimed_data_len - neighborhood
                    neighbor_end = trimed_data_len

                subjectdata = trimed_data[neighbor_start:neighbor_end]
                thissegment = audio_segment_data[
                    (i * observation_period) : ((i + 1) * observation_period)
                ]
                segment_time = get_time_from_segment(subjectdata, thissegment) + neighbor_start
                segment_time_in_ms = (segment_time + offset) / sample_rate
            media_time = start_media_time + i * audio_sample_length

            # content ID for now is not used
            audio_content_id = ""
            audio_segment = AudioSegment(
                audio_content_id,
                media_time,
                segment_time_in_ms,
            )
            audio_segments.append(audio_segment)
        index += 1
        start_media_time = start_media_time + max_segments * audio_sample_length

    return first_offset, audio_segments
