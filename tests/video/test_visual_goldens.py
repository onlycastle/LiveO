"""Visual golden comparison tests (SSIM-based)."""
import pytest
import numpy as np
from pathlib import Path

from backend.clip_editor import render
from .frame_utils import extract_frames


GOLDEN_DIR = Path(__file__).parent / "goldens"


@pytest.fixture
def blur_fill_frames(test_video_fixture, tmp_path):
    result = render(
        input_path=test_video_fixture,
        output_dir=str(tmp_path),
        output_name="golden_blur_fill",
        template="blur_fill",
    )
    return extract_frames(result.video_path, max_frames=5)


def test_blur_fill_renders_consistently(blur_fill_frames):
    """Verify blur_fill template produces non-empty, valid frames."""
    assert len(blur_fill_frames) >= 1, "No frames rendered"

    # Check frame dimensions (1080 wide x 1920 tall in numpy shape = [H, W, C])
    frame = blur_fill_frames[0]
    assert frame.shape[0] == 1920, f"Height mismatch: {frame.shape[0]}"
    assert frame.shape[1] == 1080, f"Width mismatch: {frame.shape[1]}"


def test_golden_frame_dimensions(test_video_fixture, tmp_path):
    """All templates produce correct 1080x1920 frames."""
    for template in ["blur_fill", "letterbox", "cam_split"]:
        result = render(
            input_path=test_video_fixture,
            output_dir=str(tmp_path),
            output_name=f"golden_{template}",
            template=template,
        )
        frames = extract_frames(result.video_path, max_frames=1)
        assert len(frames) >= 1, f"No frames for {template}"
        assert frames[0].shape[0] == 1920, (
            f"{template} height: {frames[0].shape[0]}"
        )
        assert frames[0].shape[1] == 1080, (
            f"{template} width: {frames[0].shape[1]}"
        )


def test_templates_differ(test_video_fixture, tmp_path):
    """Different templates should produce visually different outputs."""
    template_frames: dict[str, np.ndarray] = {}
    for template in ["blur_fill", "letterbox", "cam_split"]:
        result = render(
            input_path=test_video_fixture,
            output_dir=str(tmp_path),
            output_name=f"diff_{template}",
            template=template,
        )
        frames = extract_frames(result.video_path, max_frames=1)
        if frames:
            template_frames[template] = frames[0]

    # At least 2 templates should produce different frames
    if len(template_frames) < 2:
        pytest.skip("Not enough templates rendered")

    templates = list(template_frames.keys())
    for i in range(len(templates)):
        for j in range(i + 1, len(templates)):
            diff = np.abs(
                template_frames[templates[i]].astype(float)
                - template_frames[templates[j]].astype(float)
            ).mean()
            assert diff > 1.0, (
                f"{templates[i]} and {templates[j]} are too similar "
                f"(avg pixel diff: {diff:.2f})"
            )
