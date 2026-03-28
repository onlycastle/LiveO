import pytest
from pathlib import Path
from backend.clip_editor import render


@pytest.fixture
def blur_fill_video(test_video_fixture, tmp_path):
    return render(
        input_path=test_video_fixture,
        output_dir=str(tmp_path),
        output_name="blur_fill_test",
        template="blur_fill",
    )


@pytest.fixture
def letterbox_video(test_video_fixture, tmp_path):
    return render(
        input_path=test_video_fixture,
        output_dir=str(tmp_path),
        output_name="letterbox_test",
        template="letterbox",
    )


@pytest.fixture
def cam_split_video(test_video_fixture, tmp_path):
    return render(
        input_path=test_video_fixture,
        output_dir=str(tmp_path),
        output_name="cam_split_test",
        template="cam_split",
    )


def test_blur_fill_output(blur_fill_video):
    assert blur_fill_video.width == 1080
    assert blur_fill_video.height == 1920
    assert blur_fill_video.template == "blur_fill"
    assert Path(blur_fill_video.video_path).exists()


def test_letterbox_output(letterbox_video):
    assert letterbox_video.width == 1080
    assert letterbox_video.height == 1920
    assert letterbox_video.template == "letterbox"
    assert Path(letterbox_video.video_path).exists()


def test_cam_split_output(cam_split_video):
    assert cam_split_video.width == 1080
    assert cam_split_video.height == 1920
    assert cam_split_video.template == "cam_split"
    assert Path(cam_split_video.video_path).exists()


def test_invalid_template(test_video_fixture, tmp_path):
    with pytest.raises(ValueError, match="Unknown template"):
        render(
            input_path=test_video_fixture,
            output_dir=str(tmp_path),
            output_name="invalid",
            template="nonexistent",
        )


def test_trim_start_end(test_video_fixture, tmp_path):
    result = render(
        input_path=test_video_fixture,
        output_dir=str(tmp_path),
        output_name="trimmed",
        template="blur_fill",
        trim_start=0.5,
        trim_end=2.0,
    )
    assert result.duration <= 2.0
    assert Path(result.video_path).exists()
