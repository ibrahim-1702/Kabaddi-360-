"""
Step 3: Camera Calibration Module

Provides:
- Checkerboard-based calibration capture and solve (for production use).
- Default synthetic calibration parameters (for development/testing).
- Load/save camera parameters as JSON.
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def calibrate_single_camera(
    image_paths: List[str],
    board_size: Tuple[int, int] = (9, 6),
    square_size: float = 0.025,
) -> Optional[Dict]:
    """
    Calibrate a single camera from checkerboard images.

    Args:
        image_paths: Paths to checkerboard images.
        board_size: Interior corners (cols, rows).
        square_size: Physical size of each square in meters.

    Returns:
        Dict with 'K' (3x3 intrinsic), 'dist' (distortion coeffs),
        or None if calibration fails.
    """
    objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)
    objp *= square_size

    obj_points = []
    img_points = []
    img_size = None

    for path in image_paths:
        img = cv2.imread(path)
        if img is None:
            logger.warning(f"Cannot read image: {path}")
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if img_size is None:
            img_size = (gray.shape[1], gray.shape[0])

        ret, corners = cv2.findChessboardCorners(gray, board_size, None)
        if ret:
            corners_refined = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1),
                (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            )
            obj_points.append(objp)
            img_points.append(corners_refined)
        else:
            logger.warning(f"Checkerboard not found in: {path}")

    if len(obj_points) < 3:
        logger.error(
            f"Insufficient calibration images with detected corners: "
            f"{len(obj_points)} (need ≥3)"
        )
        return None

    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, img_size, None, None
    )

    if not ret:
        logger.error("Camera calibration failed")
        return None

    logger.info(f"Calibration successful. Reprojection error: {ret:.4f}")

    return {
        "K": K.tolist(),
        "dist": dist.tolist(),
        "image_size": list(img_size),
    }


def calibrate_stereo_pair(
    images_cam1: List[str],
    images_cam2: List[str],
    K1: np.ndarray,
    dist1: np.ndarray,
    K2: np.ndarray,
    dist2: np.ndarray,
    board_size: Tuple[int, int] = (9, 6),
    square_size: float = 0.025,
) -> Optional[Dict]:
    """
    Compute extrinsic parameters (R, T) between a camera pair.

    Returns:
        Dict with 'R' (3x3) and 'T' (3x1), or None.
    """
    objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)
    objp *= square_size

    obj_points = []
    img_points_1 = []
    img_points_2 = []
    img_size = None

    for p1, p2 in zip(images_cam1, images_cam2):
        img1 = cv2.imread(p1, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(p2, cv2.IMREAD_GRAYSCALE)
        if img1 is None or img2 is None:
            continue

        if img_size is None:
            img_size = (img1.shape[1], img1.shape[0])

        ret1, corners1 = cv2.findChessboardCorners(img1, board_size, None)
        ret2, corners2 = cv2.findChessboardCorners(img2, board_size, None)

        if ret1 and ret2:
            corners1 = cv2.cornerSubPix(
                img1, corners1, (11, 11), (-1, -1),
                (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            )
            corners2 = cv2.cornerSubPix(
                img2, corners2, (11, 11), (-1, -1),
                (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            )
            obj_points.append(objp)
            img_points_1.append(corners1)
            img_points_2.append(corners2)

    if len(obj_points) < 3:
        logger.error("Insufficient stereo calibration pairs")
        return None

    ret, _, _, _, _, R, T, E, F = cv2.stereoCalibrate(
        obj_points, img_points_1, img_points_2,
        K1, dist1, K2, dist2, img_size,
        flags=cv2.CALIB_FIX_INTRINSIC,
    )

    if not ret:
        logger.error("Stereo calibration failed")
        return None

    logger.info(f"Stereo calibration error: {ret:.4f}")
    return {"R": R.tolist(), "T": T.tolist()}


def generate_default_params(
    image_width: int = 1920,
    image_height: int = 1080,
) -> Dict:
    """
    Generate synthetic camera parameters for a 3-camera setup
    arranged at 0°, -60°, +60° (front, left, right) around the subject.

    This is for DEVELOPMENT AND TESTING ONLY.
    Real calibration data is required for production.

    Args:
        image_width: Frame width in pixels.
        image_height: Frame height in pixels.

    Returns:
        Dict with camera parameters for front, left, right.
    """
    # Approximate intrinsics (focal length ~frame width)
    fx = fy = float(image_width)
    cx = image_width / 2.0
    cy = image_height / 2.0

    K = [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
    dist = [[0, 0, 0, 0, 0]]

    # Camera distance from origin (in meters)
    cam_dist = 3.0

    # Front camera: at (0, 0, -cam_dist), looking at origin
    R_front = np.eye(3)
    T_front = np.array([[0], [0], [cam_dist]])

    # Left camera: at (cam_dist * sin(60°), 0, -cam_dist * cos(60°))
    angle_left = np.radians(60)
    R_left = np.array([
        [np.cos(angle_left), 0, np.sin(angle_left)],
        [0, 1, 0],
        [-np.sin(angle_left), 0, np.cos(angle_left)],
    ])
    T_left = np.array([
        [-cam_dist * np.sin(angle_left)],
        [0],
        [cam_dist * np.cos(angle_left)],
    ])

    # Right camera: at (-cam_dist * sin(60°), 0, -cam_dist * cos(60°))
    angle_right = np.radians(-60)
    R_right = np.array([
        [np.cos(angle_right), 0, np.sin(angle_right)],
        [0, 1, 0],
        [-np.sin(angle_right), 0, np.cos(angle_right)],
    ])
    T_right = np.array([
        [-cam_dist * np.sin(angle_right)],
        [0],
        [cam_dist * np.cos(angle_right)],
    ])

    params = {
        "_note": "SYNTHETIC DEFAULT — replace with real calibration data",
        "is_default": True,
        "image_size": [image_width, image_height],
        "cameras": {
            "front": {
                "K": K,
                "dist": dist,
                "R": R_front.tolist(),
                "T": T_front.tolist(),
            },
            "left": {
                "K": K,
                "dist": dist,
                "R": R_left.tolist(),
                "T": T_left.tolist(),
            },
            "right": {
                "K": K,
                "dist": dist,
                "R": R_right.tolist(),
                "T": T_right.tolist(),
            },
        },
    }

    logger.warning("Generated SYNTHETIC camera parameters — not for production use")
    return params


def save_camera_params(params: Dict, output_path: str) -> None:
    """Save camera parameters to JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(params, f, indent=2)
    logger.info(f"Saved camera parameters to {output_path}")


def load_camera_params(json_path: str) -> Dict:
    """
    Load camera parameters from JSON file.

    Returns:
        Dict with 'cameras' key containing per-camera K, R, T.

    Raises:
        FileNotFoundError: If JSON file does not exist.
    """
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"Camera params not found: {json_path}")

    with open(json_path, "r") as f:
        params = json.load(f)

    is_default = params.get("is_default", False)
    if is_default:
        logger.warning(
            "Using SYNTHETIC calibration — 3D results may be distorted. "
            "Run calibration with real checkerboard data for production."
        )

    # Convert lists back to numpy arrays for computation
    for cam_name, cam in params["cameras"].items():
        cam["K"] = np.array(cam["K"], dtype=np.float64)
        cam["dist"] = np.array(cam["dist"], dtype=np.float64)
        cam["R"] = np.array(cam["R"], dtype=np.float64)
        cam["T"] = np.array(cam["T"], dtype=np.float64)

    logger.info(f"Loaded camera parameters for: {list(params['cameras'].keys())}")
    return params
