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
Contributor: Eurofins Digital Product Testing UK Limited
"""
import logging
import hashlib
import json
import math
import os
import struct
import subprocess
import wave
import numpy as np
import pyaudio

from wave import Wave_read
from exceptions import ObsFrameTerminate
from global_configurations import GlobalConfigurations

# audio file reader chunk size
CHUNK_SIZE = 1024 * 1000

logger = logging.getLogger(__name__)


def _next_power_of_2(value):
    """
    calculate and return next power of 2
    if given valuse is less then 2 then return 0
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
    Returns
    1) A resulting time value tR (scalar int) in (1/sample_rate) units.  The interpretation of this time value
    is,     The value tD is referenced to t0, the beginning of the subject data, and is the delay from t0 until the first
            sample of the segment appears when matched up with the subject data; the value tD is in (1/sample_rate) units,
            where a positive tD indicates the segment appears later than t0, and negative tD implies the segment
            is cut off by trying to start before t0.
    This method finds the media time where the observationsegment appears in the target segmentdata.

    (Timing information: the next block (to RESULTDATA) takes about 0.03s on length_result 262144.)
    Cross-correlate the two data sets to find where the segmentdata appears in the subjectdata.
    """
    length_result = _next_power_of_2(len(subject_data))
    SUBJECTDATA = np.fft.fft(subject_data, n=length_result, norm="ortho")
    SEGMENTDATA = np.fft.fft(segment_data, n=length_result, norm="ortho")
    RESULTDATA = np.multiply(SUBJECTDATA, np.conj(SEGMENTDATA))

    result_complex = np.fft.ifft(RESULTDATA, n=length_result, norm="ortho")
    result_data = np.absolute(result_complex)
    result_tuple = np.where(result_data == np.amax(np.absolute(result_data)))
    result = result_tuple[0][0]

    return result


def extract_audio_to_wav_file(video_file: str, output_ext="wav") -> str:
    """
    Converts video to audio directly using ffmpeg command
    with the help of subprocess module.
    Not concert when file exisit already, running OF multiple times.
    """
    file_name, _ = os.path.splitext(video_file)
    audio_file_name = f"{file_name}.{output_ext}"
    if not os.path.exists(audio_file_name):
        logger.info(
            f"Extracting audio from '{video_file}' and save it to a wav file..."
        )
        result =subprocess.call(
            ["ffmpeg", "-y", "-i", video_file, audio_file_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )

        if result == 0:
            return audio_file_name
        else:
            logger.warning(
                f"Unable to extract audio from '{video_file}'."
                f"If the recording file contains audio testing, "
                f"audio observation will not be made correctly."
            )
            return ""
    else:
        return audio_file_name


def _check_hash(file_name: str) -> bool:
    """Python program to find MD5 hash value of a file
    Adapted from: https://www.quickprogrammingtips.com/python/how-to-calculate-md5-hash-of-a-file-in-python.html
    Accepts: filename
    Returns: hashresult; True == pass, False == failed the check.

    We assume the segmentfile is the correct one for the test but we want to check integrity.  For now,
    that means the calculated hash must match one of the following (we don't care which one, because
    we assume the test software "knows" which file to use; this is checking integrity).
    These are Lch only version from PN build 2, should match hash via http://onlinemd5.com/
    """
    # define hashs for audio mezzanine extracted from json files located in the audio mezzanine folder
    hash_dict ={}
    content_list = os.listdir('audio_mezzanine/')
    count = sum(item.count("wav") for item in content_list)
    for i in range(1,count+1):
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
    framelist = list(struct.unpack(unpack_string, frame_string))
    frames_as_channels = np.array(framelist, dtype=np.short, ndmin=2)
    # extract only left channel
    frames_left_ch = np.reshape(frames_as_channels, (channels, chunk_size), "F")[0]
    return frames_left_ch

def _open_data_file(file_name: str, verify_hash: bool):
    """Accepts
    1) filename: An OS file of recorded data, with or without path (must be in exec directory if without path)
    2) verify_hash: A boolean, should we check the file hash to verify integrity (used for the archived PN files)
    If verify_hash is set, checks the MD5 hash of the file first.
    Then opens and reads the file.
    Returns a tuple of:
    1) sample_rate, typically 48000 Hz
    2) data, the array of data (frames) read from the file
    3) channels, the number of channels (stereo == 2)
    4) sampleformat, bit depth, e.g. uint16
    5) MD5 check result, True == pass, False == fail.
    """
    # If this is a PN file, verify integrity before using
    hash_result = False
    if verify_hash == True:
        hash_result = _check_hash(file_name)

    frames_left_ch = []
    wf = wave.open(file_name, "rb")

    # Get information about the recording
    p = pyaudio.PyAudio()
    sample_format = p.get_format_from_width(wf.getsampwidth())
    channels = wf.getnchannels()
    sample_rate = wf.getframerate()

    # Read the data into an array.
    frame_count = wf.getnframes()
    loop_count = int(frame_count / CHUNK_SIZE)
    last_chunk_size = frame_count % CHUNK_SIZE
    for i in range(loop_count):
        left_ch_data = _read_chunk(wf, channels, CHUNK_SIZE)
        frames_left_ch.extend(left_ch_data)
    left_ch_data = _read_chunk(wf, channels, last_chunk_size)
    frames_left_ch.extend(left_ch_data)

    p.terminate()

    # Return data includes channeldata but only the part that represents the L channel.
    return (sample_rate, frames_left_ch, channels, sample_format, hash_result)


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

    segment_info = _open_data_file(segment_file, verify_hash=True)
    segment_data = segment_info[1]
    hash_result = segment_info[4]

    if hash_result != True:
        raise ObsFrameTerminate(
            f"Error, PN file {segment_file} appears corrupted (failed hash check)"
        )

    return segment_data


def read_audio_recording(subject_file: str) -> list:
    """
    Read recorded audio file.
    Open the PN sequence file (archived pseudo noise sequence in audio format),
    and extract the L channel
    """
    subject_info = _open_data_file(subject_file, verify_hash=False)
    sample_rate = subject_info[0]
    subject_data = subject_info[1]
    sample_format = subject_info[3]

    # only accept 48KHz required for dpctf WAVE
    required_sample_rate = 48000
    # only accept 16b (8 bytes) required for dpctf WAVE
    required_sample_format = 8

    if sample_rate != required_sample_rate:
        raise ObsFrameTerminate(
            f"Error, thesample rate is {sample_rate}, should be {required_sample_rate}"
        )
    if sample_format != required_sample_format:
        raise ObsFrameTerminate(
            f"Error, the file format is {sample_format*2}b; should be {required_sample_format*2}b PCM"
        )

    return subject_data
