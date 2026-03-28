import subprocess
import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def ffmpeg_available():
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode != 0:
        pytest.skip("ffmpeg not available")


@pytest.fixture(scope="session")
def test_video_fixture(tmp_path_factory, ffmpeg_available):
    """3-second deterministic test video via ffmpeg testsrc."""
    out = tmp_path_factory.mktemp("fixtures") / "test_input.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=3:size=1920x1080:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx264", "-c:a", "aac",
        str(out)
    ], check=True, capture_output=True)
    return str(out)


GOLDEN_DIR = Path(__file__).parent / "goldens"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
