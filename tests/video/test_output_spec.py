import json
import subprocess

import pytest
from pathlib import Path

from backend.clip_editor import render


@pytest.fixture(params=["blur_fill", "letterbox", "cam_split"])
def rendered_video(request, test_video_fixture, tmp_path):
    result = render(
        input_path=test_video_fixture,
        output_dir=str(tmp_path),
        output_name=f"test_{request.param}",
        template=request.param,
    )
    return result


def _ffprobe(path: str) -> dict:
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            path,
        ],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_output_resolution(rendered_video):
    probe = _ffprobe(rendered_video.video_path)
    video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    assert int(video_stream["width"]) == 1080
    assert int(video_stream["height"]) == 1920


def test_output_codec(rendered_video):
    probe = _ffprobe(rendered_video.video_path)
    video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
    assert video_stream["codec_name"] == "h264"

    audio_streams = [s for s in probe["streams"] if s["codec_type"] == "audio"]
    if audio_streams:
        assert audio_streams[0]["codec_name"] == "aac"


def test_output_duration(rendered_video):
    assert 1.0 <= rendered_video.duration <= 30.0


def test_output_files_exist(rendered_video):
    assert Path(rendered_video.video_path).exists()
    assert Path(rendered_video.thumbnail_path).exists()


def test_thumbnail_is_image(rendered_video):
    thumb = Path(rendered_video.thumbnail_path)
    assert thumb.stat().st_size > 0
