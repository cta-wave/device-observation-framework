# -*- coding: utf-8 -*-
"""WAVE DPCTF audio file reader

Extract audio from mp4 file and read audio wave data from it.

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
import hashlib
import json
import logging
import math
import os
import struct
import subprocess
import wave
from wave import Wave_read

import numpy as np
import pyaudio
import sounddevice

from exceptions import ObsFrameTerminate
from global_configurations import GlobalConfigurations

# audio file reader chunk size
CHUNK_SIZE = 1024 * 1000
# only accept 48KHz required for dpctf WAVE
REQUIRED_SAMPLE_RATE = 48
# only accept 16b (8 bytes) required for dpctf WAVE
REQUIRED_SAMPLE_FORMAT = 8

logger = logging.getLogger(__name__)


def _next_power_of_2(value):
    """
    calculate and return next power of 2
    if given value is less then 2 then return 0
    """
    if value < 2:
        return 0
    next2 = 2 ** (math.ceil(math.log2(value - 1)))
    return next2


def get_time_from_segment(subject_data: list, segment_data: list):
    """Accepts
    1) subjectdata: audio data in which we will search for a PN-based timestamp,
    2) observationsegment: a slice of audio embedding a PN timestamp
    (i.e., should be from an audio file with encoded PN sequencing).
    Length of observationsegment is the observation period OP.

    Returns:
    1) A resulting time value tR (scalar int) in (1/sample_rate) units.
    The interpretation of this time value is:
    The value tD is referenced to t0, the beginning of the subject data, and is the delay from t0
    until the first sample of the segment appears when matched up with the subject data; the value
    tD is in (1/sample_rate) units, where a positive tD indicates the segment appears later than t0,
    and negative tD implies the segment is cut off by trying to start before t0.
    This method finds the media time where the observationsegment appears in the target segmentdata.

    (Timing information: the next block (to result_data) takes about 0.03s on length_result 262144.)
    Cross-correlate the two data sets to find where the segmentdata appears in the subjectdata.
    """
    length_result = _next_power_of_2(len(subject_data))
    np_subject_data = np.fft.fft(subject_data, n=length_result, norm="ortho")
    np_segment_data = np.fft.fft(segment_data, n=length_result, norm="ortho")
    result_data = np.multiply(np_subject_data, np.conj(np_segment_data))

    result_complex = np.fft.ifft(result_data, n=length_result, norm="ortho")
    result_data = np.absolute(result_complex)
    result_tuple = np.where(result_data == np.amax(np.absolute(result_data)))
    if result_tuple[0].size > 0:
        result = result_tuple[0][0]
    else:
        result = 0

    return result


def extract_audio_to_wav_file(video_file: str, output_ext="wav") -> str:
    """
    Converts video to audio directly using ffmpeg command
    with the help of subprocess module.
    Not concert when file exist already, running OF multiple times.
    """
    file_name, _ = os.path.splitext(video_file)
    audio_file_name = f"{file_name}.{output_ext}"
    if not os.path.exists(audio_file_name):
        logger.info(
            "Extracting audio from '%s' and save it to a wav file...", video_file
        )
        result = subprocess.call(
            ["ffmpeg", "-y", "-i", video_file, audio_file_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        if result == 0:
            _check_audio_recording(audio_file_name)
            return audio_file_name
        else:
            logger.warning(
                "Unable to extract audio from '%s'. If the recording file contains audio testing, "
                "audio observation will not be made correctly.",
                video_file,
            )
            return ""
    else:
        _check_audio_recording(audio_file_name)
        return audio_file_name


def _check_hash(file_name: str) -> bool:
    """Python program to find MD5 hash value of a file
    Adapted from:
      https://www.quickprogrammingtips.com/python/how-to-calculate-md5-hash-of-a-file-in-python.html
    Accepts: filename
    Returns: hash_result; True == pass, False == failed the check.

    We assume the segment file is the correct one for the test but we want to check integrity.
    For now, that means the calculated hash must match one of the following (we don't care which
    one, because we assume the test software "knows" which file to use; this is checking integrity).
    These are Lch only version from PN build 2, should match hash via http://onlinemd5.com/
    """
    # define hashes for audio mezzanine extracted from json files
    # located in the audio mezzanine folder
    hash_dict = {}
    content_list = os.listdir("audio_mezzanine/")
    count = sum(item.count("wav") for item in content_list)
    for i in range(1, count + 1):
        temp = open(f"audio_mezzanine/PN0{i}.json", encoding="utf-8")
        temp_data = json.load(temp)
        name = temp_data["Mezzanine"]["name"]
        hash_dict[name] = temp_data["Mezzanine"]["md5"].upper()
        temp.close()
    temp_name1 = file_name.split("/")[2]
    file_name_pn = temp_name1.split(".")[0]

    # Read and update hash in chunks of 4K
    md5_hash = hashlib.md5()
    with open(file_name, "rb") as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            md5_hash.update(byte_block)
    hash_result = md5_hash.hexdigest()
    hash_result = hash_result.upper()  # Force the hash to be an uppercase hex string
    file.close()

    result = False
    if hash_result == hash_dict[file_name_pn]:
        result = True
    return result


def _read_chunk(wf: Wave_read, channels: int, chunk_size: int) -> list:
    """
    read audio wave data in a small chunk
    """
    frame_string = wf.readframes(chunk_size)
    unpack_string = "{0}h{0}h".format(chunk_size)
    frame_list = list(struct.unpack(unpack_string, frame_string))
    frames_as_channels = np.array(frame_list, dtype=np.short, ndmin=2)
    # extract only left channel
    frames_left_ch = np.reshape(frames_as_channels, (channels, chunk_size), "F")[0]
    return frames_left_ch


def _read_data_file(file_name: str, start: int, count: int) -> tuple:
    """Accepts
        filename: An OS file of recorded data, with or without path
          (must be in exec directory if without path)
        start: start sample to read from
        count: sample count to read to
    Returns a tuple of:
        sample_rate, typically 48000 Hz
        data, the array of data (frames) read from the file
        channels, the number of channels (stereo == 2)
        sample_format, bit depth, e.g. uint16
    """
    frames_left_ch = []
    wf = wave.open(file_name, "rb")

    # Get information about the recording
    p = pyaudio.PyAudio()
    sample_format = p.get_format_from_width(wf.getsampwidth())
    channels = wf.getnchannels()
    sample_rate = wf.getframerate()

    # set start position and sample count to read
    if start > 0:
        wf.setpos(start)
    if count:
        sample_count = count
    else:
        sample_count = wf.getnframes() - start

    # Read the data into an array.
    loop_count = int(sample_count / CHUNK_SIZE)
    last_chunk_size = sample_count % CHUNK_SIZE
    for _i in range(loop_count):
        left_ch_data = _read_chunk(wf, channels, CHUNK_SIZE)
        frames_left_ch.extend(left_ch_data)
    left_ch_data = _read_chunk(wf, channels, last_chunk_size)
    frames_left_ch.extend(left_ch_data)

    p.terminate()

    # Return data includes channel data but only the part that represents the L channel.
    return (sample_rate, frames_left_ch, channels, sample_format)


def read_audio_mezzanine(
    global_configurations: GlobalConfigurations, audio_content_id: str
) -> list:
    """
    Read audio mezzanine file
    Open the PN sequence file (archived pseudo noise sequence in audio format),
    check hash, and extract the L channel
    """
    audio_mezzanine_file_path = (
        "./" + global_configurations.get_audio_mezzanine_file_path() + "/"
    )
    segment_file = audio_mezzanine_file_path + audio_content_id + ".wav"

    # If this is a PN file, verify integrity before using
    hash_result = _check_hash(segment_file)
    if hash_result is not True:
        raise ObsFrameTerminate(
            f"Error, PN file {segment_file} appears corrupted (failed hash check)"
        )
    segment_info = _read_data_file(segment_file, start=0, count=None)
    segment_data = segment_info[1]

    return segment_data


def _check_audio_recording(subject_file: str):
    """
    Check recorded audio file.
    Get information about the recording
    and check if it matches with wave requirement.
    """
    wf = wave.open(subject_file, "rb")
    p = pyaudio.PyAudio()
    sample_format = p.get_format_from_width(wf.getsampwidth())
    sample_rate = wf.getframerate()
    p.terminate()
    if sample_rate != REQUIRED_SAMPLE_RATE * 1000:
        logger.warning(
            "The sample rate is %d, should be %dkHz. If the recording file contains audio testing, "
            "audio observation will not be made correctly.",
            sample_rate,
            REQUIRED_SAMPLE_RATE,
        )
    if sample_format != REQUIRED_SAMPLE_FORMAT:
        logger.warning(
            "The file format is %db; should be %db PCM. If the recording file contains audio "
            "testing, audio observation will not be made correctly.",
            sample_format * 2,
            REQUIRED_SAMPLE_FORMAT * 2,
        )


def read_audio_recording(
    subject_file: str, test_start_time: float, test_finish_time: float
) -> list:
    """
    Read recorded audio file.
    Open the PN sequence file (archived pseudo noise sequence in audio format),
    and extract the L channel
    When test_finish_time is not defined read till the end of audio file.
    """
    if test_start_time < 0:
        raise ObsFrameTerminate(
            f"Error, the test_start_time={test_start_time} should not be negative."
        )
    audio_test_start_sample = math.ceil(test_start_time * REQUIRED_SAMPLE_RATE)

    if test_finish_time:
        if test_finish_time < 0:
            raise ObsFrameTerminate(
                f"Error, the test_finish_time={test_finish_time} should not be negative."
            )
        audio_test_end_sample = math.ceil(test_finish_time * REQUIRED_SAMPLE_RATE)
        audio_test_sample_count = audio_test_end_sample - audio_test_start_sample
        if audio_test_sample_count < 0:
            raise ObsFrameTerminate(
                f"Error, the test_start_time={test_start_time}, "
                f"should be before the test_finish_time={test_finish_time}."
            )
    else:
        audio_test_sample_count = None

    subject_info = _read_data_file(
        subject_file, audio_test_start_sample, audio_test_sample_count
    )
    sample_rate = subject_info[0]
    subject_data = subject_info[1]
    sample_format = subject_info[3]

    if sample_rate != REQUIRED_SAMPLE_RATE * 1000:
        raise ObsFrameTerminate(
            f"Error, the sample rate is {sample_rate}, should be {REQUIRED_SAMPLE_RATE}kHz."
        )
    if sample_format != REQUIRED_SAMPLE_FORMAT:
        raise ObsFrameTerminate(
            f"Error, the file format is {sample_format*2}b; "
            f"should be {REQUIRED_SAMPLE_FORMAT*2}b PCM."
        )

    return subject_data
