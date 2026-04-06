"""
Automated BVH → Character → FBX Retargeting Script for Blender

This script does EVERYTHING automatically:
  1. Imports your BVH animation
  2. Imports a Mixamo character (FBX)
  3. Maps all 15 bones with constraints
  4. Bakes the animation onto the character
  5. Exports a Unity-ready FBX

=== HOW TO USE ===

Option A — From Blender GUI:
  1. Open Blender
  2. Go to: Scripting tab (top menu bar)
  3. Click "Open" → select this file
  4. Edit the 3 paths at the top of CONFIGURATION section below
  5. Click "Run Script" (▶ button)

Option B — From command line:
  blender --background --python auto_retarget.py

=== REQUIREMENTS ===
  - Blender 3.0+ 
  - A Mixamo character FBX (download from mixamo.com, no animation)
  - Your animation.bvh from the pipeline
"""

import bpy
import os
import sys
import math

# =====================================================================
# CONFIGURATION — EDIT THESE 3 PATHS
# =====================================================================

BVH_PATH = r"C:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer\outputs\Bonus_Player-1\animations\animation.bvh"
CHARACTER_FBX_PATH = r"C:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer\Assets\character.fbx"  # Your Mixamo character
OUTPUT_FBX_PATH = r"C:\Users\msibr\Documents\MCA\SEM 4\Project\kabaddi_trainer\outputs\Bonus_Player-1\animations\kabaddi_ghost.fbx"

# =====================================================================
# BONE MAPPING: BVH joint name → Mixamo bone SUFFIX (without prefix)
# The prefix (mixamorig:, mixamorig5:, etc.) is auto-detected.
# =====================================================================

BONE_MAP_BASE = {
    "Pelvis":        "Hips",
    "Spine":         "Spine",
    "Head":          "Head",
    "LeftShoulder":  "LeftArm",
    "LeftElbow":     "LeftForeArm",
    "LeftWrist":     "LeftHand",
    "RightShoulder": "RightArm",
    "RightElbow":    "RightForeArm",
    "RightWrist":    "RightHand",
    "LeftHip":       "LeftUpLeg",
    "LeftKnee":      "LeftLeg",
    "LeftAnkle":     "LeftFoot",
    "RightHip":      "RightUpLeg",
    "RightKnee":     "RightLeg",
    "RightAnkle":    "RightFoot",
}


def detect_mixamo_prefix(armature):
    """Auto-detect the Mixamo bone prefix (e.g., 'mixamorig:', 'mixamorig5:')."""
    for bone in armature.data.bones:
        name = bone.name
        # Look for the Hips bone — it always exists in Mixamo rigs
        if name.endswith(":Hips"):
            prefix = name.replace("Hips", "")
            print(f"   Auto-detected Mixamo prefix: '{prefix}'")
            return prefix
    
    # Fallback: try to find any bone with a colon
    for bone in armature.data.bones:
        if ":" in bone.name:
            prefix = bone.name.split(":")[0] + ":"
            print(f"   Auto-detected prefix from '{bone.name}': '{prefix}'")
            return prefix
    
    print("   WARNING: Could not detect Mixamo prefix, trying 'mixamorig:'")
    return "mixamorig:"


def build_bone_map(armature):
    """Build the full bone map with the correct prefix for this character."""
    prefix = detect_mixamo_prefix(armature)
    bone_map = {}
    for bvh_name, base_name in BONE_MAP_BASE.items():
        bone_map[bvh_name] = prefix + base_name
    return bone_map

# =====================================================================
# SCRIPT — DO NOT EDIT BELOW THIS LINE
# =====================================================================


def clear_scene():
    """Remove all objects from the scene."""
    print("[1/6] Clearing scene...")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Also clear orphan data
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.armatures:
        if block.users == 0:
            bpy.data.armatures.remove(block)
    print("   Scene cleared.")


def import_bvh(bvh_path):
    """Import BVH file and return the armature object."""
    print(f"[2/6] Importing BVH: {bvh_path}")
    
    if not os.path.isfile(bvh_path):
        print(f"   ERROR: BVH file not found: {bvh_path}")
        sys.exit(1)
    
    bpy.ops.import_anim.bvh(
        filepath=bvh_path,
        filter_glob="*.bvh",
        target='ARMATURE',
        global_scale=1.0,
        frame_start=1,
        use_fps_scale=False,
        use_cyclic=False,
        rotate_mode='NATIVE',
    )
    
    # Find the imported armature
    bvh_armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            bvh_armature = obj
            break
    
    if bvh_armature is None:
        print("   ERROR: No armature found after BVH import!")
        sys.exit(1)
    
    # Rename for clarity
    bvh_armature.name = "BVH_Armature"
    
    # Print bone names for debugging
    print(f"   Imported BVH armature: {bvh_armature.name}")
    print(f"   Bones ({len(bvh_armature.data.bones)}):")
    for bone in bvh_armature.data.bones:
        print(f"      - {bone.name}")
    
    # Get frame range
    frame_end = int(bpy.context.scene.frame_end)
    print(f"   Animation frames: 1 to {frame_end}")
    
    return bvh_armature, frame_end


