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
        self._ytdlp: subprocess.Popen | None = None
        self._ffmpeg: subprocess.Popen | None = None
        self._tmpdir: str | None = None
        self._video_fifo: str | None = None
        self._audio_fifo: str | None = None

    def start(self) -> None:
        self._tmpdir = tempfile.mkdtemp(prefix="liveo_demo_")
        self._video_fifo = os.path.join(self._tmpdir, "video.ts")
        self._audio_fifo = os.path.join(self._tmpdir, "audio.wav")
        os.mkfifo(self._video_fifo)
        os.mkfifo(self._audio_fifo)

        self._ytdlp = subprocess.Popen(
            [
                "yt-dlp", self.video_url,
                "--live-from-start",
                "-f", "bestvideo[height<=1080]+bestaudio",
                "--downloader", "ffmpeg",
                "--hls-use-mpegts",
                "--fragment-retries", "50",
                "--retries", "10",
                "-o", "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

        self._ffmpeg = subprocess.Popen(
            [
                "ffmpeg", "-i", "pipe:0",
                "-c:v", "copy", "-an", "-f", "mpegts", self._video_fifo,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                "-f", "wav", self._audio_fifo,
            ],
            stdin=self._ytdlp.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        for p in [self._ffmpeg, self._ytdlp]:
            if p:
                p.terminate()
                p.wait()
        self._ffmpeg = None
        self._ytdlp = None
        if self._tmpdir:
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None
            self._video_fifo = None
            self._audio_fifo = None

    def is_alive(self) -> bool:
        return all(
            p is not None and p.poll() is None
            for p in [self._ytdlp, self._ffmpeg]
        )

    @property
    def video_pipe_path(self) -> str | None:
        return self._video_fifo

    @property
    def audio_pipe_path(self) -> str | None:
        return self._audio_fifo
