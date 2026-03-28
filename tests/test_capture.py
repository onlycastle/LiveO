import os
from unittest.mock import MagicMock, patch, call

import pytest

from apps.live_server.capture import (
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
        assert cap.video_pipe_path is None
        assert cap.audio_pipe_path is None
        assert cap.is_alive() is False

    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_start_creates_fifos_and_process(self, mock_mkdtemp, mock_mkfifo, mock_popen):
        mock_mkdtemp.return_value = "/tmp/liveo_rtmp_test"
        mock_popen.return_value = _mock_popen()
        cap = RTMPStreamCapture()
        cap.start()
        assert mock_mkfifo.call_count == 2
        assert mock_popen.call_count == 1
        assert cap.video_pipe_path == "/tmp/liveo_rtmp_test/video.ts"
        assert cap.audio_pipe_path == "/tmp/liveo_rtmp_test/audio.wav"

    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_start_ffmpeg_single_process_with_dual_output(self, mock_mkdtemp, mock_mkfifo, mock_popen):
        mock_mkdtemp.return_value = "/tmp/liveo_rtmp_test"
        mock_popen.return_value = _mock_popen()
        cap = RTMPStreamCapture("rtmp://test:1935/live/s")
        cap.start()
        cmd = mock_popen.call_args[0][0]
        assert "ffmpeg" in cmd
        assert "rtmp://test:1935/live/s" in cmd
        assert "-an" in cmd
        assert "-vn" in cmd
        assert "/tmp/liveo_rtmp_test/video.ts" in cmd
        assert "/tmp/liveo_rtmp_test/audio.wav" in cmd

    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_is_alive_when_running(self, mock_mkdtemp, mock_mkfifo, mock_popen):
        mock_mkdtemp.return_value = "/tmp/test"
        mock_popen.return_value = _mock_popen(poll_return=None)
        cap = RTMPStreamCapture()
        cap.start()
        assert cap.is_alive() is True

    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_is_alive_when_dead(self, mock_mkdtemp, mock_mkfifo, mock_popen):
        mock_mkdtemp.return_value = "/tmp/test"
        mock_popen.return_value = _mock_popen(poll_return=1)
        cap = RTMPStreamCapture()
        cap.start()
        assert cap.is_alive() is False

    @patch("apps.live_server.capture.shutil.rmtree")
    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_stop_terminates_and_cleans_up(self, mock_mkdtemp, mock_mkfifo, mock_popen, mock_rmtree):
        mock_mkdtemp.return_value = "/tmp/liveo_rtmp_test"
        mock_proc = _mock_popen()
        mock_popen.return_value = mock_proc
        cap = RTMPStreamCapture()
        cap.start()
        cap.stop()
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once()
        mock_rmtree.assert_called_once_with("/tmp/liveo_rtmp_test", ignore_errors=True)
        assert cap.video_pipe_path is None
        assert cap.audio_pipe_path is None

    def test_stop_when_not_started(self):
        cap = RTMPStreamCapture()
        cap.stop()
        assert cap.video_pipe_path is None


class TestYtdlpDemoCapture:
    def test_stores_url(self):
        cap = YtdlpDemoCapture("https://youtube.com/watch?v=test")
        assert cap.video_url == "https://youtube.com/watch?v=test"

    def test_initial_state(self):
        cap = YtdlpDemoCapture("https://youtube.com/watch?v=test")
        assert cap.video_pipe_path is None
        assert cap.audio_pipe_path is None
        assert cap.is_alive() is False

    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_start_creates_ytdlp_and_ffmpeg(self, mock_mkdtemp, mock_mkfifo, mock_popen):
        mock_mkdtemp.return_value = "/tmp/liveo_demo_test"
        mock_proc = _mock_popen()
        mock_popen.return_value = mock_proc
        cap = YtdlpDemoCapture("https://youtube.com/watch?v=test")
        cap.start()
        assert mock_popen.call_count == 2
        assert mock_mkfifo.call_count == 2

    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_start_ytdlp_args(self, mock_mkdtemp, mock_mkfifo, mock_popen):
        mock_mkdtemp.return_value = "/tmp/test"
        mock_popen.return_value = _mock_popen()
        cap = YtdlpDemoCapture("https://youtube.com/watch?v=abc")
        cap.start()
        ytdlp_cmd = mock_popen.call_args_list[0][0][0]
        assert "yt-dlp" in ytdlp_cmd
        assert "https://youtube.com/watch?v=abc" in ytdlp_cmd
        assert "--live-from-start" in ytdlp_cmd

    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_start_pipes_ytdlp_stdout_to_ffmpeg(self, mock_mkdtemp, mock_mkfifo, mock_popen):
        mock_mkdtemp.return_value = "/tmp/test"
        mock_proc = _mock_popen()
        mock_popen.return_value = mock_proc
        cap = YtdlpDemoCapture("https://youtube.com/watch?v=test")
        cap.start()
        ffmpeg_call = mock_popen.call_args_list[1]
        assert ffmpeg_call[1].get("stdin") == mock_proc.stdout

    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_ffmpeg_outputs_to_named_pipes(self, mock_mkdtemp, mock_mkfifo, mock_popen):
        mock_mkdtemp.return_value = "/tmp/liveo_demo_test"
        mock_popen.return_value = _mock_popen()
        cap = YtdlpDemoCapture("https://youtube.com/watch?v=test")
        cap.start()
        ffmpeg_cmd = mock_popen.call_args_list[1][0][0]
        assert "/tmp/liveo_demo_test/video.ts" in ffmpeg_cmd
        assert "/tmp/liveo_demo_test/audio.wav" in ffmpeg_cmd

    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_is_alive_all_running(self, mock_mkdtemp, mock_mkfifo, mock_popen):
        mock_mkdtemp.return_value = "/tmp/test"
        mock_popen.return_value = _mock_popen(poll_return=None)
        cap = YtdlpDemoCapture("https://youtube.com/watch?v=test")
        cap.start()
        assert cap.is_alive() is True

    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_is_alive_one_dead(self, mock_mkdtemp, mock_mkfifo, mock_popen):
        mock_mkdtemp.return_value = "/tmp/test"
        alive = _mock_popen(poll_return=None)
        dead = _mock_popen(poll_return=1)
        mock_popen.side_effect = [dead, alive]
        cap = YtdlpDemoCapture("https://youtube.com/watch?v=test")
        cap.start()
        assert cap.is_alive() is False

    @patch("apps.live_server.capture.shutil.rmtree")
    @patch("apps.live_server.capture.subprocess.Popen")
    @patch("apps.live_server.capture.os.mkfifo")
    @patch("apps.live_server.capture.tempfile.mkdtemp")
    def test_stop_terminates_both_and_cleans(self, mock_mkdtemp, mock_mkfifo, mock_popen, mock_rmtree):
        mock_mkdtemp.return_value = "/tmp/liveo_demo_test"
        mock_proc = _mock_popen()
        mock_popen.return_value = mock_proc
        cap = YtdlpDemoCapture("https://youtube.com/watch?v=test")
        cap.start()
        cap.stop()
        assert mock_proc.terminate.call_count == 2
        assert mock_proc.wait.call_count == 2
        mock_rmtree.assert_called_once()
        assert cap.video_pipe_path is None
        assert cap.audio_pipe_path is None

    def test_stop_when_not_started(self):
        cap = YtdlpDemoCapture("https://youtube.com/watch?v=test")
        cap.stop()
        assert cap.video_pipe_path is None
