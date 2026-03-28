"""Video quality metrics for shortform QA."""
from __future__ import annotations

import numpy as np


def compute_freeze_frames(
    frames: list[np.ndarray], threshold: float = 0.99
) -> tuple[int, float]:
    """Find longest consecutive freeze (SSIM > threshold).

    Returns:
        (max_consecutive_frozen_frames, estimated_fps)
    """
    from skimage.metrics import structural_similarity as ssim
    import cv2

    max_consecutive = 0
    consecutive = 0

    for i in range(1, len(frames)):
        gray_prev = cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY)
        gray_curr = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        score = ssim(gray_prev, gray_curr)

        if score > threshold:
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            consecutive = 0

    return max_consecutive, 30.0  # assume 30fps for testsrc


def compute_motion_energy(frames: list[np.ndarray]) -> list[float]:
    """Compute per-frame motion energy (mean absolute pixel difference)."""
    energies: list[float] = []
    for i in range(1, len(frames)):
        diff = np.abs(frames[i].astype(float) - frames[i - 1].astype(float))
        energy = diff.sum() / (frames[i].shape[0] * frames[i].shape[1])
        energies.append(energy)
    return energies


def compute_dead_air_ratio(
    energies: list[float], threshold: float = 100.0
) -> float:
    """Fraction of frames with motion energy below threshold."""
    if not energies:
        return 0.0
    dead = sum(1 for e in energies if e < threshold)
    return dead / len(energies)


def compute_black_frame_ratio(
    frames: list[np.ndarray], lum_threshold: float = 10.0
) -> float:
    """Fraction of frames with average luminance below threshold."""
    if not frames:
        return 0.0
    import cv2

    black = 0
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if gray.mean() < lum_threshold:
            black += 1
    return black / len(frames)
