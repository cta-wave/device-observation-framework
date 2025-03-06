"""Camera AV sync calibration helper"""

import argparse
import os
import sys
import subprocess
import wave
import logging
import cv2
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from global_configurations import GlobalConfigurations
from log_handler import LogManager
from exceptions import ObsFrameTerminate

matplotlib.use("Agg")  # Non-interactive backend
plt.set_loglevel("WARNING")  # Disable Matplotlib's debug messages


def detect_flash_first_appearance(
    logger: logging.Logger, file_path: str, config: list, print_processed_frame: bool
):
    """detected 1st flash appear frames from a video capture"""
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        raise ObsFrameTerminate("Cannot open video file.")
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    frame_duration = 1000 / frame_rate
    if frame_rate == 0:
        raise ObsFrameTerminate("Unable to retrieve FPS.")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    logger.debug(
        "Video capture: %dx%d, Recording Rate: %.2f, Number of frames: %d.",
        width,
        height,
        frame_rate,
        int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
    )
    # Convert the ratios to pixel coordinates
    x = int(config["x_ratio"] * width)
    y = int(config["y_ratio"] * height)
    # Define the region around the pixel (ROI)
    x_min = max(0, x - config["window_size"])
    x_max = min(width, x + config["window_size"] + 1)
    y_min = max(0, y - config["window_size"])
    y_max = min(height, y + config["window_size"] + 1)

    flashes = []
    in_flash = False  # Flag to check if we are currently in a flash state
    frames_since_flash = 0
    frame_number = 0

    # Read frames
    while True:
        ret, frame = cap.read()
        frame_number += 1
        if not ret:
            break

        # print out where the processing is currently
        if print_processed_frame:
            if frame_number % 500 == 0:
                print(f"Processed to frame {frame_number}...")

        # Convert to grayscale
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Extract the region of interest (ROI)
        roi = gray_frame[y_min:y_max, x_min:x_max]

        # Get intensity at the specified pixel
        avg_intensity = np.mean(roi)
        if avg_intensity > config["flash_threshold"] and not in_flash:
            flash_time = (frame_number - 1) * frame_duration
            # flash_time /= 2 # slow motion where video is doubles up to audio
            flashes.append((frame_number, flash_time))
            in_flash = True
            frames_since_flash = 0
        elif avg_intensity <= config["flash_threshold"] and in_flash:
            # Flash is fading out, wait until it is completely gone before detecting again
            frames_since_flash += 1
            if frames_since_flash >= config["fade_out_frames"]:
                in_flash = False  # Mark that the flash has completely faded out
    cap.release()

    for i, flash in enumerate(flashes):
        logger.debug(
            "Flash %d: detected at frame = %d, Start = %.2fms",
            i + 1,
            flash[0],
            flash[1],
        )
    return flashes


