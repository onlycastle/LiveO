from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod

from .debug import record_debug_log


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
        record_debug_log(
            "backend.capture",
            "rtmp_capture_start",
            "Starting RTMP capture process",
            details={"rtmpUrl": self.rtmp_url},
        )
        try:
            self._process = subprocess.Popen(
                [
                    "ffmpeg", "-i", self.rtmp_url,
                    "-c:v", "copy", "-c:a", "aac", "-f", "mpegts", "pipe:1",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            record_debug_log(
                "backend.capture",
                "rtmp_capture_start_failed",
                "Failed to start RTMP capture process",
                level="error",
                details={"rtmpUrl": self.rtmp_url, "error": str(exc)},
            )
            raise

        record_debug_log(
            "backend.capture",
            "rtmp_capture_started",
            "RTMP capture process started",
            details={"rtmpUrl": self.rtmp_url, "pid": self._process.pid},
        )

    def stop(self) -> None:
        if self._process:
            pid = self._process.pid
            record_debug_log(
                "backend.capture",
                "rtmp_capture_stop",
                "Stopping RTMP capture process",
                details={"pid": pid, "rtmpUrl": self.rtmp_url},
            )
            self._process.terminate()
            self._process.wait()
            self._process = None
            record_debug_log(
                "backend.capture",
                "rtmp_capture_stopped",
                "RTMP capture process stopped",
                details={"pid": pid},
            )

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
        record_debug_log(
            "backend.capture",
            "demo_stream_resolve_start",
            "Resolving demo stream URL with yt-dlp",
            details={"videoUrl": self.video_url},
        )
        result = subprocess.run(
            [
                "yt-dlp", self.video_url,
                "-f", "best[height>=1080]/best[height>=720]/best",
                "--get-url",
            ],
            capture_output=True, text=True, timeout=30,
        )
        lines = result.stdout.strip().splitlines()
        if not lines:
            error = f"yt-dlp returned no URL (stream may be offline): {result.stderr.strip()}"
            record_debug_log(
                "backend.capture",
                "demo_stream_resolve_failed",
                "yt-dlp returned no stream URL",
                level="error",
                details={"videoUrl": self.video_url, "error": error},
            )
            raise RuntimeError(error)
        url = lines[0]
        if not url:
            error = f"yt-dlp failed to resolve URL: {result.stderr}"
            record_debug_log(
                "backend.capture",
                "demo_stream_resolve_failed",
                "yt-dlp failed to resolve demo stream URL",
                level="error",
                details={"videoUrl": self.video_url, "error": error},
            )
            raise RuntimeError(error)
        record_debug_log(
            "backend.capture",
            "demo_stream_resolved",
            "Resolved demo stream URL",
            details={"videoUrl": self.video_url},
        )
        return url

    def start(self) -> None:
        stream_url = self._resolve_stream_url()
        record_debug_log(
            "backend.capture",
            "demo_capture_start",
            "Starting demo capture process",
            details={"videoUrl": self.video_url},
        )
        try:
            self._ffmpeg = subprocess.Popen(
                [
                    "ffmpeg", "-i", stream_url,
                    "-c:v", "copy", "-c:a", "aac", "-f", "mpegts", "pipe:1",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:
            record_debug_log(
                "backend.capture",
                "demo_capture_start_failed",
                "Failed to start demo capture process",
                level="error",
                details={"videoUrl": self.video_url, "error": str(exc)},
            )
            raise

        record_debug_log(
            "backend.capture",
            "demo_capture_started",
            "Demo capture process started",
            details={"videoUrl": self.video_url, "pid": self._ffmpeg.pid},
        )

    def stop(self) -> None:
        if self._ffmpeg:
            pid = self._ffmpeg.pid
            record_debug_log(
                "backend.capture",
                "demo_capture_stop",
                "Stopping demo capture process",
                details={"pid": pid, "videoUrl": self.video_url},
            )
            self._ffmpeg.terminate()
            self._ffmpeg.wait()
            self._ffmpeg = None
            record_debug_log(
                "backend.capture",
                "demo_capture_stopped",
                "Demo capture process stopped",
                details={"pid": pid},
            )

    def is_alive(self) -> bool:
        return self._ffmpeg is not None and self._ffmpeg.poll() is None

    @property
    def video_stdout(self) -> subprocess.Popen | None:
        return self._ffmpeg


class FakeCapture(BaseCapture):
    """LIVEO_TEST_MODE=1 전용. 실제 프로세스 없이 캡처 상태만 관리."""

    def __init__(self, url: str = ""):
        self._alive = False
        self.url = url

    def start(self):
        self._alive = True
        record_debug_log(
            "backend.capture",
            "fake_capture_started",
            "Started fake capture for test mode",
            details={"url": self.url},
        )

    def stop(self):
        self._alive = False
        record_debug_log(
            "backend.capture",
            "fake_capture_stopped",
            "Stopped fake capture for test mode",
            details={"url": self.url},
        )

    def is_alive(self) -> bool:
        return self._alive

    @property
    def video_stdout(self):
        return None
