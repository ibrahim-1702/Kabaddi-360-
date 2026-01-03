import numpy as np
from joints import (
    LEFT_HIP, RIGHT_HIP,
    LEFT_SHOULDER, RIGHT_SHOULDER
)

# -------------------------------------------------------
# 1. INVALID JOINT DETECTION
# -------------------------------------------------------

def mark_valid_joints(poses):
    valid = np.isfinite(poses).all(axis=2)
    valid &= ~(np.abs(poses).sum(axis=2) == 0)
    return valid


# -------------------------------------------------------
# 2. TEMPORAL INTERPOLATION
# -------------------------------------------------------

def interpolate_missing_joints(poses):
    poses = poses.copy()
    T, J, _ = poses.shape
    valid = mark_valid_joints(poses)

    for j in range(J):
        for c in range(2):
            series = poses[:, j, c]
            v = valid[:, j]

            if v.sum() < 2:
                continue

            poses[:, j, c] = np.interp(
                np.arange(T),
                np.where(v)[0],
                series[v]
            )
    return poses


# -------------------------------------------------------
# 3. PELVIS CENTERING
# -------------------------------------------------------

def pelvis_centering(poses):
    pelvis = (poses[:, LEFT_HIP] + poses[:, RIGHT_HIP]) * 0.5
    return poses - pelvis[:, None, :]


# -------------------------------------------------------
# 4. SCALE NORMALIZATION (TORSO-BASED)
# -------------------------------------------------------

def scale_normalization(poses, eps=1e-6):
    shoulders = (poses[:, LEFT_SHOULDER] + poses[:, RIGHT_SHOULDER]) * 0.5
    hips = (poses[:, LEFT_HIP] + poses[:, RIGHT_HIP]) * 0.5

    torso_len = np.linalg.norm(shoulders - hips, axis=1)
    scale = torso_len[:, None, None] + eps

    return poses / scale


# -------------------------------------------------------
# 5. OUTLIER FRAME SUPPRESSION
# -------------------------------------------------------

def suppress_outlier_frames(poses, z_thresh=3.0):
    velocity = np.linalg.norm(np.diff(poses, axis=0), axis=(1, 2))
    z = (velocity - velocity.mean()) / (velocity.std() + 1e-6)

    clean = poses.copy()
    bad = np.where(np.abs(z) > z_thresh)[0] + 1

    for f in bad:
        clean[f] = clean[f - 1]

    return clean


# -------------------------------------------------------
# 6. TEMPORAL SMOOTHING (EMA)
# -------------------------------------------------------

def ema_smoothing(poses, alpha=0.75):
    smooth = poses.copy()

    for t in range(1, poses.shape[0]):
        smooth[t] = alpha * smooth[t - 1] + (1 - alpha) * poses[t]

    return smooth


# -------------------------------------------------------
# 7. LEVEL-1 PIPELINE
# -------------------------------------------------------

def clean_level1_poses(poses_2d):
    """
    Input:
        poses_2d -> (T, J, 2)

    Output:
        clean poses -> (T, J, 2)
    """

    poses = interpolate_missing_joints(poses_2d)
    poses = pelvis_centering(poses)
    poses = scale_normalization(poses)
    poses = suppress_outlier_frames(poses)
    poses = ema_smoothing(poses)

    return poses
