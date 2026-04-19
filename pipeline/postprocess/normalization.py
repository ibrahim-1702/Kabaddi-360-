"""
Step 6b (Step 7 in prompt): 3D Pose Normalization

Root-relative centering and bone-length normalization.
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# COCO-17 joint indices
LEFT_HIP = 11
RIGHT_HIP = 12
NOSE = 0
LEFT_ANKLE = 15
RIGHT_ANKLE = 16
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6

# Reference bone lengths for normalization (approximate human proportions in meters)
# These define the expected absolute distances between connected joints.
COCO17_BONE_PAIRS = [
    (5, 7),   # left_shoulder → left_elbow
    (7, 9),   # left_elbow → left_wrist
    (6, 8),   # right_shoulder → right_elbow
    (8, 10),  # right_elbow → right_wrist
    (5, 11),  # left_shoulder → left_hip
    (6, 12),  # right_shoulder → right_hip
    (11, 13), # left_hip → left_knee
    (13, 15), # left_knee → left_ankle
    (12, 14), # right_hip → right_knee
    (14, 16), # right_knee → right_ankle
    (5, 6),   # left_shoulder → right_shoulder
    (11, 12), # left_hip → right_hip
]


def compute_body_height(poses_3d: np.ndarray) -> float:
    """
    Estimate body height as max(head_to_ankle) across all frames.

    Args:
        poses_3d: (T, 17, 3) array.

    Returns:
        Estimated body height (in whatever units the poses are in).
    """
    # Head = nose, feet = midpoint of ankles
    head = poses_3d[:, NOSE, :]
    ankle_mid = (poses_3d[:, LEFT_ANKLE, :] + poses_3d[:, RIGHT_ANKLE, :]) / 2.0

    heights = np.linalg.norm(head - ankle_mid, axis=1)

    # Use median to be robust to outliers
    height = float(np.nanmedian(heights))
    logger.info(f"Estimated body height: {height:.4f} (median across frames)")
    return height


def normalize_scale(
    poses_3d: np.ndarray,
    target_height: float = 1.7,
) -> np.ndarray:
    """
    Scale 3D poses so that body height matches target.

    Args:
        poses_3d: (T, 17, 3) array.
        target_height: Desired body height in meters.

    Returns:
        (T, 17, 3) scaled array.
    """
    current_height = compute_body_height(poses_3d)

    if current_height < 1e-6:
        logger.warning("Body height is near zero — skipping scale normalization")
        return poses_3d

    scale_factor = target_height / current_height
    logger.info(
        f"Scaling: current_height={current_height:.4f}, "
        f"target={target_height}, scale_factor={scale_factor:.4f}"
    )

    return poses_3d * scale_factor


def center_on_root(poses_3d: np.ndarray) -> np.ndarray:
    """
    Convert to root-relative coordinates (root = pelvis midpoint).

    Args:
        poses_3d: (T, 17, 3) array.

    Returns:
        (T, 17, 3) root-relative array. Pelvis is at origin each frame.
    """
    root = (poses_3d[:, LEFT_HIP, :] + poses_3d[:, RIGHT_HIP, :]) / 2.0
    result = poses_3d - root[:, np.newaxis, :]

    logger.info("Applied root-relative centering (pelvis = origin)")
    return result


def enforce_bone_lengths(
    poses_3d: np.ndarray,
    iterations: int = 3,
) -> np.ndarray:
    """
    Enforce consistent bone lengths across frames using iterative projection.

    Computes the median bone length for each bone pair across all frames,
    then adjusts child joints to maintain that length.

    Args:
        poses_3d: (T, 17, 3) array.
        iterations: Number of enforcement iterations.

    Returns:
        (T, 17, 3) bone-length-normalized array.
    """
    result = poses_3d.copy()
    T = result.shape[0]

    # Compute target bone lengths (median across frames)
    target_lengths = {}
    for parent, child in COCO17_BONE_PAIRS:
        bone_vecs = result[:, child, :] - result[:, parent, :]
        lengths = np.linalg.norm(bone_vecs, axis=1)
        valid = lengths[~np.isnan(lengths)]
        if len(valid) > 0:
            target_lengths[(parent, child)] = float(np.median(valid))

    logger.info(f"Computed {len(target_lengths)} target bone lengths")

    # Iterative enforcement
    for iteration in range(iterations):
        max_correction = 0
        for (parent, child), target_len in target_lengths.items():
            for t in range(T):
                bone_vec = result[t, child, :] - result[t, parent, :]
                current_len = np.linalg.norm(bone_vec)

                if current_len < 1e-8:
                    continue

                correction = target_len / current_len
                if abs(correction - 1.0) > 0.001:
                    result[t, child, :] = (
                        result[t, parent, :] + bone_vec * correction
                    )
                    max_correction = max(max_correction, abs(correction - 1.0))

        logger.debug(
            f"Bone length enforcement iter {iteration+1}: "
            f"max_correction={max_correction:.6f}"
        )

    logger.info(f"Bone length normalization complete ({iterations} iterations)")
    return result


def normalize_poses(
    poses_3d: np.ndarray,
    target_height: float = 1.7,
    enforce_bones: bool = True,
) -> np.ndarray:
    """
    Full normalization pipeline: scale → root-center → bone enforcement.

    Args:
        poses_3d: (T, 17, 3) smoothed 3D poses.
        target_height: Target body height in meters.
        enforce_bones: Whether to enforce bone-length consistency.

    Returns:
        (T, 17, 3) normalized poses.
    """
    logger.info(f"Normalizing 3D poses ({poses_3d.shape})...")

    # Step 1: Scale to target height
    result = normalize_scale(poses_3d, target_height)

    # Step 2: Center on root (pelvis)
    result = center_on_root(result)

    # Step 3: Enforce bone lengths
    if enforce_bones:
        result = enforce_bone_lengths(result)

    logger.info("Normalization complete")
    return result
