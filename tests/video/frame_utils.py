"""Frame extraction and analysis utilities for video QA."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np


def extract_frames(video_path: str, max_frames: int = 0) -> list[np.ndarray]:
    """Extract frames from video as numpy arrays.

    Args:
        video_path: Path to the video file.
        max_frames: Maximum number of frames to extract (0 = all).

    Returns:
        List of BGR numpy arrays (OpenCV format).
    """
    import cv2

    cap = cv2.VideoCapture(video_path)
    frames: list[np.ndarray] = []
    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
        count += 1
        if max_frames > 0 and count >= max_frames:
            break
    cap.release()
    return frames


def frame_energy(current: np.ndarray, previous: np.ndarray) -> float:
    """Compute motion energy between two frames (mean absolute difference per pixel)."""
    diff = np.abs(current.astype(float) - previous.astype(float))
    return diff.sum() / (current.shape[0] * current.shape[1])


def ffprobe(video_path: str) -> dict:
    """Get video metadata via ffprobe.

    Returns dict with keys: width, height, video_codec, audio_codec,
    duration_sec, display_aspect_ratio.
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    video_stream = next(
        (s for s in data["streams"] if s["codec_type"] == "video"), {}
    )
    audio_streams = [s for s in data["streams"] if s["codec_type"] == "audio"]

    return {
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "video_codec": video_stream.get("codec_name", ""),
        "audio_codec": audio_streams[0].get("codec_name", "")
        if audio_streams
        else "",
        "duration_sec": float(data.get("format", {}).get("duration", 0)),
        "display_aspect_ratio": video_stream.get("display_aspect_ratio", ""),
    }
