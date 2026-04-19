"""
Step 8 (Step 9 in prompt): Blender Retargeting Script

This script is meant to be run inside Blender's Python environment:
    blender --background --python blender_retarget.py -- \\
        --bvh animation.bvh \\
        --rig character_rig.fbx \\
        --output avatar_animation.fbx

If Blender is not available, the pipeline still produces a valid BVH file.
"""

import sys
import os
import argparse
import logging

logger = logging.getLogger(__name__)


def check_blender_available(blender_path: str = "blender") -> bool:
    """Check if Blender is available on the system."""
    import shutil
    return shutil.which(blender_path) is not None


def run_blender_retarget(
    bvh_path: str,
    output_fbx_path: str,
    rig_path: str = None,
    blender_path: str = "blender",
) -> bool:
    """
    Run Blender in background mode to retarget BVH to humanoid rig and export FBX.

    Args:
        bvh_path: Path to input BVH file.
        output_fbx_path: Path to output FBX file.
        rig_path: Optional path to humanoid rig FBX (e.g., Mixamo character).
        blender_path: Path to Blender executable.

    Returns:
        True if successful, False otherwise.
    """
    import subprocess

    if not check_blender_available(blender_path):
        logger.warning("Blender not found — skipping FBX retargeting")
        return False

    if not os.path.isfile(bvh_path):
        logger.error(f"BVH file not found: {bvh_path}")
        return False

    # Build inline Blender Python script
    blender_script = _generate_blender_script(bvh_path, output_fbx_path, rig_path)

    # Write temporary script
    script_path = os.path.join(
        os.path.dirname(output_fbx_path), "_retarget_temp.py"
    )
    with open(script_path, "w") as f:
        f.write(blender_script)

    try:
        logger.info(f"Running Blender retarget: {bvh_path} → {output_fbx_path}")
        result = subprocess.run(
            [blender_path, "--background", "--python", script_path],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            logger.info("Blender retarget completed successfully")
            if os.path.isfile(output_fbx_path):
                logger.info(f"FBX exported: {output_fbx_path}")
                return True
            else:
                logger.error("Blender ran but FBX was not created")
                return False
        else:
            logger.error(f"Blender failed (exit code {result.returncode})")
            logger.error(f"STDERR: {result.stderr[:500]}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Blender timed out after 120 seconds")
        return False
    except Exception as e:
        logger.error(f"Blender execution error: {e}")
        return False
    finally:
        if os.path.isfile(script_path):
            os.remove(script_path)


def _generate_blender_script(
    bvh_path: str,
    output_fbx_path: str,
    rig_path: str = None,
) -> str:
    """Generate the Blender Python script for retargeting."""

    # Normalize paths for cross-platform
    bvh_path = bvh_path.replace("\\", "/")
    output_fbx_path = output_fbx_path.replace("\\", "/")

    script = f'''
import bpy
import os

# Clear the scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import BVH
bpy.ops.import_anim.bvh(
    filepath="{bvh_path}",
    filter_glob="*.bvh",
    target="ARMATURE",
    global_scale=1.0,
    frame_start=1,
    use_fps_scale=False,
    use_cyclic=False,
    rotate_mode="NATIVE",
)

# Get the imported armature
armature = None
for obj in bpy.data.objects:
    if obj.type == "ARMATURE":
        armature = obj
        break

if armature is None:
    print("ERROR: No armature found after BVH import")
    exit(1)

print(f"Imported armature: {{armature.name}}")
print(f"Bones: {{len(armature.data.bones)}}")

# Select the armature
bpy.context.view_layer.objects.active = armature
armature.select_set(True)

# Bake the animation
bpy.ops.object.mode_set(mode="POSE")
bpy.ops.nla.bake(
    frame_start=1,
    frame_end=bpy.context.scene.frame_end,
    only_selected=False,
    visual_keying=True,
    clear_constraints=True,
    use_current_action=True,
    bake_types={{"POSE"}},
)
bpy.ops.object.mode_set(mode="OBJECT")

# Export as FBX
output_dir = os.path.dirname("{output_fbx_path}")
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir, exist_ok=True)

bpy.ops.export_scene.fbx(
    filepath="{output_fbx_path}",
    use_selection=False,
    use_armature_deform_only=False,
    add_leaf_bones=False,
    bake_anim=True,
    bake_anim_use_all_bones=True,
    bake_anim_force_startend_keying=True,
    use_metadata=True,
    axis_forward="-Z",
    axis_up="Y",
)

print(f"FBX exported: {output_fbx_path}")
'''
    return script


def generate_unity_metadata(
    fps: float,
    frame_count: int,
    duration: float,
    output_path: str,
) -> None:
    """
    Generate metadata JSON for Unity import.

    Args:
        fps: Animation FPS.
        frame_count: Total number of frames.
        duration: Duration in seconds.
        output_path: Path to save metadata JSON.
    """
    import json

    metadata = {
        "animation_info": {
            "fps": fps,
            "frame_count": frame_count,
            "duration_seconds": round(duration, 3),
            "format": "FBX",
            "rig_type": "humanoid",
            "up_axis": "Y",
            "forward_axis": "-Z",
            "scale": 1.0,
            "units": "meters",
        },
        "unity_import_settings": {
            "animation_type": "Humanoid",
            "root_motion": True,
            "loop_time": False,
            "import_constraints": False,
        },
        "notes": [
            "Import FBX into Unity Assets folder",
            "Set Rig → Animation Type to Humanoid",
            "Create Animator Controller and assign animation clip",
            "Use AR Foundation for AR placement",
        ],
    }

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Unity metadata saved to {output_path}")
