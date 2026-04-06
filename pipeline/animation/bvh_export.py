"""
Step 7: BVH Animation Export (Fixed)

Converts 3D joint positions into BVH format using proper
parent-relative rotation decomposition.
"""

import logging
import os
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# COCO-17 Skeleton Hierarchy for BVH
#
# BVH hierarchy rooted at pelvis (virtual joint = midpoint of hips).
# Virtual joints: Pelvis, Spine (midpoint of shoulders).
#
# Hierarchy:
#   Pelvis (root)
#     ├── Spine
#     │     ├── Head
#     │     ├── LeftShoulder → LeftElbow → LeftWrist
#     │     └── RightShoulder → RightElbow → RightWrist
#     ├── LeftHip → LeftKnee → LeftAnkle
#     └── RightHip → RightKnee → RightAnkle
# -------------------------------------------------------------------------

BVH_JOINTS = [
    {"name": "Pelvis",         "type": "virtual", "source": "pelvis"},       # 0
    {"name": "Spine",          "type": "virtual", "source": "spine"},        # 1
    {"name": "Head",           "type": "coco17",  "source": 0},              # 2
    {"name": "LeftShoulder",   "type": "coco17",  "source": 5},              # 3
    {"name": "LeftElbow",      "type": "coco17",  "source": 7},              # 4
    {"name": "LeftWrist",      "type": "coco17",  "source": 9},              # 5
    {"name": "RightShoulder",  "type": "coco17",  "source": 6},              # 6
    {"name": "RightElbow",     "type": "coco17",  "source": 8},              # 7
    {"name": "RightWrist",     "type": "coco17",  "source": 10},             # 8
    {"name": "LeftHip",        "type": "coco17",  "source": 11},             # 9
    {"name": "LeftKnee",       "type": "coco17",  "source": 13},             # 10
    {"name": "LeftAnkle",      "type": "coco17",  "source": 15},             # 11
    {"name": "RightHip",       "type": "coco17",  "source": 12},             # 12
    {"name": "RightKnee",      "type": "coco17",  "source": 14},             # 13
    {"name": "RightAnkle",     "type": "coco17",  "source": 16},             # 14
]

PARENT_IDX = [-1, 0, 1, 1, 3, 4, 1, 6, 7, 0, 9, 10, 0, 12, 13]

CHILDREN = {}
for child_i, par_i in enumerate(PARENT_IDX):
    CHILDREN.setdefault(par_i, []).append(child_i)


def get_bvh_positions(poses_3d: np.ndarray) -> np.ndarray:
    """
    Compute positions for all 15 BVH joints from COCO-17 poses.

    Args:
        poses_3d: (T, 17, 3) COCO-17 3D poses.

    Returns:
        (T, 15, 3) BVH joint positions.
    """
    T = poses_3d.shape[0]
    positions = np.zeros((T, len(BVH_JOINTS), 3))

    for i, joint in enumerate(BVH_JOINTS):
        if joint["type"] == "coco17":
            positions[:, i, :] = poses_3d[:, joint["source"], :]
        elif joint["source"] == "pelvis":
            positions[:, i, :] = (poses_3d[:, 11, :] + poses_3d[:, 12, :]) / 2.0
        elif joint["source"] == "spine":
            positions[:, i, :] = (poses_3d[:, 5, :] + poses_3d[:, 6, :]) / 2.0

    return positions


def _rotation_matrix_from_vectors(vec_from: np.ndarray, vec_to: np.ndarray) -> np.ndarray:
    """
    Compute 3x3 rotation matrix that rotates vec_from to vec_to.
    Uses Rodrigues' rotation formula.
    """
    a = vec_from / (np.linalg.norm(vec_from) + 1e-10)
    b = vec_to / (np.linalg.norm(vec_to) + 1e-10)

    v = np.cross(a, b)
    c = np.dot(a, b)
    s = np.linalg.norm(v)

    if s < 1e-8:
        if c > 0:
            return np.eye(3)
        else:
            # 180 degree rotation — pick perpendicular axis
            perp = np.array([1, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1, 0])
            perp = perp - np.dot(perp, a) * a
            perp = perp / (np.linalg.norm(perp) + 1e-10)
            return 2 * np.outer(perp, perp) - np.eye(3)

    vx = np.array([[0, -v[2], v[1]],
                    [v[2], 0, -v[0]],
                    [-v[1], v[0], 0]])
    R = np.eye(3) + vx + vx @ vx * (1 - c) / (s * s + 1e-10)
    return R


def _rotation_matrix_to_euler_zxy(R: np.ndarray) -> Tuple[float, float, float]:
    """
    Decompose rotation matrix to ZXY Euler angles (in degrees).
    BVH standard uses ZXY rotation order.

    Returns: (x_rot, y_rot, z_rot) in degrees.
    """
    # ZXY decomposition: R = Rz * Rx * Ry
    # R[1,2] = -sin(x)
    sx = -R[1, 2]
    sx = np.clip(sx, -1.0, 1.0)
    x = np.arcsin(sx)

    if abs(abs(sx) - 1.0) < 1e-6:
        # Gimbal lock
        y = 0.0
        z = np.arctan2(-R[2, 0], R[0, 0])
    else:
        cx = np.cos(x)
        y = np.arctan2(R[0, 2] / cx, R[2, 2] / cx)
        z = np.arctan2(R[1, 0] / cx, R[1, 1] / cx)

    return (np.degrees(x), np.degrees(y), np.degrees(z))


