from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod


class BaseCapture(ABC):
    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def is_alive(self) -> bool: ...

    @property
    @abstractmethod
    def video_stdout(self) -> subprocess.Popen | None: ...


class RTMPStreamCapture(BaseCapture):
    def __init__(self, rtmp_url: str = "rtmp://localhost:1935/live/stream"):
        self.rtmp_url = rtmp_url
        self._process: subprocess.Popen | None = None

    def start(self) -> None:
        self._process = subprocess.Popen(
            [
                "ffmpeg", "-i", self.rtmp_url,
                "-c:v", "copy", "-an", "-f", "mpegts", "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None

    def is_alive(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def video_stdout(self) -> subprocess.Popen | None:
        return self._process


class YtdlpDemoCapture(BaseCapture):
    def __init__(self, video_url: str):
        self.video_url = video_url
        self._ffmpeg: subprocess.Popen | None = None

    def _resolve_stream_url(self) -> str:
        result = subprocess.run(
            [
                "yt-dlp", self.video_url,
                "-f", "best[height>=1080]/best[height>=720]/best",
                "--get-url",
            ],
            capture_output=True, text=True, timeout=30,
        )
        url = result.stdout.strip().splitlines()[0]
        if not url:
            raise RuntimeError(f"yt-dlp failed to resolve URL: {result.stderr}")
        return url

    def start(self) -> None:
        stream_url = self._resolve_stream_url()

        self._ffmpeg = subprocess.Popen(
            [
                "ffmpeg", "-i", stream_url,
                "-c:v", "copy", "-an", "-f", "mpegts", "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        if self._ffmpeg:
            self._ffmpeg.terminate()
            self._ffmpeg.wait()
            self._ffmpeg = None

    def is_alive(self) -> bool:
        return self._ffmpeg is not None and self._ffmpeg.poll() is None

    @property
    def video_stdout(self) -> subprocess.Popen | None:
        return self._ffmpeg
