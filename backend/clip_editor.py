from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RenderResult:
    video_path: str
    thumbnail_path: str
    template: str
    duration: float
    width: int
    height: int


def render(
    input_path: str,
    output_dir: str,
    output_name: str,
    template: str = "blur_fill",
    trim_start: float | None = None,
    trim_end: float | None = None,
    caption: str = "",
) -> RenderResult:
    """Render a clip to 9:16 vertical format.

    Args:
        input_path: Path to source video (16:9)
        output_dir: Directory for output files
        output_name: Base filename (without extension)
        template: One of blur_fill, letterbox, cam_split
        trim_start: Start time in seconds (optional)
        trim_end: End time in seconds (optional)
        caption: Caption text for letterbox template

    Returns:
        RenderResult with paths and metadata
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    video_path = str(out_dir / f"{output_name}.mp4")
    thumb_path = str(out_dir / f"{output_name}.jpg")

    # Build ffmpeg filter based on template
    if template == "blur_fill":
        vf = _blur_fill_filter()
    elif template == "letterbox":
        vf = _letterbox_filter()
    elif template == "cam_split":
        vf = _cam_split_filter()
    else:
        raise ValueError(f"Unknown template: {template}")

    # Build ffmpeg command
    cmd = ["ffmpeg", "-y"]

    # Input with trim
    if trim_start is not None:
        cmd.extend(["-ss", str(trim_start)])
    cmd.extend(["-fflags", "+discardcorrupt", "-err_detect", "ignore_err",
                "-i", input_path])
    if trim_end is not None and trim_start is not None:
        duration = trim_end - trim_start
        cmd.extend(["-t", str(duration)])
    elif trim_end is not None:
        cmd.extend(["-t", str(trim_end)])

    # Video filter + encoding
    cmd.extend([
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        video_path,
    ])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr_tail = (result.stderr or "").strip()[-500:]
        logger.error("Render ffmpeg failed (exit %d): %s", result.returncode, stderr_tail)
        raise RuntimeError(f"Render failed (ffmpeg exit {result.returncode}): {stderr_tail}")

    _validate_video(video_path)

    # Generate thumbnail from first frame (best-effort)
    thumb_cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        thumb_path,
    ]
    thumb_result = subprocess.run(thumb_cmd, capture_output=True, text=True)
    if thumb_result.returncode != 0:
        stderr_tail = (thumb_result.stderr or "").strip()[-500:]
        logger.warning(
            "Thumbnail extraction failed (exit %d), continuing without thumbnail: %s",
            thumb_result.returncode, stderr_tail,
        )
        thumb_path = ""

    # Get duration from output
    dur = _get_duration(video_path)

    return RenderResult(
        video_path=video_path,
        thumbnail_path=thumb_path,
        template=template,
        duration=dur,
        width=1080,
        height=1920,
    )


def _validate_video(video_path: str) -> None:
    """Verify the rendered MP4 contains decodable video frames."""
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-count_packets",
            "-show_entries", "stream=nb_read_packets",
            "-of", "csv=p=0",
            video_path,
        ],
        capture_output=True, text=True,
    )
    try:
        packets = int(probe.stdout.strip())
    except (ValueError, AttributeError):
        packets = 0
    if packets == 0:
        raise RuntimeError(
            "Rendered video has no decodable video frames — source segments may be corrupt"
        )


def _blur_fill_filter() -> str:
    """Blur fill: blurred scaled background + centered original.

    Creates a 1080x1920 output with:
    - Background: input scaled to fill 1080x1920, heavily blurred
    - Foreground: input scaled to fit width (1080px), centered vertically
    """
    return (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=30[blurred];"
        "[fg]scale=1080:-2:force_original_aspect_ratio=decrease[scaled];"
        "[blurred][scaled]overlay=(W-w)/2:(H-h)/2"
    )


def _letterbox_filter() -> str:
    """Letterbox: black bars top/bottom with content centered.

    Creates a 1080x1920 output with:
    - Black 1080x1920 canvas
    - Content scaled to fit width, centered
    """
    return (
        "[0:v]scale=1080:-2:force_original_aspect_ratio=decrease[scaled];"
        "[scaled]pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
    )


def _cam_split_filter() -> str:
    """Cam split: game footage top + game footage bottom (simulated cam).

    Creates a 1080x1920 output with:
    - Top half: game footage cropped/scaled to 1080x960
    - Bottom half: game footage zoomed in (simulating camera) to 1080x960
    """
    return (
        "[0:v]split=2[top][bot];"
        "[top]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[top_cropped];"
        "[bot]scale=2160:1920:force_original_aspect_ratio=increase,crop=1080:960[bot_zoomed];"
        "[top_cropped][bot_zoomed]vstack"
    )


def _get_duration(video_path: str) -> float:
    """Get video duration using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-print_format", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0
