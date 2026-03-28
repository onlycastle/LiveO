from unittest.mock import MagicMock, patch

import pytest

from backend.capture import (
    BaseCapture,
    RTMPStreamCapture,
    YtdlpDemoCapture,
)


def _mock_popen(poll_return=None):
    p = MagicMock()
    p.poll.return_value = poll_return
    p.stdout = MagicMock()
    return p


class TestBaseCapture:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseCapture()

    def test_subclass_must_implement(self):
        class Incomplete(BaseCapture):
            pass

        with pytest.raises(TypeError):
            Incomplete()


class TestRTMPStreamCapture:
    def test_default_url(self):
        cap = RTMPStreamCapture()
        assert cap.rtmp_url == "rtmp://localhost:1935/live/stream"

    def test_custom_url(self):
        cap = RTMPStreamCapture("rtmp://example.com/live/test")
        assert cap.rtmp_url == "rtmp://example.com/live/test"

    def test_initial_state(self):
        cap = RTMPStreamCapture()
        assert cap.video_stdout is None
        assert cap.is_alive() is False

    @patch("backend.capture.subprocess.Popen")
    def test_start_creates_process(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        cap = RTMPStreamCapture()
        cap.start()
        assert mock_popen.call_count == 1
        assert cap.video_stdout is not None

    @patch("backend.capture.subprocess.Popen")
    def test_start_ffmpeg_args(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        cap = RTMPStreamCapture("rtmp://test:1935/live/s")
        cap.start()
        cmd = mock_popen.call_args[0][0]
        assert "ffmpeg" in cmd
        assert "rtmp://test:1935/live/s" in cmd
        assert "-an" in cmd
        assert "pipe:1" in cmd

    @patch("backend.capture.subprocess.Popen")
    def test_is_alive_when_running(self, mock_popen):
        mock_popen.return_value = _mock_popen(poll_return=None)
        cap = RTMPStreamCapture()
        cap.start()
        assert cap.is_alive() is True

    @patch("backend.capture.subprocess.Popen")
    def test_is_alive_when_dead(self, mock_popen):
        mock_popen.return_value = _mock_popen(poll_return=1)
        cap = RTMPStreamCapture()
        cap.start()
        assert cap.is_alive() is False

    @patch("backend.capture.subprocess.Popen")
    def test_stop_terminates(self, mock_popen):
        mock_proc = _mock_popen()
        mock_popen.return_value = mock_proc
        cap = RTMPStreamCapture()
        cap.start()
        cap.stop()
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once()
        assert cap.video_stdout is None

    def test_stop_when_not_started(self):
        cap = RTMPStreamCapture()
        cap.stop()
        assert cap.video_stdout is None


class TestYtdlpDemoCapture:
    def test_stores_url(self):
        cap = YtdlpDemoCapture("https://twitch.tv/test")
        assert cap.video_url == "https://twitch.tv/test"

    def test_initial_state(self):
        cap = YtdlpDemoCapture("https://twitch.tv/test")
        assert cap.video_stdout is None
        assert cap.is_alive() is False

    @patch("backend.capture.subprocess.Popen")
    @patch("backend.capture.subprocess.run")
    def test_start_resolves_url_and_creates_ffmpeg(self, mock_run, mock_popen):
        mock_run.return_value = MagicMock(stdout="https://stream.url/live.m3u8\n", stderr="")
        mock_popen.return_value = _mock_popen()
        cap = YtdlpDemoCapture("https://twitch.tv/test")
        cap.start()
        assert mock_popen.call_count == 1

    @patch("backend.capture.subprocess.Popen")
    @patch("backend.capture.subprocess.run")
    def test_resolve_uses_ytdlp_get_url(self, mock_run, mock_popen):
        mock_run.return_value = MagicMock(stdout="https://stream.url/live.m3u8\n", stderr="")
        mock_popen.return_value = _mock_popen()
        cap = YtdlpDemoCapture("https://twitch.tv/abc")
        cap.start()
        run_cmd = mock_run.call_args[0][0]
        assert "yt-dlp" in run_cmd
        assert "https://twitch.tv/abc" in run_cmd
        assert "--get-url" in run_cmd

    @patch("backend.capture.subprocess.Popen")
    @patch("backend.capture.subprocess.run")
    def test_ffmpeg_uses_resolved_url(self, mock_run, mock_popen):
        mock_run.return_value = MagicMock(stdout="https://stream.url/live.m3u8\n", stderr="")
        mock_popen.return_value = _mock_popen()
        cap = YtdlpDemoCapture("https://twitch.tv/test")
        cap.start()
        ffmpeg_cmd = mock_popen.call_args[0][0]
        assert "https://stream.url/live.m3u8" in ffmpeg_cmd
        assert "pipe:1" in ffmpeg_cmd

    @patch("backend.capture.subprocess.Popen")
    @patch("backend.capture.subprocess.run")
    def test_is_alive_when_running(self, mock_run, mock_popen):
        mock_run.return_value = MagicMock(stdout="https://stream.url/live.m3u8\n", stderr="")
        mock_popen.return_value = _mock_popen(poll_return=None)
        cap = YtdlpDemoCapture("https://twitch.tv/test")
        cap.start()
        assert cap.is_alive() is True

    @patch("backend.capture.subprocess.Popen")
    @patch("backend.capture.subprocess.run")
    def test_is_alive_when_dead(self, mock_run, mock_popen):
        mock_run.return_value = MagicMock(stdout="https://stream.url/live.m3u8\n", stderr="")
        mock_popen.return_value = _mock_popen(poll_return=1)
        cap = YtdlpDemoCapture("https://twitch.tv/test")
        cap.start()
        assert cap.is_alive() is False

    @patch("backend.capture.subprocess.Popen")
    @patch("backend.capture.subprocess.run")
    def test_stop_terminates(self, mock_run, mock_popen):
        mock_run.return_value = MagicMock(stdout="https://stream.url/live.m3u8\n", stderr="")
        mock_proc = _mock_popen()
        mock_popen.return_value = mock_proc
        cap = YtdlpDemoCapture("https://twitch.tv/test")
        cap.start()
        cap.stop()
        mock_proc.terminate.assert_called_once()
        assert cap.video_stdout is None

    def test_stop_when_not_started(self):
        cap = YtdlpDemoCapture("https://twitch.tv/test")
        cap.stop()
        assert cap.video_stdout is None
