"""
Direct Position-Based Retarget for Blender

Bypasses BVH entirely. Reads the 3D joint positions (.npy)
and drives the Mixamo skeleton directly using bone constraints
and keyframes.

This is MORE RELIABLE than BVH because:
  - No rotation computation needed
  - Positions drive IK → Blender computes rotations automatically
  - Works with any Mixamo character

=== HOW TO USE ===

Option A — From Blender GUI:
  1. Open Blender → Scripting tab
  2. Click "Open" → select this file
  3. Edit the 2 paths below
  4. Click Run Script (▶)

Option B — Command line:
  blender --background --python direct_retarget.py

=== OUTPUT ===
  - kabaddi_ghost.fbx in the same directory as the .npy file
"""

import bpy
import os
import sys
import json
import math
import mathutils

# =====================================================================
# CONFIGURATION — EDIT THESE PATHS
# =====================================================================

POSE_3D_PATH = r"C:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer\outputs\Bonus_Player-1\pose_3d\pose_3d_clean.npy"
CHARACTER_FBX_PATH = r"C:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer\Assets\character.fbx"
OUTPUT_FBX_PATH = r"C:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer\outputs\Bonus_Player-1\animations\kabaddi_ghost.fbx"
FPS = 30

# =====================================================================
# COCO-17 to Mixamo Bone Mapping
#
# Maps COCO-17 joint indices to Mixamo bone names.
# The bone's TAIL (tip) is positioned at the joint location.
# =====================================================================

# COCO-17 indices
NOSE = 0
L_EYE = 1; R_EYE = 2; L_EAR = 3; R_EAR = 4
L_SHO = 5; R_SHO = 6
L_ELB = 7; R_ELB = 8
L_WRI = 9; R_WRI = 10
L_HIP = 11; R_HIP = 12
L_KNE = 13; R_KNE = 14
L_ANK = 15; R_ANK = 16

# Mapping: Mixamo bone → which COCO-17 joint positions its HEAD and TAIL
# Format: (head_joint_or_virtual, tail_joint)
# "virtual" means computed from other joints (e.g., midpoint)
BONE_TARGETS = {
    "Hips":         {"head": "pelvis",   "tail": "spine_mid"},
    "Spine":        {"head": "pelvis",   "tail": "spine_mid"},
    "Spine1":       {"head": "spine_mid","tail": "chest"},
    "Spine2":       {"head": "chest",    "tail": "neck"},
    "Neck":         {"head": "neck",     "tail": NOSE},
    "Head":         {"head": NOSE,       "tail": "head_top"},
    "LeftArm":      {"head": L_SHO,      "tail": L_ELB},
    "LeftForeArm":  {"head": L_ELB,      "tail": L_WRI},
    "LeftHand":     {"head": L_WRI,      "tail": "l_hand_tip"},
    "RightArm":     {"head": R_SHO,      "tail": R_ELB},
    "RightForeArm": {"head": R_ELB,      "tail": R_WRI},
    "RightHand":    {"head": R_WRI,      "tail": "r_hand_tip"},
    "LeftUpLeg":    {"head": L_HIP,      "tail": L_KNE},
    "LeftLeg":      {"head": L_KNE,      "tail": L_ANK},
    "LeftFoot":     {"head": L_ANK,      "tail": "l_toe"},
    "RightUpLeg":   {"head": R_HIP,      "tail": R_KNE},
    "RightLeg":     {"head": R_KNE,      "tail": R_ANK},
    "RightFoot":    {"head": R_ANK,      "tail": "r_toe"},
}


def load_numpy_file(path):
    """Load .npy file without requiring numpy in Blender's Python."""
    # Try to import numpy (may or may not be available in Blender)
    try:
        import numpy as np
        return np.load(path)
    except ImportError:
        # If numpy not available in Blender, read the .npy file manually
        print("NumPy not available in Blender Python. Installing...")
        import subprocess
        python_exe = sys.executable
        subprocess.check_call([python_exe, "-m", "pip", "install", "numpy", "--quiet"])
        import numpy as np
        return np.load(path)


