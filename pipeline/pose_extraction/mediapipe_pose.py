"""
Step 2: 2D Pose Extraction using MediaPipe

Extracts COCO-17 keypoints from video frames using MediaPipe Pose.
MediaPipe outputs 33 landmarks; we map them to COCO-17.
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# MediaPipe 33 → COCO-17 mapping
# COCO-17 order:
#   0: nose, 1: left_eye, 2: right_eye, 3: left_ear, 4: right_ear,
#   5: left_shoulder, 6: right_shoulder, 7: left_elbow, 8: right_elbow,
#   9: left_wrist, 10: right_wrist, 11: left_hip, 12: right_hip,
#   13: left_knee, 14: right_knee, 15: left_ankle, 16: right_ankle
#
# MediaPipe indices (relevant subset):
#   0: nose, 2: left_eye_inner→left_eye, 5: right_eye_inner→right_eye,
#   7: left_ear, 8: right_ear,
#   11: left_shoulder, 12: right_shoulder,
#   13: left_elbow, 14: right_elbow,
#   15: left_wrist, 16: right_wrist,
#   23: left_hip, 24: right_hip,
#   25: left_knee, 26: right_knee,
#   27: left_ankle, 28: right_ankle
# -------------------------------------------------------------------------

MP33_TO_COCO17 = {
    0: 0,    # nose → nose
    1: 2,    # left_eye → mp left_eye_inner (index 2)
    2: 5,    # right_eye → mp right_eye_inner (index 5)
    3: 7,    # left_ear → mp left_ear
    4: 8,    # right_ear → mp right_ear
    5: 11,   # left_shoulder → mp left_shoulder
    6: 12,   # right_shoulder → mp right_shoulder
    7: 13,   # left_elbow → mp left_elbow
    8: 14,   # right_elbow → mp right_elbow
    9: 15,   # left_wrist → mp left_wrist
    10: 16,  # right_wrist → mp right_wrist
    11: 23,  # left_hip → mp left_hip
    12: 24,  # right_hip → mp right_hip
    13: 25,  # left_knee → mp left_knee
    14: 26,  # right_knee → mp right_knee
    15: 27,  # left_ankle → mp left_ankle
    16: 28,  # right_ankle → mp right_ankle
}

# COCO-17 skeleton connections for visualization
COCO17_SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),        # head
    (5, 6),                                   # shoulders
    (5, 7), (7, 9),                           # left arm
    (6, 8), (8, 10),                          # right arm
    (5, 11), (6, 12),                         # torso
    (11, 12),                                 # hips
    (11, 13), (13, 15),                       # left leg
    (12, 14), (14, 16),                       # right leg
]

COCO17_JOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]


def extract_2d_poses(
    frames: np.ndarray,
    view_name: str = "unknown",
    model_complexity: int = 1,
    min_detection_confidence: float = 0.5,
    min_tracking_confidence: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract COCO-17 2D poses from video frames using MediaPipe.

    Args:
        frames: (T, H, W, 3) BGR frame array.
        view_name: Name tag for logging.
        model_complexity: MediaPipe model complexity (0/1/2).
        min_detection_confidence: Minimum detection confidence.
        min_tracking_confidence: Minimum tracking confidence.

    Returns:
        Tuple of:
            poses: np.ndarray of shape (T, 17, 2) — pixel coordinates (x, y).
            confidences: np.ndarray of shape (T, 17) — per-joint confidence.
    """
    import mediapipe as mp

    mp_pose = mp.solutions.pose
    T, H, W, _ = frames.shape

    poses = np.full((T, 17, 2), np.nan, dtype=np.float32)
    confidences = np.zeros((T, 17), dtype=np.float32)

    logger.info(f"[{view_name}] Extracting 2D poses from {T} frames ({W}x{H})...")

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=model_complexity,
        min_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
    ) as pose:
        for t in range(T):
            # MediaPipe expects RGB
            frame_rgb = cv2.cvtColor(frames[t], cv2.COLOR_BGR2RGB)
            results = pose.process(frame_rgb)

            if results.pose_landmarks is not None:
                landmarks = results.pose_landmarks.landmark

                for coco_idx, mp_idx in MP33_TO_COCO17.items():
                    lm = landmarks[mp_idx]
                    # Convert normalized coords to pixel coords
                    poses[t, coco_idx, 0] = lm.x * W
                    poses[t, coco_idx, 1] = lm.y * H
                    confidences[t, coco_idx] = lm.visibility

            if (t + 1) % 50 == 0 or t == T - 1:
                detected = np.sum(~np.isnan(poses[t, :, 0]))
                logger.info(
                    f"[{view_name}] Frame {t+1}/{T} — "
                    f"{detected}/17 joints detected"
                )

    # Summary statistics
    nan_count = np.sum(np.isnan(poses[:, :, 0]))
    total_joints = T * 17
    nan_pct = 100.0 * nan_count / total_joints
    logger.info(
        f"[{view_name}] Extraction complete. "
        f"Missing joints: {nan_count}/{total_joints} ({nan_pct:.1f}%)"
    )

    return poses, confidences


def draw_pose_overlay(
    frame: np.ndarray,
    keypoints: np.ndarray,
    confidence: np.ndarray,
    conf_threshold: float = 0.3,
) -> np.ndarray:
    """
    Draw COCO-17 skeleton overlay on a frame.

    Args:
        frame: (H, W, 3) BGR image.
        keypoints: (17, 2) pixel coordinates.
        confidence: (17,) visibility scores.
        conf_threshold: Minimum confidence to draw.

    Returns:
        Frame with skeleton drawn.
    """
    overlay = frame.copy()

    # Draw bones
    for j1, j2 in COCO17_SKELETON:
        if (confidence[j1] >= conf_threshold and
                confidence[j2] >= conf_threshold and
                not np.isnan(keypoints[j1, 0]) and
                not np.isnan(keypoints[j2, 0])):
            pt1 = (int(keypoints[j1, 0]), int(keypoints[j1, 1]))
            pt2 = (int(keypoints[j2, 0]), int(keypoints[j2, 1]))
            cv2.line(overlay, pt1, pt2, (0, 255, 0), 2)

    # Draw joints
    for j in range(17):
        if confidence[j] >= conf_threshold and not np.isnan(keypoints[j, 0]):
            pt = (int(keypoints[j, 0]), int(keypoints[j, 1]))
            color = (0, 0, 255) if confidence[j] >= 0.7 else (0, 165, 255)
            cv2.circle(overlay, pt, 4, color, -1)

    return overlay


def save_debug_overlay_video(
    frames: np.ndarray,
    poses: np.ndarray,
    confidences: np.ndarray,
    output_path: str,
    fps: float = 30.0,
) -> None:
    """
    Save a debug video with skeleton overlays.

    Args:
        frames: (T, H, W, 3) BGR frames.
        poses: (T, 17, 2) keypoints.
        confidences: (T, 17) visibility.
        output_path: Output video file path.
        fps: Output frame rate.
    """
    T, H, W, _ = frames.shape
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (W, H))

    for t in range(T):
        overlay = draw_pose_overlay(frames[t], poses[t], confidences[t])
        writer.write(overlay)

    writer.release()
    logger.info(f"Saved debug overlay video: {output_path}")