def import_character(fbx_path):
    """Import Mixamo character FBX and return the armature object."""
    print(f"[3/6] Importing character: {fbx_path}")
    
    if not os.path.isfile(fbx_path):
        print(f"   ERROR: Character FBX not found: {fbx_path}")
        print(f"   Download a character from mixamo.com (FBX, no animation)")
        sys.exit(1)
    
    bpy.ops.import_scene.fbx(
        filepath=fbx_path,
        use_anim=False,
        ignore_leaf_bones=True,
    )
    
    # Find the character armature (not the BVH one)
    char_armature = None
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj.name != "BVH_Armature":
            char_armature = obj
            break
    
    if char_armature is None:
        print("   ERROR: No character armature found after FBX import!")
        sys.exit(1)
    
    char_armature.name = "Character_Armature"
    
    print(f"   Imported character: {char_armature.name}")
    print(f"   Bones ({len(char_armature.data.bones)}):")
    for bone in char_armature.data.bones:
        print(f"      - {bone.name}")
    
    return char_armature


def setup_constraints(bvh_armature, char_armature, bone_map):
    """Add Copy Rotation/Location constraints to map BVH to character bones."""
    print("[4/6] Setting up bone constraints...")
    
    # Switch to pose mode on character
    bpy.context.view_layer.objects.active = char_armature
    bpy.ops.object.mode_set(mode='POSE')
    
    mapped = 0
    skipped = 0
    
    for bvh_bone_name, mixamo_bone_name in bone_map.items():
        # Check if both bones exist
        if bvh_bone_name not in bvh_armature.data.bones:
            print(f"   SKIP: BVH bone '{bvh_bone_name}' not found")
            skipped += 1
            continue
        
        if mixamo_bone_name not in char_armature.data.bones:
            print(f"   SKIP: Character bone '{mixamo_bone_name}' not found")
            skipped += 1
            continue
        
        pose_bone = char_armature.pose.bones[mixamo_bone_name]
        
        # Add Copy Rotation constraint
        rot_constraint = pose_bone.constraints.new('COPY_ROTATION')
        rot_constraint.name = f"BVH_Rot_{bvh_bone_name}"
        rot_constraint.target = bvh_armature
        rot_constraint.subtarget = bvh_bone_name
        rot_constraint.mix_mode = 'REPLACE'
        rot_constraint.target_space = 'LOCAL'
        rot_constraint.owner_space = 'LOCAL'
        
        # For the root (Pelvis/Hips), also copy location
        if bvh_bone_name == "Pelvis":
            loc_constraint = pose_bone.constraints.new('COPY_LOCATION')
            loc_constraint.name = f"BVH_Loc_{bvh_bone_name}"
            loc_constraint.target = bvh_armature
            loc_constraint.subtarget = bvh_bone_name
            loc_constraint.target_space = 'LOCAL'
            loc_constraint.owner_space = 'LOCAL'
            print(f"   ✓ {bvh_bone_name} → {mixamo_bone_name} (rotation + location)")
        else:
            print(f"   ✓ {bvh_bone_name} → {mixamo_bone_name} (rotation)")
        
        mapped += 1
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"   Mapped: {mapped}, Skipped: {skipped}")
    
    if mapped == 0:
        print("   ERROR: No bones were mapped! Check bone names.")
        sys.exit(1)
    
    return mapped


def bake_animation(char_armature, frame_end):
    """Bake the constrained animation onto the character."""
    print(f"[5/6] Baking animation (frames 1-{frame_end})...")
    
    bpy.context.view_layer.objects.active = char_armature
    char_armature.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    
    # Select all pose bones
    bpy.ops.pose.select_all(action='SELECT')
    
    # Bake
    bpy.ops.nla.bake(
        frame_start=1,
        frame_end=frame_end,
        only_selected=False,
        visual_keying=True,
        clear_constraints=True,
        use_current_action=True,
        bake_types={'POSE'},
    )
    
    bpy.ops.object.mode_set(mode='OBJECT')
    print("   Animation baked successfully.")


def export_fbx(output_path, char_armature, bvh_armature):
    """Delete BVH armature and export character as FBX."""
    print(f"[6/6] Exporting FBX: {output_path}")
    
    # Delete BVH armature (deselect everything first!)
    bpy.ops.object.select_all(action='DESELECT')
    bvh_armature.select_set(True)
    bpy.context.view_layer.objects.active = bvh_armature
    bpy.ops.object.delete(use_global=False)
    print("   Deleted BVH armature.")
    
    # Select character and all its children (mesh, etc.)
    bpy.ops.object.select_all(action='DESELECT')
    char_armature.select_set(True)
    for child in char_armature.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = char_armature
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Export
    bpy.ops.export_scene.fbx(
        filepath=output_path,
        use_selection=True,
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
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"   FBX exported: {output_path} ({size_mb:.1f} MB)")
    else:
        print(f"   ERROR: FBX was not created!")


def main():
    print("=" * 60)
    print("  AUTOMATED BVH → CHARACTER → FBX RETARGETING")
    print("=" * 60)
    print()
    
    # Step 1: Clear scene
    clear_scene()
    
    # Step 2: Import BVH
    bvh_armature, frame_end = import_bvh(BVH_PATH)
    
    # Step 3: Import character
    char_armature = import_character(CHARACTER_FBX_PATH)
    
    # Step 4: Setup constraints (auto-detects Mixamo prefix)
    bone_map = build_bone_map(char_armature)
    mapped = setup_constraints(bvh_armature, char_armature, bone_map)
    
    # Step 5: Bake animation
    bake_animation(char_armature, frame_end)
    
    # Step 6: Export FBX
    export_fbx(OUTPUT_FBX_PATH, char_armature, bvh_armature)
    
    print()
    print("=" * 60)
    print("  DONE! Your FBX is ready for Unity.")
    print(f"  Output: {OUTPUT_FBX_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