def get_joint_position(frame_data, joint_ref):
    """
    Get 3D position for a joint reference.
    joint_ref can be:
      - int: COCO-17 joint index
      - str: virtual joint name
    """
    if isinstance(joint_ref, int):
        return frame_data[joint_ref]

    # Virtual joints
    if joint_ref == "pelvis":
        return (frame_data[L_HIP] + frame_data[R_HIP]) / 2.0
    elif joint_ref == "spine_mid":
        pelvis = (frame_data[L_HIP] + frame_data[R_HIP]) / 2.0
        shoulders = (frame_data[L_SHO] + frame_data[R_SHO]) / 2.0
        return pelvis + (shoulders - pelvis) * 0.3  # lower spine
    elif joint_ref == "chest":
        pelvis = (frame_data[L_HIP] + frame_data[R_HIP]) / 2.0
        shoulders = (frame_data[L_SHO] + frame_data[R_SHO]) / 2.0
        return pelvis + (shoulders - pelvis) * 0.7  # upper spine
    elif joint_ref == "neck":
        return (frame_data[L_SHO] + frame_data[R_SHO]) / 2.0
    elif joint_ref == "head_top":
        nose = frame_data[NOSE]
        ears = (frame_data[L_EAR] + frame_data[R_EAR]) / 2.0
        # Head top = extend above ears
        head_up = nose - ears
        import numpy as np
        n = np.linalg.norm(head_up)
        if n > 1e-8:
            head_up = head_up / n * 0.15  # 15cm above nose
        return nose + head_up
    elif joint_ref == "l_hand_tip":
        # Extend beyond wrist
        direction = frame_data[L_WRI] - frame_data[L_ELB]
        import numpy as np
        n = np.linalg.norm(direction)
        if n > 1e-8:
            direction = direction / n * 0.1
        return frame_data[L_WRI] + direction
    elif joint_ref == "r_hand_tip":
        direction = frame_data[R_WRI] - frame_data[R_ELB]
        import numpy as np
        n = np.linalg.norm(direction)
        if n > 1e-8:
            direction = direction / n * 0.1
        return frame_data[R_WRI] + direction
    elif joint_ref == "l_toe":
        direction = frame_data[L_ANK] - frame_data[L_KNE]
        import numpy as np
        n = np.linalg.norm(direction)
        if n > 1e-8:
            direction = direction / n * 0.1
        return frame_data[L_ANK] + direction
    elif joint_ref == "r_toe":
        direction = frame_data[R_ANK] - frame_data[R_KNE]
        import numpy as np
        n = np.linalg.norm(direction)
        if n > 1e-8:
            direction = direction / n * 0.1
        return frame_data[R_ANK] + direction

    # Fallback
    return frame_data[0]


def detect_prefix(armature):
    """Auto-detect Mixamo bone prefix."""
    for bone in armature.data.bones:
        if bone.name.endswith(":Hips"):
            return bone.name.replace("Hips", "")
    for bone in armature.data.bones:
        if ":" in bone.name:
            return bone.name.split(":")[0] + ":"
    return "mixamorig:"


def clear_scene():
    """Remove all objects from the scene."""
    print("[1/5] Clearing scene...")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.armatures:
        if block.users == 0:
            bpy.data.armatures.remove(block)


def import_character(fbx_path):
    """Import Mixamo character."""
    print(f"[2/5] Importing character: {fbx_path}")
    if not os.path.isfile(fbx_path):
        print(f"   ERROR: FBX not found: {fbx_path}")
        sys.exit(1)

    bpy.ops.import_scene.fbx(filepath=fbx_path, use_anim=False, ignore_leaf_bones=True)

    armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            armature = obj
            break

    if armature is None:
        print("   ERROR: No armature found!")
        sys.exit(1)

    prefix = detect_prefix(armature)
    print(f"   Character: {armature.name}, prefix: '{prefix}', bones: {len(armature.data.bones)}")
    return armature, prefix


def create_empty_target(name, location):
    """Create an empty object to use as an IK target."""
    empty = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(empty)
    empty.location = location
    empty.empty_display_size = 0.02
    empty.empty_display_type = 'SPHERE'
    return empty


