"""Continuity tests: freeze frames, black frames."""
import pytest

from backend.clip_editor import render
from .frame_utils import extract_frames
from .metrics import compute_black_frame_ratio, compute_freeze_frames


@pytest.fixture(params=["blur_fill", "letterbox", "cam_split"])
def rendered_video_path(request, test_video_fixture, tmp_path):
    """Render each template and return the video file path."""
    result = render(
        input_path=test_video_fixture,
        output_dir=str(tmp_path),
        output_name=f"continuity_{request.param}",
        template=request.param,
    )
    return result.video_path


def test_no_freeze_frames(rendered_video_path):
    """No pixel-identical freeze longer than 0.5 seconds (15 frames @30fps).

    testsrc updates its counter once per second, producing SSIM ~0.999
    between frames within the same tick.  Templates with large static
    regions (letterbox black bars, cam_split borders) push SSIM up to
    ~0.9997.  We set threshold=0.9999 to only flag truly pixel-identical
    encoding freezes.  For real footage the threshold can be 0.99.
    """
    frames = extract_frames(rendered_video_path)
    if len(frames) < 2:
        pytest.skip("Not enough frames for continuity test")

    # 0.9999 catches genuine encoding freezes (pixel-identical frames)
    # while ignoring testsrc's slow tick pattern across all templates.
    # Observed max SSIM: blur_fill=0.998, letterbox=0.9997, cam_split=0.9996
    max_consecutive, fps = compute_freeze_frames(frames, threshold=0.9999)
    max_freeze_frames = int(fps * 0.5)

    assert max_consecutive <= max_freeze_frames, (
        f"Freeze detected: {max_consecutive} pixel-identical frames "
        f"({max_consecutive / fps:.1f}s), limit is {max_freeze_frames} "
        f"({max_freeze_frames / fps:.1f}s). "
        f"Adjust: clip_editor scene selection or segment boundary."
    )


def test_no_excessive_black_frames(rendered_video_path):
    """Black frame ratio must be <= 3%."""
    frames = extract_frames(rendered_video_path)
    if not frames:
        pytest.skip("No frames extracted")

    ratio = compute_black_frame_ratio(frames)
    assert ratio <= 0.03, (
        f"Black frame ratio {ratio:.1%} exceeds 3%. "
        f"Adjust: pre-buffer start point or source content."
    )
