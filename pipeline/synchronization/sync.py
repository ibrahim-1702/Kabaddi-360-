"""
Step 4: Temporal Synchronization

Aligns 3 views temporally using cross-correlation of weighted
velocity signals from pelvis, wrist, and ankle trajectories.
"""

import json
import logging
import os
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# COCO-17 joint indices
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_ANKLE = 15
RIGHT_ANKLE = 16


def compute_velocity(trajectory: np.ndarray) -> np.ndarray:
    """
    Compute velocity magnitude from a 2D trajectory using finite differences.

    Args:
        trajectory: (T, 2) array of x,y positions.

    Returns:
        (T,) array of velocity magnitudes. First element is 0.
    """
    # Handle NaN by interpolation first
    for dim in range(2):
        col = trajectory[:, dim].copy()
        nans = np.isnan(col)
        if nans.all():
            col[:] = 0.0
        elif nans.any():
            valid = np.where(~nans)[0]
            col[nans] = np.interp(np.where(nans)[0], valid, col[valid])
        trajectory[:, dim] = col

    diff = np.diff(trajectory, axis=0)
    speed = np.sqrt(np.sum(diff ** 2, axis=1))
    return np.concatenate([[0.0], speed])


def compute_sync_signal(
    poses: np.ndarray,
    pelvis_weight: float = 0.5,
    wrist_weight: float = 0.3,
    ankle_weight: float = 0.2,
) -> np.ndarray:
    """
    Compute weighted velocity signal for synchronization.

    Args:
        poses: (T, 17, 2) pose array.
        pelvis_weight: Weight for pelvis velocity.
        wrist_weight: Weight for wrist velocity.
        ankle_weight: Weight for ankle velocity.

    Returns:
        (T,) weighted velocity signal.
    """
    # Pelvis = midpoint of hips
    pelvis = (poses[:, LEFT_HIP, :] + poses[:, RIGHT_HIP, :]) / 2.0
    pelvis_vel = compute_velocity(pelvis.copy())

    # Wrist = average of left and right
    wrist = (poses[:, LEFT_WRIST, :] + poses[:, RIGHT_WRIST, :]) / 2.0
    wrist_vel = compute_velocity(wrist.copy())

    # Ankle = average of left and right
    ankle = (poses[:, LEFT_ANKLE, :] + poses[:, RIGHT_ANKLE, :]) / 2.0
    ankle_vel = compute_velocity(ankle.copy())

    signal = (
        pelvis_weight * pelvis_vel
        + wrist_weight * wrist_vel
        + ankle_weight * ankle_vel
    )

    # Normalize signal
    std = np.std(signal)
    if std > 1e-8:
        signal = (signal - np.mean(signal)) / std

    return signal


def cross_correlate_offset(
    signal_ref: np.ndarray,
    signal_target: np.ndarray,
    max_offset: int = 30,
) -> Tuple[int, float]:
    """
    Find temporal offset between two signals using normalized cross-correlation.

    Args:
        signal_ref: Reference signal (T_ref,).
        signal_target: Target signal (T_target,).
        max_offset: Maximum allowed offset in frames.

    Returns:
        Tuple of (offset, correlation_score).
        Positive offset means target is ahead of reference.
    """
    n_ref = len(signal_ref)
    n_target = len(signal_target)

    # Use full cross-correlation
    correlation = np.correlate(signal_ref, signal_target, mode="full")

    # Normalize
    norm = np.sqrt(np.sum(signal_ref ** 2) * np.sum(signal_target ** 2))
    if norm > 1e-8:
        correlation = correlation / norm

    # The zero-lag index in 'full' mode
    zero_lag = n_target - 1

    # Restrict to max_offset range
    search_start = max(0, zero_lag - max_offset)
    search_end = min(len(correlation), zero_lag + max_offset + 1)
    search_range = correlation[search_start:search_end]

    best_idx = np.argmax(search_range)
    best_offset = (search_start + best_idx) - zero_lag
    best_score = search_range[best_idx]

    return int(best_offset), float(best_score)


