"""
Step 6a: 3D Pose Smoothing

Applies Savitzky-Golay filter and NaN interpolation to 3D poses.
"""

import logging
from typing import Optional

import numpy as np
from scipy.signal import savgol_filter

logger = logging.getLogger(__name__)


def interpolate_missing_joints(poses_3d: np.ndarray) -> np.ndarray:
    """
    Interpolate NaN values in 3D poses using linear interpolation.

    Args:
        poses_3d: (T, 17, 3) array with possible NaN entries.

    Returns:
        (T, 17, 3) array with NaN values interpolated.
    """
    result = poses_3d.copy()
    T, J, D = result.shape
    interpolated_count = 0

    for j in range(J):
        for d in range(D):
            col = result[:, j, d]
            nans = np.isnan(col)

            if nans.all():
                # Entire joint missing — fill with zero
                result[:, j, d] = 0.0
                interpolated_count += T
                continue

            if not nans.any():
                continue

            valid = np.where(~nans)[0]
            col[nans] = np.interp(np.where(nans)[0], valid, col[valid])
            result[:, j, d] = col
            interpolated_count += nans.sum()

    nan_pct = 100.0 * interpolated_count / (T * J * D)
    logger.info(
        f"Interpolated {interpolated_count} NaN values "
        f"({nan_pct:.1f}% of all coordinates)"
    )
    return result


def smooth_savgol(
    poses_3d: np.ndarray,
    window_length: int = 7,
    polyorder: int = 3,
) -> np.ndarray:
    """
    Apply Savitzky-Golay filter per joint per axis.

    Args:
        poses_3d: (T, 17, 3) array (NaN-free after interpolation).
        window_length: Filter window length (must be odd).
        polyorder: Polynomial order.

    Returns:
        (T, 17, 3) smoothed array.
    """
    T, J, D = poses_3d.shape

    if T < window_length:
        logger.warning(
            f"Sequence too short ({T} frames) for window_length={window_length}. "
            f"Reducing window to {T if T % 2 == 1 else T - 1}"
        )
        window_length = T if T % 2 == 1 else max(3, T - 1)

    result = poses_3d.copy()

    for j in range(J):
        for d in range(D):
            result[:, j, d] = savgol_filter(
                poses_3d[:, j, d], window_length, polyorder
            )

    logger.info(
        f"Applied Savitzky-Golay filter (window={window_length}, order={polyorder})"
    )
    return result


def smooth_ema(poses_3d: np.ndarray, alpha: float = 0.75) -> np.ndarray:
    """
    Apply Exponential Moving Average smoothing.

    Args:
        poses_3d: (T, 17, 3) array.
        alpha: Smoothing factor (0 < alpha <= 1). Higher = less smoothing.

    Returns:
        (T, 17, 3) smoothed array.
    """
    result = poses_3d.copy()
    T = result.shape[0]

    for t in range(1, T):
        result[t] = alpha * poses_3d[t] + (1 - alpha) * result[t - 1]

    logger.info(f"Applied EMA smoothing (alpha={alpha})")
    return result


def smooth_poses(
    poses_3d: np.ndarray,
    method: str = "savgol",
    window_length: int = 7,
    polyorder: int = 3,
    ema_alpha: float = 0.75,
) -> np.ndarray:
    """
    Full smoothing pipeline: interpolation → smoothing.

    Args:
        poses_3d: (T, 17, 3) raw 3D poses (may contain NaN).
        method: 'savgol' or 'ema'.
        window_length: Savitzky-Golay window.
        polyorder: Savitzky-Golay polynomial order.
        ema_alpha: EMA smoothing factor.

    Returns:
        (T, 17, 3) smoothed poses.
    """
    logger.info(f"Smoothing 3D poses ({poses_3d.shape}) with method={method}...")

    # Step 1: Interpolate missing joints
    poses_interp = interpolate_missing_joints(poses_3d)

    # Step 2: Apply smoothing
    if method == "savgol":
        poses_smooth = smooth_savgol(poses_interp, window_length, polyorder)
    elif method == "ema":
        poses_smooth = smooth_ema(poses_interp, ema_alpha)
    else:
        logger.warning(f"Unknown smoothing method '{method}', using savgol")
        poses_smooth = smooth_savgol(poses_interp, window_length, polyorder)

    # Validate: check for spikes
    if poses_smooth.shape[0] > 1:
        velocity = np.linalg.norm(np.diff(poses_smooth, axis=0), axis=2)
        max_velocity = np.max(velocity)
        mean_velocity = np.mean(velocity)
        logger.info(
            f"Post-smoothing velocity: mean={mean_velocity:.4f}, max={max_velocity:.4f}"
        )
        if max_velocity > 10 * mean_velocity and mean_velocity > 0:
            logger.warning("Possible residual spike detected after smoothing")

    return poses_smooth
