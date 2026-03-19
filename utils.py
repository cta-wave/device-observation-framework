"""
Utility functions.
"""


def frame_num_to_seconds(frame_num: int, frame_rate: float) -> float:
    """Convert frame number to seconds

    Args:
        frame_num (int): frame number
        frame_rate (float): frame rate

    Returns:
        float: time in seconds
    """
    return frame_num / frame_rate


def seconds_to_frame_num(seconds: float, frame_rate: float) -> int:
    """Convert seconds to frame number

    Args:
        seconds (float): time in seconds
        frame_rate (float): frame rate

    Returns:
        int: frame number
    """
    return round(seconds * frame_rate)