def extract_audio_to_wav_file(video_file: str, output_ext="wav") -> str:
    """
    Converts video to audio directly using ffmpeg command
    with the help of subprocess module.
    Not concert when file exist already.
    """
    file_name, _ = os.path.splitext(video_file)
    audio_file_name = f"{file_name}.{output_ext}"
    if not os.path.exists(audio_file_name):
        result = subprocess.call(
            ["ffmpeg", "-y", "-i", video_file, audio_file_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        if result == 0:
            return audio_file_name
        else:
            raise ObsFrameTerminate("Unable to extract audio from '{video_file}'.")
    else:
        return audio_file_name


def detect_beeps(
    logger: logging.Logger, video_file: str, log_file_path: str, config: list
) -> list:
    """Detects beeps in an audio file based on amplitude spikes."""
    audio_file = extract_audio_to_wav_file(video_file)
    if not audio_file:
        return []

    beep_intervals = []
    with wave.open(audio_file, "rb") as wav_file:
        n_channels = wav_file.getnchannels()
        frame_rate = wav_file.getframerate()
        n_frames = wav_file.getnframes()
        logger.debug(
            "Audio capture Channels: %d, Recording Rate: %d, Number of frames: %d.",
            n_channels,
            frame_rate,
            n_frames,
        )
        if n_channels != 2:
            raise ObsFrameTerminate(
                "Recording must be captured in duo-channel. Channels: {n_channels}"
            )
        if frame_rate != 48000:
            raise ObsFrameTerminate(
                "Recording must be in 48kHz. Recording Rate: {frame_rate}"
            )

        raw_data = wav_file.readframes(n_frames)
        audio_data = np.frombuffer(raw_data, dtype=np.int16)
        left_channel = audio_data[::2]
        left_channel = left_channel / np.max(np.abs(left_channel))

        # Detect samples above the threshold
        above_threshold = np.abs(left_channel) > config["beep_threshold"]

        # Find transitions (start and end of each beep)
        transitions = np.diff(above_threshold.astype(int))
        start_indices = np.where(transitions == 1)[0]
        end_indices = np.where(transitions == -1)[0]

        # Adjust for cases where the audio starts or ends with a beep
        if len(start_indices) > 0 and (
            len(end_indices) == 0 or start_indices[0] < end_indices[0]
        ):
            end_indices = np.append(end_indices, len(left_channel) - 1)
        if len(end_indices) > 0 and (
            len(start_indices) == 0 or end_indices[0] < start_indices[0]
        ):
            start_indices = np.insert(start_indices, 0, 0)

        # Convert indices to time
        start_times = start_indices / frame_rate
        end_times = end_indices / frame_rate

        # Filter out short silences (combine beeps separated by very short gaps)
        for start, end in zip(start_times, end_times):
            if (
                len(beep_intervals) == 0
                or (start - beep_intervals[-1][1]) > config["min_silence_duration"]
            ):
                beep_intervals.append([start, end])
            else:
                beep_intervals[-1][1] = end

        # Plot the waveform with beep intervals highlighted
        if logger.getEffectiveLevel() == logging.DEBUG:
            fig_name = f"{log_file_path}/{os.path.splitext(os.path.basename(audio_file))[0]}_beeps.png"
            time = np.linspace(0, len(left_channel) / frame_rate, len(left_channel))
            plt.figure(figsize=(10, 4))
            plt.plot(time, left_channel, label="Left Channel Waveform")
            for start, end in beep_intervals:
                plt.axvspan(
                    start,
                    end,
                    color="yellow",
                    alpha=0.3,
                    label="Beep" if start == beep_intervals[0][0] else "",
                )
            plt.title("Beep Detection in Left Channel")
            plt.xlabel("Time (s)")
            plt.ylabel("Amplitude")
            plt.legend()
            plt.savefig(fig_name)
            plt.close()

    for i, (start, end) in enumerate(beep_intervals):
        logger.debug(
            "Beep %d: Start = %.2fms, End = %.2fs, Duration = %.2fs",
            i + 1,
            start * 1000,
            end * 1000,
            end - start,
        )
    return beep_intervals


def _get_offset(
    logger: logging.Logger, beeps: list, flashes: list, config: list
) -> float:
    """loop detected beeps and flashes to get mean offset"""
    offsets = []
    beep, flash = 0.0, 0.0
    for detected_beep in beeps:
        offset = sys.float_info.max
        for detected_flash in flashes:
            current_offset = detected_beep[0] * 1000 - detected_flash[1]
            if abs(current_offset) < abs(offset):
                offset = current_offset
                beep = detected_beep[0] * 1000
                flash = detected_flash[1]
        if abs(offset) < 500:
            offsets.append(offset)
            logger.debug(
                "offset = %.2fms, Beep = %.2fms, Flash = %.2fms", offset, beep, flash
            )

    mean_offset = np.mean(offsets[1:-1])
    logger.info("Calibration result: Average offset is %.2fms.", mean_offset)
    if abs(mean_offset) <= config["allowed_offset"]:
        logger.info("[PASS]: The camera can capture audio and video in sync.")
    elif (
        abs(mean_offset) > config["allowed_offset"]
        and abs(mean_offset) <= config["max_allowed_offset"]
    ):
        logger.warning(
            "The camera cannot capture audio and video in sync, resulting in an offset \n"
            "that exceeds the allowable limit. Please try recalibrating the camera by\n"
            "adjusting the settings or ensuring the battery is fully charged. If the issue\n"
            "persists, it may indicate that the camera is unsuitable for WAVE test requirements\n"
            "and could produce inaccurate results. Use this camera at your discretion."
        )
    else:
        raise ObsFrameTerminate(
            "The camera cannot capture audio and video in sync, resulting in an offset that\n"
            "exceeds the maximum allowable limit. Please try recalibrating the camera by\n"
            "adjusting the settings or ensuring the battery is fully charged. If the issue\n"
            "persists, the camera is unsuitable for WAVE test requirements and could produce\n"
            "inaccurate results. This camera cannot be used."
        )
    return mean_offset


def calibrate_camera(
    recording_file: str,
    global_configurations: GlobalConfigurations,
    print_processed_frame: bool,
) -> float:
    """
    process camera calibration based on input recording file
    """
    logger = global_configurations.get_logger()
    log_file_path = global_configurations.get_log_file_path()
    if os.path.isfile(recording_file):
        if not os.path.isabs(recording_file):
            recording_file = os.path.abspath(recording_file)
    else:
        raise ObsFrameTerminate(
            f"{recording_file} is not a valid file path. Please provide a valid calibration file path."
        )

    config = global_configurations.get_calibration()
    offset = 0
    detected_flashes = detect_flash_first_appearance(
        logger, recording_file, config, print_processed_frame
    )
    detected_beeps = detect_beeps(logger, recording_file, log_file_path, config)
    # tolerate for starting flash or beep is missing
    if abs(len(detected_beeps) - len(detected_flashes)) > 1:
        logger.warning(
            "The detected number of flashes and beeps do not match.\n"
            "Please verify that the correct test media has been recorded and that the entire duration\n"
            "of the test has been captured. Ensure all instructions were followed carefully.\n"
            "If same issue persists, it may indicate that the camera is not suitable for WAVE test\n"
            "requirements and could produce inaccurate results. Use this camera at your discretion."
        )
    if (
        len(detected_flashes) > config["flash_and_beep_count"]
        or len(detected_beeps) > config["flash_and_beep_count"]
    ):
        raise ObsFrameTerminate(
            "The detected number of flashes or beeps are greater than the expected number.\n"
            "Please verify that the correct test media has been recorded and that the entire\n"
            "duration of the test has been captured. Ensure all instructions were followed \n"
            "carefully and re-calibrate the camera. If same issue persists, the camera does not\n"
            "meet WAVE test requirements and it cannot be used."
        )
    else:
        offset = _get_offset(logger, detected_beeps, detected_flashes, config)
    return offset


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="DPCTF Device Observation Framework Camera Calibration Helper."
    )
    parser.add_argument(
        "--log",
        nargs="+",  # Allow 1 or 2 values
        help="Logging levels for log file writing and console output.",
        default=["debug", "info"],  # default to info console log and debug file writing
        choices=["info", "debug"],
    )
    parser.add_argument(
        "--calibration", required=True, help="Camera calibration recording file path."
    )
    args = parser.parse_args()

    global_configurations = GlobalConfigurations()
    log_file_path = global_configurations.get_log_file_path()
    log_file = log_file_path + "/events.log"
    if len(args.log) == 1:
        args.log = [args.log[0], args.log[0]]
    LogManager(log_file, args.log[0], args.log[1])
    logger = global_configurations.get_logger()
    try:
        calibrate_camera(
            args.calibration,
            global_configurations,
            True,  # print out processed frame
        )
    except ObsFrameTerminate as e:
        logger.exception(
            "Serious error is detected!\n%s\nSystem is terminating!", e, exc_info=False
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
