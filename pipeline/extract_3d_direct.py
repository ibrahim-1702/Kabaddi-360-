"""
MediaPipe Native 3D Extraction + Direct Blender Retarget

This script does everything in one file:
  1. Reads the front video
  2. Extracts MediaPipe's WORLD 3D landmarks (NOT pixel coordinates)
  3. Saves 3D poses as .npy
  4. Generates a Blender-ready Python script

MediaPipe's pose_world_landmarks provides anatomically valid 3D positions
in meters, centered at the hip midpoint. This bypasses the broken
multi-view triangulation with synthetic cameras entirely.

Usage:
    python pipeline/extract_3d_direct.py --technique Bonus --player Player-1
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("extract_3d")

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# MediaPipe 33 → COCO-17 mapping (same as mediapipe_pose.py)
MP33_TO_COCO17 = {
    0: 0,    # nose
    1: 2,    # left_eye
    2: 5,    # right_eye
    3: 7,    # left_ear
    4: 8,    # right_ear
    5: 11,   # left_shoulder
    6: 12,   # right_shoulder
    7: 13,   # left_elbow
    8: 14,   # right_elbow
    9: 15,   # left_wrist
    10: 16,  # right_wrist
    11: 23,  # left_hip
    12: 24,  # right_hip
    13: 25,  # left_knee
    14: 26,  # right_knee
    15: 27,  # left_ankle
    16: 28,  # right_ankle
}

JOINT_NAMES = [
    "nose", "L_eye", "R_eye", "L_ear", "R_ear",
    "L_sho", "R_sho", "L_elb", "R_elb",
    "L_wri", "R_wri", "L_hip", "R_hip",
    "L_kne", "R_kne", "L_ank", "R_ank",
]

SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]


def extract_mediapipe_3d(video_path, max_frames=None):
    """
    Extract MediaPipe's native WORLD 3D landmarks.

    Returns:
        poses_3d: (T, 17, 3) — 3D positions in meters (hip-centered)
        poses_2d: (T, 17, 2) — 2D pixel positions
        confidences: (T, 17) — visibility scores
    """
    import mediapipe as mp

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if max_frames:
        total_frames = min(total_frames, max_frames)

    logger.info(f"Video: {W}x{H} @ {fps} FPS, {total_frames} frames")

    poses_3d = np.full((total_frames, 17, 3), np.nan, dtype=np.float32)
    poses_2d = np.full((total_frames, 17, 2), np.nan, dtype=np.float32)
    confidences = np.zeros((total_frames, 17), dtype=np.float32)
    frames_bgr = []

    mp_pose = mp.solutions.pose

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=2,  # highest for best 3D
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        smooth_landmarks=True,
    ) as pose:
        for t in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break

            frames_bgr.append(frame)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)

            if results.pose_world_landmarks is not None:
                world_lms = results.pose_world_landmarks.landmark
                for coco_idx, mp_idx in MP33_TO_COCO17.items():
                    lm = world_lms[mp_idx]
                    # MediaPipe world coords: X=right, Y=down, Z=toward camera
                    # We convert to: X=right, Y=up, Z=forward
                    poses_3d[t, coco_idx, 0] = lm.x       # X stays
                    poses_3d[t, coco_idx, 1] = -lm.y       # Y flip (down→up)
                    poses_3d[t, coco_idx, 2] = -lm.z       # Z flip (toward→away)
                    confidences[t, coco_idx] = lm.visibility

            if results.pose_landmarks is not None:
                lms = results.pose_landmarks.landmark
                for coco_idx, mp_idx in MP33_TO_COCO17.items():
                    lm = lms[mp_idx]
                    poses_2d[t, coco_idx, 0] = lm.x * W
                    poses_2d[t, coco_idx, 1] = lm.y * H

            if (t + 1) % 20 == 0 or t == total_frames - 1:
                detected = int(np.sum(~np.isnan(poses_3d[t, :, 0])))
                logger.info(f"Frame {t+1}/{total_frames} — {detected}/17 joints")

    cap.release()

    # Summary
    nan_pct = 100 * np.sum(np.isnan(poses_3d[:, :, 0])) / (total_frames * 17)
    logger.info(f"Extraction complete. Missing: {nan_pct:.1f}%")
    logger.info(f"Avg confidence: {np.nanmean(confidences):.3f}")

    return poses_3d, poses_2d, confidences, np.array(frames_bgr), fps


def smooth_3d(poses_3d):
    """Apply light smoothing to 3D poses."""
    from scipy.signal import savgol_filter

    T, J, D = poses_3d.shape
    smoothed = poses_3d.copy()

    for j in range(J):
        for d in range(D):
            col = smoothed[:, j, d]
            valid = ~np.isnan(col)
            if np.sum(valid) > 7:
                col[valid] = savgol_filter(col[valid], min(7, np.sum(valid) | 1), 3)
            smoothed[:, j, d] = col

    return smoothed


def generate_debug_video(frames_bgr, poses_2d, poses_3d, confidences, output_path, fps):
    """Generate a debug video: 2D overlay + 3D skeleton side by side."""
    T = len(frames_bgr)
    H, W = frames_bgr[0].shape[:2]

    # Scale frames
    panel_w = 640
    scale = panel_w / W
    panel_h = int(H * scale)
    panel_3d_w = 400
    canvas_w = panel_w + panel_3d_w
    canvas_h = max(panel_h, panel_3d_w)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (canvas_w, canvas_h))

    for t in range(T):
        canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

        # Left panel: 2D overlay
        frame = frames_bgr[t].copy()
        kp = poses_2d[t]
        conf = confidences[t]

        for j1, j2 in SKELETON:
            if conf[j1] > 0.3 and conf[j2] > 0.3:
                pt1 = (int(kp[j1, 0]), int(kp[j1, 1]))
                pt2 = (int(kp[j2, 0]), int(kp[j2, 1]))
                cv2.line(frame, pt1, pt2, (0, 255, 0), 2)

        for j in range(17):
            if conf[j] > 0.3:
                pt = (int(kp[j, 0]), int(kp[j, 1]))
                cv2.circle(frame, pt, 4, (0, 0, 255), -1)

        frame_small = cv2.resize(frame, (panel_w, panel_h))
        canvas[:panel_h, :panel_w] = frame_small

        # Right panel: 3D skeleton (front view)
        p3d = poses_3d[t]
        panel_3d = np.zeros((canvas_h, panel_3d_w, 3), dtype=np.uint8)

        valid = ~np.isnan(p3d[:, 0])
        if np.sum(valid) > 2:
            # Project: X→screen_x, Y→screen_y (already flipped)
            proj_x = p3d[:, 0]
            proj_y = -p3d[:, 1]  # Y flip for screen

            x_min, x_max = np.nanmin(proj_x), np.nanmax(proj_x)
            y_min, y_max = np.nanmin(proj_y), np.nanmax(proj_y)
            x_range = max(x_max - x_min, 0.01)
            y_range = max(y_max - y_min, 0.01)
            s = min((panel_3d_w - 60) / x_range, (canvas_h - 60) / y_range)

            cx, cy = panel_3d_w // 2, canvas_h // 2
            xc, yc = (x_min + x_max) / 2, (y_min + y_max) / 2

            px = ((proj_x - xc) * s + cx).astype(int)
            py = ((proj_y - yc) * s + cy).astype(int)

            for j1, j2 in SKELETON:
                if valid[j1] and valid[j2]:
                    cv2.line(panel_3d, (px[j1], py[j1]), (px[j2], py[j2]), (0, 200, 0), 2)

            for j in range(17):
                if valid[j]:
                    cv2.circle(panel_3d, (px[j], py[j]), 4, (0, 255, 255), -1)
                    cv2.putText(panel_3d, JOINT_NAMES[j], (px[j]+5, py[j]-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.3, (200, 200, 200), 1)

        cv2.putText(panel_3d, "3D World (MediaPipe)", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        canvas[:, panel_w:panel_w + panel_3d_w] = panel_3d

        # Info bar
        cv2.putText(canvas, f"Frame {t+1}/{T}", (10, canvas_h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        writer.write(canvas)

    writer.release()
    logger.info(f"Debug video: {output_path}")


def generate_blender_script(npy_path, character_fbx, output_fbx, fps):
    """Generate a Blender Python script for the retarget."""
    script_path = str(Path(npy_path).parent.parent / "animations" / "retarget_blender.py")
    os.makedirs(os.path.dirname(script_path), exist_ok=True)

    script_path = script_path.replace("\\", "/")
    npy_path = str(npy_path).replace("\\", "/")
    character_fbx = str(character_fbx).replace("\\", "/")
    output_fbx = str(output_fbx).replace("\\", "/")
    
    script = f'''"""