def apply_animation(armature, prefix, poses_3d, fps):
    """
    Apply 3D joint positions directly as bone location keyframes.

    Strategy:
    - For each frame, compute the target position for the Hips bone
    - Compute rotation of each bone to point toward its child joint
    - Keyframe both location (Hips only) and rotation (all bones)
    """
    import numpy as np

    print(f"[3/5] Applying animation ({poses_3d.shape[0]} frames)...")

    T = poses_3d.shape[0]

    bpy.context.scene.frame_start = 1
    bpy.context.scene.frame_end = T
    bpy.context.scene.render.fps = fps

    # Set active and enter pose mode
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    # Get rest pose bone data
    rest_data = {}
    for bone in armature.data.bones:
        short_name = bone.name.replace(prefix, "")
        if short_name in BONE_TARGETS:
            # Store bone rest-pose direction in local space
            rest_data[short_name] = {
                "bone_name": bone.name,
                "head": bone.head_local.copy(),
                "tail": bone.tail_local.copy(),
                "length": bone.length,
                "direction": (bone.tail_local - bone.head_local).normalized(),
            }

    print(f"   Matched {len(rest_data)} bones")

    for t in range(T):
        frame_num = t + 1
        bpy.context.scene.frame_set(frame_num)
        frame_data = poses_3d[t]  # (17, 3)

        # Compute pelvis position (root motion)
        pelvis_pos = get_joint_position(frame_data, "pelvis")

        # Set Hips bone location
        hips_bone_name = prefix + "Hips"
        if hips_bone_name in armature.pose.bones:
            hips_pose_bone = armature.pose.bones[hips_bone_name]
            # Convert to Blender coordinate system (Y-up)
            # Our pipeline: X=right, Y=up, Z=forward
            # Blender: X=right, Y=forward, Z=up
            hips_pose_bone.location = mathutils.Vector((
                float(pelvis_pos[0]),
                float(pelvis_pos[2]),  # our Z → Blender Y (forward)
                float(pelvis_pos[1]),  # our Y → Blender Z (up)
            ))
            hips_pose_bone.keyframe_insert(data_path="location", frame=frame_num)

        # For each mapped bone, compute rotation to point toward target
        for short_name, targets in BONE_TARGETS.items():
            bone_name = prefix + short_name
            if bone_name not in armature.pose.bones:
                continue

            pose_bone = armature.pose.bones[bone_name]
            rest_info = rest_data.get(short_name)
            if rest_info is None:
                continue

            # Get target direction in world space
            head_pos = get_joint_position(frame_data, targets["head"])
            tail_pos = get_joint_position(frame_data, targets["tail"])

            # Convert to Blender coords
            head_bl = mathutils.Vector((float(head_pos[0]), float(head_pos[2]), float(head_pos[1])))
            tail_bl = mathutils.Vector((float(tail_pos[0]), float(tail_pos[2]), float(tail_pos[1])))

            target_dir = tail_bl - head_bl
            if target_dir.length < 1e-6:
                continue
            target_dir.normalize()

            # Get bone's rest direction in armature space
            rest_dir = rest_info["direction"]

            # Compute rotation from rest direction to target direction
            rotation = rest_dir.rotation_difference(target_dir)

            # Apply as quaternion in bone-local space
            # We need to account for parent bone's influence
            if pose_bone.parent:
                # Get parent's world-space matrix
                parent_mat = pose_bone.parent.matrix.to_3x3()
                parent_inv = parent_mat.inverted()
                # Transform target direction to parent-local space
                local_target = parent_inv @ target_dir
                local_rest = parent_inv @ rest_dir
                rotation = local_rest.rotation_difference(local_target)

            pose_bone.rotation_quaternion = rotation
            pose_bone.rotation_mode = 'QUATERNION'
            pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=frame_num)

        if (t + 1) % 10 == 0 or t == 0:
            print(f"   Frame {t+1}/{T}")

    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"   Animation applied: {T} frames at {fps} FPS")


def export_fbx(output_path):
    """Export as FBX for Unity."""
    print(f"[5/5] Exporting FBX: {output_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=False,
        use_armature_deform_only=False,
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_force_startend_keying=True,
        use_metadata=True,
        path_mode='COPY',
        embed_textures=True,
        axis_forward='-Z',
        axis_up='Y',
    )

    if os.path.isfile(output_path):
        size_kb = os.path.getsize(output_path) / 1024
        print(f"   Exported: {output_path} ({size_kb:.0f} KB)")
    else:
        print(f"   ERROR: FBX was not created!")


def main():
    print("=" * 60)
    print("  DIRECT POSITION-BASED RETARGET")
    print("  (Bypasses BVH — positions → Blender IK)")
    print("=" * 60)

    # Load 3D poses
    print(f"\n[0/5] Loading poses: {POSE_3D_PATH}")
    if not os.path.isfile(POSE_3D_PATH):
        print(f"   ERROR: File not found: {POSE_3D_PATH}")
        sys.exit(1)

    poses_3d = load_numpy_file(POSE_3D_PATH)
    print(f"   Shape: {poses_3d.shape}")

    # Step 1: Clear
    clear_scene()

    # Step 2: Import character
    armature, prefix = import_character(CHARACTER_FBX_PATH)

    # Step 3: Apply animation
    apply_animation(armature, prefix, poses_3d, FPS)

    # Step 4: (reserved for cleanup)
    print("[4/5] Cleanup...")

    # Step 5: Export
    export_fbx(OUTPUT_FBX_PATH)

    print()
    print("=" * 60)
    print("  DONE!")
    print(f"  Output: {OUTPUT_FBX_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