def compute_rotations(positions: np.ndarray) -> np.ndarray:
    """
    Compute parent-relative Euler rotations for each BVH joint.

    For each bone (parent→child), computes the rotation needed to align
    the rest-pose bone direction to the current-frame bone direction,
    relative to the parent's accumulated rotation.

    Args:
        positions: (T, 15, 3) BVH joint positions.

    Returns:
        (T, 15, 3) Euler angles (x, y, z) in degrees per joint per frame.
    """
    T, J, _ = positions.shape
    rotations = np.zeros((T, J, 3))

    # Compute rest-pose bone directions from frame 0
    rest_dirs = {}
    for j in range(J):
        children = CHILDREN.get(j, [])
        if children:
            # Average direction to children in rest pose
            dirs = []
            for c in children:
                d = positions[0, c, :] - positions[0, j, :]
                n = np.linalg.norm(d)
                if n > 1e-8:
                    dirs.append(d / n)
            if dirs:
                avg = np.mean(dirs, axis=0)
                n = np.linalg.norm(avg)
                rest_dirs[j] = avg / n if n > 1e-8 else np.array([0, 1, 0])
            else:
                rest_dirs[j] = np.array([0, 1, 0])

    # For each frame, compute local rotations
    for t in range(T):
        parent_world_rot = {-1: np.eye(3)}  # root has identity parent rotation

        for j in range(J):
            parent_j = PARENT_IDX[j]
            parent_rot = parent_world_rot.get(parent_j, np.eye(3))

            children = CHILDREN.get(j, [])
            if not children:
                parent_world_rot[j] = parent_rot
                continue

            # Current bone direction (average across children)
            dirs = []
            for c in children:
                d = positions[t, c, :] - positions[t, j, :]
                n = np.linalg.norm(d)
                if n > 1e-8:
                    dirs.append(d / n)

            if not dirs:
                parent_world_rot[j] = parent_rot
                continue

            current_dir = np.mean(dirs, axis=0)
            n = np.linalg.norm(current_dir)
            if n < 1e-8:
                parent_world_rot[j] = parent_rot
                continue
            current_dir /= n

            rest_dir = rest_dirs.get(j, np.array([0, 1, 0]))

            # World rotation for this bone
            world_rot = _rotation_matrix_from_vectors(rest_dir, current_dir)

            # Local rotation = inverse(parent_world) * world_rot
            local_rot = parent_rot.T @ world_rot

            rx, ry, rz = _rotation_matrix_to_euler_zxy(local_rot)
            rotations[t, j] = [rx, ry, rz]

            # Store world rotation for children
            parent_world_rot[j] = world_rot

    return rotations


def _write_hierarchy(f, joint_idx: int, offsets: np.ndarray, indent: int = 0):
    """Recursively write BVH HIERARCHY section."""
    prefix = "  " * indent
    name = BVH_JOINTS[joint_idx]["name"]
    children = CHILDREN.get(joint_idx, [])

    if indent == 0:
        f.write(f"ROOT {name}\n")
    else:
        f.write(f"{prefix}JOINT {name}\n")

    f.write(f"{prefix}{{\n")
    ox, oy, oz = offsets[joint_idx]
    f.write(f"{prefix}  OFFSET {ox:.6f} {oy:.6f} {oz:.6f}\n")

    if indent == 0:
        f.write(f"{prefix}  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation\n")
    else:
        f.write(f"{prefix}  CHANNELS 3 Zrotation Xrotation Yrotation\n")

    if children:
        for child_idx in children:
            _write_hierarchy(f, child_idx, offsets, indent + 1)
    else:
        f.write(f"{prefix}  End Site\n")
        f.write(f"{prefix}  {{\n")
        f.write(f"{prefix}    OFFSET 0.000000 0.100000 0.000000\n")
        f.write(f"{prefix}  }}\n")

    f.write(f"{prefix}}}\n")


def export_bvh(
    poses_3d: np.ndarray,
    fps: float = 30.0,
    output_path: str = "animation.bvh",
) -> None:
    """
    Export 3D poses to BVH format with proper parent-relative rotations.

    Args:
        poses_3d: (T, 17, 3) normalized 3D poses.
        fps: Animation frame rate.
        output_path: Output BVH file path.
    """
    logger.info(f"Exporting BVH: {poses_3d.shape[0]} frames at {fps} FPS")

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Compute BVH joint positions
    positions = get_bvh_positions(poses_3d)
    T, J, _ = positions.shape

    # Compute rest-pose offsets (parent → child in frame 0)
    offsets = np.zeros((J, 3))
    for j in range(J):
        par = PARENT_IDX[j]
        if par >= 0:
            offsets[j] = positions[0, j] - positions[0, par]

    # Compute rotations
    rotations = compute_rotations(positions)

    frame_time = 1.0 / fps

    with open(output_path, "w") as f:
        f.write("HIERARCHY\n")
        _write_hierarchy(f, 0, offsets)

        f.write("MOTION\n")
        f.write(f"Frames: {T}\n")
        f.write(f"Frame Time: {frame_time:.6f}\n")

        for t in range(T):
            values = []
            # Root: position + rotation
            values.extend(positions[t, 0].tolist())
            values.extend([rotations[t, 0, 2], rotations[t, 0, 0], rotations[t, 0, 1]])

            # Other joints: rotation only (ZXY order)
            for j in range(1, J):
                values.extend([rotations[t, j, 2], rotations[t, j, 0], rotations[t, j, 1]])

            f.write(" ".join(f"{v:.6f}" for v in values) + "\n")

    logger.info(f"BVH exported: {output_path} ({T} frames, {J} joints)")