Auto-generated Blender retarget script.
Uses per-frame direct rotation keyframing with proper parent-child processing.
Run: blender --background --python "{script_path}"
"""
import bpy
import sys
import os
import math
import mathutils
from mathutils import Vector, Matrix, Quaternion

# Paths
NPY_PATH = r"{npy_path}"
CHARACTER_FBX = r"{character_fbx}"
OUTPUT_FBX = r"{output_fbx}"
FPS = {fps}

try:
    import numpy as np
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy", "--quiet"])
    import numpy as np

# COCO-17 indices
NOSE = 0; L_EYE = 1; R_EYE = 2; L_EAR = 3; R_EAR = 4
L_SHO = 5; R_SHO = 6; L_ELB = 7; R_ELB = 8; L_WRI = 9; R_WRI = 10
L_HIP = 11; R_HIP = 12; L_KNE = 13; R_KNE = 14; L_ANK = 15; R_ANK = 16

# Bone chain: process in strict parent-first order
# Each entry: (Mixamo suffix, parent_joint_ref, child_joint_ref)
# Removed LeftShoulder/RightShoulder (clavicle bones cause arm fighting)
BONE_CHAIN = [
    # Spine chain (processed first)
    ("Spine",       "pelvis",  "chest"),
    ("Spine1",      "chest",   "neck"),
    ("Spine2",      "chest",   "neck"),
    ("Neck",        "neck",    NOSE),
    ("Head",        NOSE,      "head_top"),
    # Left arm (skip clavicle)
    ("LeftArm",     L_SHO,     L_ELB),
    ("LeftForeArm", L_ELB,     L_WRI),
    ("LeftHand",    L_WRI,     "l_tip"),
    # Right arm (skip clavicle)
    ("RightArm",    R_SHO,     R_ELB),
    ("RightForeArm",R_ELB,     R_WRI),
    ("RightHand",   R_WRI,     "r_tip"),
    # Left leg
    ("LeftUpLeg",   L_HIP,     L_KNE),
    ("LeftLeg",     L_KNE,     L_ANK),
    ("LeftFoot",    L_ANK,     "l_toe"),
    # Right leg
    ("RightUpLeg",  R_HIP,     R_KNE),
    ("RightLeg",    R_KNE,     R_ANK),
    ("RightFoot",   R_ANK,     "r_toe"),
]


def get_pos(data, ref):
    if isinstance(ref, int): return data[ref]
    if ref == "pelvis": return (data[L_HIP] + data[R_HIP]) / 2
    if ref == "neck": return (data[L_SHO] + data[R_SHO]) / 2
    if ref == "chest":
        p = (data[L_HIP] + data[R_HIP]) / 2
        n = (data[L_SHO] + data[R_SHO]) / 2
        return p + (n - p) * 0.5
    if ref == "head_top": return data[NOSE] + np.array([0, 0.15, 0])
    if ref == "l_tip":
        d = data[L_WRI] - data[L_ELB]; n = np.linalg.norm(d)
        return data[L_WRI] + (d / n * 0.1 if n > 1e-6 else np.zeros(3))
    if ref == "r_tip":
        d = data[R_WRI] - data[R_ELB]; n = np.linalg.norm(d)
        return data[R_WRI] + (d / n * 0.1 if n > 1e-6 else np.zeros(3))
    if ref == "l_toe":
        d = data[L_ANK] - data[L_KNE]; n = np.linalg.norm(d)
        return data[L_ANK] + (d / n * 0.1 if n > 1e-6 else np.zeros(3))
    if ref == "r_toe":
        d = data[R_ANK] - data[R_KNE]; n = np.linalg.norm(d)
        return data[R_ANK] + (d / n * 0.1 if n > 1e-6 else np.zeros(3))
    return np.zeros(3)


def to_bl(pos):
    \"\"\"Pipeline (X-right, Y-up, Z-fwd) -> Blender (X-right, Y-fwd, Z-up)\"\"\"
    return Vector((float(pos[0]), float(pos[2]), float(pos[1])))


def detect_prefix(arm):
    for b in arm.data.bones:
        if b.name.endswith(":Hips"): return b.name.replace("Hips", "")
    return "mixamorig:"


# ============ MAIN ============
print("=" * 60)
print("  MediaPipe 3D -> Direct Rotation Retarget (v3)")
print("=" * 60)

poses = np.load(NPY_PATH)
T = poses.shape[0]
print(f"Frames: {{T}}")

# 1. Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# 2. Import character
bpy.ops.import_scene.fbx(filepath=CHARACTER_FBX, use_anim=False, ignore_leaf_bones=True)
armature = next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')
prefix = detect_prefix(armature)
print(f"Prefix: {{prefix}}")

bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = T
bpy.context.scene.render.fps = FPS

# 3. Measure character scale (compare armature height to MediaPipe range)
bpy.context.view_layer.objects.active = armature
bpy.ops.object.mode_set(mode='EDIT')

# Get rest-pose bone directions in armature-local space
rest_info = {{}}
for eb in armature.data.edit_bones:
    short = eb.name.replace(prefix, "")
    rest_info[short] = {{
        "head": eb.head.copy(),
        "tail": eb.tail.copy(),
        "matrix": eb.matrix.copy(),  # 4x4 bone matrix in armature space
        "length": eb.length,
    }}

# Measure character height from Hips to Head
char_height = 1.0
if "Hips" in rest_info and "Head" in rest_info:
    char_height = (rest_info["Head"]["head"] - rest_info["Hips"]["head"]).length
    if char_height < 0.01: char_height = 1.0

# Measure MediaPipe pose height from first valid frame
mp_height = 1.0
for t in range(T):
    fd = poses[t]
    pelvis = get_pos(fd, "pelvis")
    head = fd[NOSE]
    if not (np.isnan(pelvis).any() or np.isnan(head).any()):
        h = np.linalg.norm(head - pelvis)
        if h > 0.01:
            mp_height = h
            break

scale_factor = char_height / mp_height
print(f"Character height: {{char_height:.3f}}, MediaPipe height: {{mp_height:.3f}}, Scale: {{scale_factor:.3f}}")

bpy.ops.object.mode_set(mode='POSE')

# Set all bones to quaternion rotation mode
for pb in armature.pose.bones:
    pb.rotation_mode = 'QUATERNION'

# 4. Animate frame by frame
print("Animating...")

for t in range(T):
    frame = t + 1
    bpy.context.scene.frame_set(frame)
    fd = poses[t]

    # Skip frames with too many NaN joints
    valid_count = np.sum(~np.isnan(fd[:, 0]))
    if valid_count < 10:
        continue

    # --- HIPS: Position + Rotation ---
    hips_name = prefix + "Hips"
    if hips_name in armature.pose.bones:
        pb_hips = armature.pose.bones[hips_name]

        # Position (scaled)
        pelvis = get_pos(fd, "pelvis")
        pb_hips.location = to_bl(pelvis) * scale_factor
        pb_hips.keyframe_insert("location", frame=frame)

        # Rotation: build orientation from hip-hip and spine vectors
        l_hip = to_bl(fd[L_HIP])
        r_hip = to_bl(fd[R_HIP])
        neck = to_bl(get_pos(fd, "neck"))
        pelvis_bl = to_bl(pelvis)

        spine_dir = (neck - pelvis_bl)
        if spine_dir.length > 1e-6:
            spine_dir.normalize()
        else:
            spine_dir = Vector((0, 0, 1))

        hip_vec = (r_hip - l_hip)
        if hip_vec.length > 1e-6:
            hip_vec.normalize()
        else:
            hip_vec = Vector((1, 0, 0))

        # Forward = cross(spine, hip_vec)
        fwd = spine_dir.cross(hip_vec)
        if fwd.length > 1e-6:
            fwd.normalize()
        else:
            fwd = Vector((0, 1, 0))

        # Rebuild orthogonal basis
        right = fwd.cross(spine_dir).normalized()

        # Build world rotation matrix (columns = right, fwd, up)
        target_mat = Matrix((right, fwd, spine_dir)).transposed().to_3x3()
        target_quat = target_mat.to_quaternion()

        # Get rest pose world rotation of Hips
        if "Hips" in rest_info:
            rest_mat = rest_info["Hips"]["matrix"].to_3x3()
            rest_quat = rest_mat.to_quaternion()
            # Delta from rest to target
            delta = rest_quat.inverted() @ target_quat
            pb_hips.rotation_quaternion = delta
        else:
            pb_hips.rotation_quaternion = target_quat

        pb_hips.keyframe_insert("rotation_quaternion", frame=frame)

    # --- OTHER BONES: Direction-based rotation ---
    # Update the scene so parent matrices are current
    bpy.context.view_layer.update()

    for short_name, parent_ref, child_ref in BONE_CHAIN:
        bone_name = prefix + short_name
        if bone_name not in armature.pose.bones: continue
        if short_name not in rest_info: continue

        pb = armature.pose.bones[bone_name]
        rest = rest_info[short_name]

        # Get target direction in Blender world space
        p_pos = to_bl(get_pos(fd, parent_ref))
        c_pos = to_bl(get_pos(fd, child_ref))
        target_dir = c_pos - p_pos

        if target_dir.length < 1e-6:
            continue

        target_dir.normalize()

        # Rest bone direction in armature space (head->tail)
        rest_dir = (rest["tail"] - rest["head"]).normalized()

        # Compute world-space rotation to go from rest_dir to target_dir
        world_rot = rest_dir.rotation_difference(target_dir)

        # Convert to bone-local space using the bone's rest matrix
        # and the parent's current evaluated matrix
        rest_mat = rest["matrix"].to_3x3().to_quaternion()

        if pb.parent:
            # Get parent's current world-space rotation (after our keyframes)
            parent_world = pb.parent.matrix.to_quaternion()
            # local_rot = inverse(parent_world) * world_rot * rest_quat_correction
            local_rot = parent_world.inverted() @ world_rot @ rest_mat
            # Remove rest pose contribution
            local_rot = rest_mat.inverted() @ parent_world.inverted() @ world_rot @ rest_mat
        else:
            local_rot = rest_mat.inverted() @ world_rot @ rest_mat

        pb.rotation_quaternion = local_rot
        pb.keyframe_insert("rotation_quaternion", frame=frame)

    # Update every frame so child bones see parent rotations
    bpy.context.view_layer.update()

    if frame % 10 == 0 or frame == 1 or frame == T:
        print(f"  Frame {{frame}}/{{T}}")

bpy.ops.object.mode_set(mode='OBJECT')

# 5. Select Armature + Mesh for Export
bpy.ops.object.select_all(action='DESELECT')
armature.select_set(True)
for child in armature.children:
    child.select_set(True)
bpy.context.view_layer.objects.active = armature

os.makedirs(os.path.dirname(OUTPUT_FBX), exist_ok=True)
bpy.ops.export_scene.fbx(
    filepath=OUTPUT_FBX,
    use_selection=True,
    use_armature_deform_only=True,
    add_leaf_bones=False,
    bake_anim=True,
    bake_anim_use_all_bones=True,
    bake_anim_force_startend_keying=True,
    path_mode='COPY',
    embed_textures=True,
    axis_forward='-Z',
    axis_up='Y',
)

print(f"DONE! Saved to {{OUTPUT_FBX}}")
'''

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    logger.info(f"Blender script: {script_path}")
    return script_path


def main():
    parser = argparse.ArgumentParser(description="Extract MediaPipe 3D + Generate Blender Script")
    parser.add_argument("--technique", required=True, choices=["Bonus", "HandTouch"])
    parser.add_argument("--player", required=True)
    parser.add_argument("--debug-frames", type=int, default=None)
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    # Resolve video path
    prefix_map = {"Bonus": "bonus", "HandTouch": "hand"}
    prefix = prefix_map.get(args.technique, args.technique.lower())
    video_path = str(
        project_root / "samples" / "3D" / "Techniques" / args.technique / args.player / f"{prefix}_front.mp4"
    )

    output_base = project_root / "outputs" / f"{args.technique}_{args.player}"
    pose_dir = output_base / "pose_3d"
    debug_dir = output_base / "debug"
    anim_dir = output_base / "animations"

    for d in [pose_dir, debug_dir, anim_dir]:
        d.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("MediaPipe NATIVE 3D Extraction")
    logger.info("=" * 60)
    logger.info(f"Video: {video_path}")

    # Extract
    poses_3d, poses_2d, confs, frames, fps = extract_mediapipe_3d(
        video_path, max_frames=args.debug_frames
    )

    # Smooth
    poses_3d_smooth = smooth_3d(poses_3d)

    # Save
    npy_path = str(pose_dir / "pose_3d_mediapipe.npy")
    np.save(npy_path, poses_3d_smooth)
    np.save(str(pose_dir / "pose_3d_mediapipe_raw.npy"), poses_3d)
    logger.info(f"Saved: {npy_path} — shape {poses_3d_smooth.shape}")

    # 3D coordinate ranges
    logger.info("3D ranges (meters):")
    for i, ax in enumerate(["X", "Y", "Z"]):
        vals = poses_3d_smooth[:, :, i]
        logger.info(f"  {ax}: [{np.nanmin(vals):.3f}, {np.nanmax(vals):.3f}]")

    # Debug video
    debug_path = str(debug_dir / "debug_mediapipe_3d.mp4")
    generate_debug_video(frames, poses_2d, poses_3d_smooth, confs, debug_path, fps)

    # Generate Blender script
    character_fbx = str(project_root / "Assets" / "character.fbx")
    output_fbx = str(anim_dir / "kabaddi_ghost.fbx")
    script_path = generate_blender_script(npy_path, character_fbx, output_fbx, int(fps))

    logger.info("")
    logger.info("=" * 60)
    logger.info("NEXT STEP — Run in Blender:")
    logger.info(f'  blender --background --python "{script_path}"')
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
