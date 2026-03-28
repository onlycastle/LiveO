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
    def video_pipe_path(self) -> str | None: ...

    @property
    @abstractmethod
    def audio_pipe_path(self) -> str | None: ...


class RTMPStreamCapture(BaseCapture):
    def __init__(self, rtmp_url: str = "rtmp://localhost:1935/live/stream"):
        self.rtmp_url = rtmp_url
        self._process: subprocess.Popen | None = None
        self._tmpdir: str | None = None
        self._video_fifo: str | None = None
        self._audio_fifo: str | None = None

    def start(self) -> None:
        self._tmpdir = tempfile.mkdtemp(prefix="liveo_rtmp_")
        self._video_fifo = os.path.join(self._tmpdir, "video.ts")
        self._audio_fifo = os.path.join(self._tmpdir, "audio.wav")
        os.mkfifo(self._video_fifo)
        os.mkfifo(self._audio_fifo)

        self._process = subprocess.Popen(
            [
                "ffmpeg", "-i", self.rtmp_url,
                "-c:v", "copy", "-an", "-f", "mpegts", self._video_fifo,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                "-f", "wav", self._audio_fifo,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        if self._process:
            self._process.terminate()
            self._process.wait()
            self._process = None
        if self._tmpdir:
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
            self._video_fifo = None
            self._audio_fifo = None

    def is_alive(self) -> bool:
        return self._process is not None and self._process.poll() is None

    @property
    def video_pipe_path(self) -> str | None:
        return self._video_fifo

    @property
    def audio_pipe_path(self) -> str | None:
        return self._audio_fifo


class YtdlpDemoCapture(BaseCapture):
    def __init__(self, video_url: str):
        self.video_url = video_url
        self._ffmpeg: subprocess.Popen | None = None
        self._tmpdir: str | None = None
        self._video_fifo: str | None = None
        self._audio_fifo: str | None = None

    def _resolve_stream_url(self) -> str:
        result = subprocess.run(
            [
                "yt-dlp", self.video_url,
                "-f", "best[height<=1080]",
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

        self._tmpdir = tempfile.mkdtemp(prefix="liveo_demo_")
        self._video_fifo = os.path.join(self._tmpdir, "video.ts")
        self._audio_fifo = os.path.join(self._tmpdir, "audio.wav")
        os.mkfifo(self._video_fifo)
        os.mkfifo(self._audio_fifo)

        self._ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-i", stream_url,
                "-c:v", "copy", "-an", "-f", "mpegts", self._video_fifo,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                "-f", "wav", self._audio_fifo,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        if self._ffmpeg:
            self._ffmpeg.terminate()
            self._ffmpeg.wait()
            self._ffmpeg = None
        if self._tmpdir:
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
            self._video_fifo = None
            self._audio_fifo = None

    def is_alive(self) -> bool:
        return self._ffmpeg is not None and self._ffmpeg.poll() is None

    @property
    def video_pipe_path(self) -> str | None:
        return self._video_fifo

    @property
    def audio_pipe_path(self) -> str | None:
        return self._audio_fifo