def apply_offsets(
    poses_dict: Dict[str, np.ndarray],
    confidences_dict: Dict[str, np.ndarray],
    offsets: Dict[str, int],
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """
    Apply temporal offsets and trim to common range.

    Args:
        poses_dict: {'front': (T,17,2), 'left': (T,17,2), ...}
        confidences_dict: {'front': (T,17), ...}
        offsets: {'front': 0, 'left': offset_left, 'right': offset_right}

    Returns:
        Aligned poses and confidences dicts trimmed to common length.
    """
    # Compute effective start and end for each view
    starts = {}
    ends = {}
    for view, offset in offsets.items():
        T = len(poses_dict[view])
        starts[view] = max(0, offset)
        ends[view] = T + min(0, offset)

    # Common range
    max_start = max(starts.values())
    min_end = min(ends.values())
    common_length = min_end - max_start

    if common_length <= 0:
        logger.error("No overlapping frames after synchronization!")
        raise ValueError("Sync offsets too large — no overlapping frames")

    aligned_poses = {}
    aligned_confs = {}
    for view, offset in offsets.items():
        local_start = max_start - offset
        aligned_poses[view] = poses_dict[view][local_start:local_start + common_length]
        aligned_confs[view] = confidences_dict[view][local_start:local_start + common_length]

    return aligned_poses, aligned_confs


def synchronize_views(
    poses_dict: Dict[str, np.ndarray],
    confidences_dict: Dict[str, np.ndarray],
    pelvis_weight: float = 0.5,
    wrist_weight: float = 0.3,
    ankle_weight: float = 0.2,
    correlation_threshold: float = 0.3,
    max_offset_frames: int = 30,
    debug_output_dir: Optional[str] = None,
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray], Dict]:
    """
    Synchronize multi-view poses using velocity cross-correlation.

    Args:
        poses_dict: {'front': (T,17,2), 'left': (T,17,2), 'right': (T,17,2)}
        confidences_dict: {'front': (T,17), ...}
        pelvis_weight: Weight for pelvis signal.
        wrist_weight: Weight for wrist signal.
        ankle_weight: Weight for ankle signal.
        correlation_threshold: Minimum correlation score.
        max_offset_frames: Maximum allowed offset.
        debug_output_dir: If set, saves debug plots and offsets JSON.

    Returns:
        Tuple of (aligned_poses_dict, aligned_confs_dict, sync_info).
    """
    logger.info("Computing synchronization signals...")

    # Compute signals for each view
    signals = {}
    for view_name, poses in poses_dict.items():
        signals[view_name] = compute_sync_signal(
            poses, pelvis_weight, wrist_weight, ankle_weight
        )
        logger.info(f"  [{view_name}] signal length: {len(signals[view_name])}")

    # Cross-correlate left and right against front (reference)
    ref_signal = signals["front"]

    offset_left, score_left = cross_correlate_offset(
        ref_signal, signals["left"], max_offset_frames
    )
    offset_right, score_right = cross_correlate_offset(
        ref_signal, signals["right"], max_offset_frames
    )

    logger.info(f"Sync results:")
    logger.info(f"  left  offset={offset_left:+d} frames, correlation={score_left:.4f}")
    logger.info(f"  right offset={offset_right:+d} frames, correlation={score_right:.4f}")

    # Fallback if correlation is too low
    if score_left < correlation_threshold:
        logger.warning(
            f"Left view correlation {score_left:.4f} < threshold "
            f"{correlation_threshold}. Falling back to offset=0"
        )
        offset_left = 0

    if score_right < correlation_threshold:
        logger.warning(
            f"Right view correlation {score_right:.4f} < threshold "
            f"{correlation_threshold}. Falling back to offset=0"
        )
        offset_right = 0

    offsets = {"front": 0, "left": offset_left, "right": offset_right}

    # Apply offsets
    aligned_poses, aligned_confs = apply_offsets(
        poses_dict, confidences_dict, offsets
    )

    sync_info = {
        "offsets": offsets,
        "correlation_scores": {
            "left": round(score_left, 4),
            "right": round(score_right, 4),
        },
        "aligned_frame_count": len(next(iter(aligned_poses.values()))),
    }

    # Save debug outputs
    if debug_output_dir:
        os.makedirs(debug_output_dir, exist_ok=True)

        # Save offsets JSON
        offsets_path = os.path.join(debug_output_dir, "sync_offsets.json")
        with open(offsets_path, "w") as f:
            json.dump(sync_info, f, indent=2)
        logger.info(f"Saved sync offsets to {offsets_path}")

        # Save sync plot
        try:
            _save_sync_plot(
                signals, offsets,
                os.path.join(debug_output_dir, "sync_plot.png")
            )
        except Exception as e:
            logger.warning(f"Could not save sync plot: {e}")

    logger.info(
        f"Synchronization complete. "
        f"Aligned to {sync_info['aligned_frame_count']} frames."
    )
    return aligned_poses, aligned_confs, sync_info


def _save_sync_plot(
    signals: Dict[str, np.ndarray],
    offsets: Dict[str, int],
    output_path: str,
) -> None:
    """Save before/after alignment signal plot."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    # Before alignment
    ax = axes[0]
    ax.set_title("Velocity Signals — Before Alignment")
    for view_name, sig in signals.items():
        ax.plot(sig, label=view_name, alpha=0.8)
    ax.legend()
    ax.set_xlabel("Frame")
    ax.set_ylabel("Normalized velocity")
    ax.grid(True, alpha=0.3)

    # After alignment
    ax = axes[1]
    ax.set_title("Velocity Signals — After Alignment")
    for view_name, sig in signals.items():
        offset = offsets.get(view_name, 0)
        shifted = np.roll(sig, -offset)
        ax.plot(shifted, label=f"{view_name} (offset={offset:+d})", alpha=0.8)
    ax.legend()
    ax.set_xlabel("Frame")
    ax.set_ylabel("Normalized velocity")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()
    logger.info(f"Saved sync plot to {output_path}")
