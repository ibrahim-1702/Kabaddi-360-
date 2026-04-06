"""
Step 5: Multi-View 3D Triangulation

Triangulates 3D joint positions from 2D poses across 2-3 calibrated views
using OpenCV's DLT (Direct Linear Transform).
"""

import logging
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def build_projection_matrix(K: np.ndarray, R: np.ndarray, T: np.ndarray) -> np.ndarray:
    """
    Build 3x4 projection matrix P = K @ [R | T].

    Args:
        K: (3, 3) intrinsic matrix.
        R: (3, 3) rotation matrix.
        T: (3, 1) translation vector.

    Returns:
        (3, 4) projection matrix.
    """
    RT = np.hstack([R, T.reshape(3, 1)])
    P = K @ RT
    return P


def triangulate_point_pair(
    P1: np.ndarray,
    P2: np.ndarray,
    pt1: np.ndarray,
    pt2: np.ndarray,
) -> np.ndarray:
    """
    Triangulate a single 3D point from 2 views using OpenCV.

    Args:
        P1, P2: (3, 4) projection matrices.
        pt1, pt2: (2,) pixel coordinates.

    Returns:
        (3,) 3D world coordinates.
    """
    pts1 = pt1.reshape(1, 1, 2).astype(np.float64)
    pts2 = pt2.reshape(1, 1, 2).astype(np.float64)

    points_4d = cv2.triangulatePoints(P1, P2, pts1, pts2)
    # Convert from homogeneous
    point_3d = points_4d[:3, 0] / points_4d[3, 0]
    return point_3d


def triangulate_point_multiview(
    projections: List[np.ndarray],
    points_2d: List[np.ndarray],
) -> np.ndarray:
    """
    Triangulate a single 3D point from N views using DLT.

    Uses the N-view DLT formulation: build a 2N x 4 matrix A,
    then solve via SVD.

    Args:
        projections: List of (3, 4) projection matrices.
        points_2d: List of (2,) pixel coordinates.

    Returns:
        (3,) 3D world coordinates.
    """
    n_views = len(projections)

    if n_views == 2:
        return triangulate_point_pair(
            projections[0], projections[1],
            points_2d[0], points_2d[1]
        )

    # N-view DLT
    A = np.zeros((2 * n_views, 4))
    for i in range(n_views):
        P = projections[i]
        x, y = points_2d[i]
        A[2 * i] = x * P[2] - P[0]
        A[2 * i + 1] = y * P[2] - P[1]

    _, _, Vt = np.linalg.svd(A)
    X = Vt[-1]
    X = X[:3] / X[3]
    return X


def triangulate_poses(
    synced_poses: Dict[str, np.ndarray],
    synced_confs: Dict[str, np.ndarray],
    camera_params: Dict,
    confidence_threshold: float = 0.5,
    max_reprojection_error: float = 50.0,
) -> Tuple[np.ndarray, Dict]:
    """
    Triangulate 3D poses from synchronized multi-view 2D poses.

    Args:
        synced_poses: {'front': (T,17,2), 'left': (T,17,2), 'right': (T,17,2)}
        synced_confs: {'front': (T,17), 'left': (T,17), 'right': (T,17)}
        camera_params: Dict with 'cameras' key containing per-camera K, R, T.
        confidence_threshold: Minimum confidence to use a 2D detection.
        max_reprojection_error: Maximum reprojection error (pixels).

    Returns:
        Tuple of:
            poses_3d: (T, 17, 3) array. NaN for failed triangulations.
            stats: Dict with triangulation statistics.
    """
    view_names = list(synced_poses.keys())
    T = len(next(iter(synced_poses.values())))

    logger.info(f"Triangulating {T} frames across {len(view_names)} views...")

    # Build projection matrices
    proj_matrices = {}
    for view_name in view_names:
        cam = camera_params["cameras"][view_name]
        P = build_projection_matrix(cam["K"], cam["R"], cam["T"])
        proj_matrices[view_name] = P

    # Triangulate
    poses_3d = np.full((T, 17, 3), np.nan, dtype=np.float64)
    total_joints = T * 17
    success_count = 0
    fail_reasons = {"insufficient_views": 0, "high_reprojection": 0}

    for t in range(T):
        for j in range(17):
            # Collect valid 2D observations
            valid_projs = []
            valid_pts = []

            for view_name in view_names:
                conf = synced_confs[view_name][t, j]
                pt = synced_poses[view_name][t, j]

                if conf >= confidence_threshold and not np.isnan(pt[0]):
                    valid_projs.append(proj_matrices[view_name])
                    valid_pts.append(pt)

            if len(valid_projs) < 2:
                fail_reasons["insufficient_views"] += 1
                continue

            try:
                point_3d = triangulate_point_multiview(valid_projs, valid_pts)

                # Validate: check for explosion
                if np.any(np.abs(point_3d) > 100.0):
                    fail_reasons["high_reprojection"] += 1
                    continue

                # Reprojection error check
                max_err = 0
                for P, pt2d in zip(valid_projs, valid_pts):
                    projected = P @ np.append(point_3d, 1.0)
                    projected = projected[:2] / projected[2]
                    err = np.linalg.norm(projected - pt2d)
                    max_err = max(max_err, err)

                if max_err > max_reprojection_error:
                    fail_reasons["high_reprojection"] += 1
                    continue

                poses_3d[t, j] = point_3d
                success_count += 1

            except Exception as e:
                logger.debug(f"Triangulation failed at t={t}, j={j}: {e}")
                fail_reasons["high_reprojection"] += 1

        if (t + 1) % 50 == 0 or t == T - 1:
            logger.info(f"  Frame {t+1}/{T} processed")

    success_pct = 100.0 * success_count / total_joints
    stats = {
        "total_joints": total_joints,
        "successful": success_count,
        "success_pct": round(success_pct, 2),
        "failed_insufficient_views": fail_reasons["insufficient_views"],
        "failed_high_reprojection": fail_reasons["high_reprojection"],
    }

    logger.info(
        f"Triangulation complete: {success_count}/{total_joints} "
        f"({success_pct:.1f}%) joints triangulated"
    )
    for reason, count in fail_reasons.items():
        if count > 0:
            logger.info(f"  Failed ({reason}): {count}")

    return poses_3d, stats
