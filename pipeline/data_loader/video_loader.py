"""
Step 1: Multi-View Video Loader

Loads 3 synchronized videos (front, left, right), validates FPS/duration,
and resamples frames to match if needed.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def get_video_info(video_path: str) -> Dict:
    """
    Extract metadata from a video file.

    Args:
        video_path: Absolute path to video file.

    Returns:
        Dict with keys: fps, frame_count, width, height, duration_s.

    Raises:
        FileNotFoundError: If video file does not exist.
        RuntimeError: If video cannot be opened.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_s = frame_count / fps if fps > 0 else 0.0

    cap.release()

    return {
        "path": video_path,
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration_s": round(duration_s, 3),
    }


def read_all_frames(video_path: str) -> np.ndarray:
    """
    Read all frames from a video file.

    Args:
        video_path: Path to video file.

    Returns:
        np.ndarray of shape (N, H, W, 3) in BGR format.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)

    cap.release()

    if len(frames) == 0:
        raise RuntimeError(f"No frames read from: {video_path}")

    return np.array(frames)


def resample_frames(frames: np.ndarray, target_count: int) -> np.ndarray:
    """
    Resample frame array to target_count using uniform index selection.

    Args:
        frames: (N, H, W, 3) array.
        target_count: Desired number of frames.

    Returns:
        (target_count, H, W, 3) array.
    """
    n = len(frames)
    if n == target_count:
        return frames
    indices = np.linspace(0, n - 1, target_count, dtype=int)
    return frames[indices]


def load_multiview_videos(
    front_path: str,
    left_path: str,
    right_path: str,
    fps_tolerance: float = 1.0,
    duration_tolerance: float = 0.5,
    debug_output_dir: Optional[str] = None,
) -> Dict[str, np.ndarray]:
    """
    Load 3 synchronized videos and validate/align frame counts.

    Args:
        front_path: Path to front-view video.
        left_path: Path to left-view video.
        right_path: Path to right-view video.
        fps_tolerance: Maximum allowed FPS difference.
        duration_tolerance: Maximum allowed duration difference (seconds).
        debug_output_dir: If set, saves video_info.json here.

    Returns:
        Dict with keys 'front', 'left', 'right', each containing
        an np.ndarray of shape (T, H, W, 3).
    """
    view_paths = {"front": front_path, "left": left_path, "right": right_path}

    # --- Collect metadata ---
    infos = {}
    for view_name, path in view_paths.items():
        info = get_video_info(path)
        infos[view_name] = info
        logger.info(
            f"[{view_name}] FPS={info['fps']:.2f}  frames={info['frame_count']}  "
            f"res={info['width']}x{info['height']}  duration={info['duration_s']}s"
        )

    # --- Validate FPS ---
    fps_values = [infos[v]["fps"] for v in infos]
    fps_spread = max(fps_values) - min(fps_values)
    if fps_spread > fps_tolerance:
        logger.warning(
            f"FPS mismatch across views: {fps_values}. Spread={fps_spread:.2f} "
            f"exceeds tolerance={fps_tolerance:.2f}. Proceeding with resampling."
        )
    else:
        logger.info(f"FPS check passed (spread={fps_spread:.2f})")

    # --- Validate duration ---
    durations = [infos[v]["duration_s"] for v in infos]
    dur_spread = max(durations) - min(durations)
    if dur_spread > duration_tolerance:
        logger.warning(
            f"Duration mismatch: {durations}. Spread={dur_spread:.3f}s "
            f"exceeds tolerance={duration_tolerance:.1f}s. Resampling to shortest."
        )
    else:
        logger.info(f"Duration check passed (spread={dur_spread:.3f}s)")

    # --- Read frames ---
    frames = {}
    for view_name, path in view_paths.items():
        logger.info(f"Reading frames from [{view_name}]...")
        frames[view_name] = read_all_frames(path)
        logger.info(f"  Read {len(frames[view_name])} frames")

    # --- Resample to match shortest ---
    counts = {v: len(frames[v]) for v in frames}
    min_count = min(counts.values())

    for view_name in frames:
        if len(frames[view_name]) != min_count:
            logger.info(
                f"Resampling [{view_name}] from {len(frames[view_name])} "
                f"to {min_count} frames"
            )
            frames[view_name] = resample_frames(frames[view_name], min_count)

    # --- Save debug info ---
    if debug_output_dir:
        os.makedirs(debug_output_dir, exist_ok=True)
        debug_info = {
            view_name: {
                **infos[view_name],
                "final_frame_count": int(len(frames[view_name])),
            }
            for view_name in infos
        }
        debug_path = os.path.join(debug_output_dir, "video_info.json")
        with open(debug_path, "w") as f:
            json.dump(debug_info, f, indent=2)
        logger.info(f"Saved video info to {debug_path}")

    logger.info(
        f"Video loading complete. Final frame count: {min_count} per view."
    )
    return frames
