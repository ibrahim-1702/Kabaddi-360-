#!/usr/bin/env python3
"""
Level-3 Step-2: Visual Error Localization

Purpose:
    Visualize joint errors using color-coded skeleton rendering.
    Uses previously computed error data - NO recomputation.

Inputs:
    - expert_aligned.npy: DTW-aligned expert poses (T, 17, 2)
    - user_aligned.npy: DTW-aligned user poses (T, 17, 2)
    - joint_errors.json: Error statistics from Level-3 Step-1

Outputs:
    - output_error_localization.mp4: Color-coded skeleton video

Scope:
    ✓ Error-based color coding (GREEN/YELLOW/RED)
    ✓ Temporal phase labels (EARLY/MID/LATE)
    ✓ Optional expert reference skeleton
    ✗ NO error recomputation
    ✗ NO scoring or feedback

Design Rationale:
    - Colors use FRAME-WISE joint errors (error[t][j]), not aggregates
    - Global thresholds prevent color flickering
    - Errors visualized AFTER DTW (spatial deviation analysis)
    - Color > numbers for immediate pattern recognition
"""

import numpy as np
import json
import cv2
import os
import sys
from typing import Tuple, Dict, List

# ============================================================================
# COCO-17 SKELETON CONNECTIONS
# ============================================================================

COCO17_CONNECTIONS = [
    (0, 1), (0, 2),      # nose to eyes
    (1, 3), (2, 4),      # eyes to ears
    (0, 5), (0, 6),      # nose to shoulders
    (5, 7), (7, 9),      # left arm
    (6, 8), (8, 10),     # right arm
    (5, 6),              # shoulders
    (5, 11), (6, 12),    # shoulders to hips
    (11, 12),            # hips
    (11, 13), (13, 15),  # left leg
    (12, 14), (14, 16)   # right leg
]

# Visualization parameters
CANVAS_SIZE = 600
FPS = 30
JOINT_RADIUS_USER = 5
JOINT_RADIUS_EXPERT = 3
LINE_THICKNESS_USER = 2
LINE_THICKNESS_EXPERT = 1

# Color definitions (BGR for OpenCV)
COLOR_GREEN = (0, 255, 0)      # Good (low error)
COLOR_YELLOW = (0, 255, 255)   # Medium error
COLOR_RED = (0, 0, 255)        # High error (critical)
COLOR_EXPERT = (180, 180, 180) # Light gray for expert reference


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def load_inputs(expert_path: str, user_path: str, errors_path: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Load aligned poses and error JSON.
    
    Validates:
        - Both pose files exist and have shape (T, 17, 2)
        - JSON exists and contains required keys
        - Temporal consistency: T matches across all inputs
    
    Returns:
        (expert_poses, user_poses, error_data)
    
    Raises:
        FileNotFoundError: If files don't exist
        ValueError: If data is invalid or inconsistent
    """
    # Load poses
    if not os.path.exists(expert_path):
        raise FileNotFoundError(f"Expert pose file not found: {expert_path}")
    if not os.path.exists(user_path):
        raise FileNotFoundError(f"User pose file not found: {user_path}")
    
    expert_poses = np.load(expert_path)
    user_poses = np.load(user_path)
    
    # Validate shapes
    if expert_poses.shape != user_poses.shape:
        raise ValueError(f"Pose shape mismatch: expert{expert_poses.shape} vs user{user_poses.shape}")
    
    if expert_poses.shape[1] != 17 or expert_poses.shape[2] != 2:
        raise ValueError(f"Invalid pose shape: expected (T, 17, 2), got {expert_poses.shape}")
    
    # Load error JSON
    if not os.path.exists(errors_path):
        raise FileNotFoundError(f"Error JSON not found: {errors_path}")
    
    with open(errors_path, 'r') as f:
        error_data = json.load(f)
    
    # Validate JSON structure
    required_keys = ['metadata', 'frame_joint_errors']
    for key in required_keys:
        if key not in error_data:
            raise ValueError(f"Error JSON missing required key: '{key}'")
    
    # Validate temporal consistency
    T = expert_poses.shape[0]
    if error_data['metadata']['num_frames'] != T:
        raise ValueError(
            f"Temporal mismatch: poses have {T} frames, "
            f"JSON has {error_data['metadata']['num_frames']} frames"
        )
    
    return expert_poses, user_poses, error_data


def compute_error_thresholds(error_data: Dict) -> Dict[str, float]:
    """
    Compute global error thresholds for color coding.
    
    Uses joint_statistics (aggregated across time):
        E_mean = mean of all joint mean errors
        E_std = std of all joint mean errors
    
    Returns:
        {
            'green_max': E_mean,
            'yellow_max': E_mean + E_std
        }
    
    Design Note:
        Global thresholds (not per-frame) prevent color flickering
        and provide consistent visual language across entire sequence.
    """
    joint_stats = error_data['joint_statistics']
    
    # Extract mean errors from all joints
    mean_errors = [stats['mean'] for stats in joint_stats.values()]
    
    E_mean = np.mean(mean_errors)
    E_std = np.std(mean_errors)
    
    return {
        'green_max': E_mean,
        'yellow_max': E_mean + E_std
    }


def get_joint_color(error_value: float, thresholds: Dict) -> Tuple[int, int, int]:
    """
    Map frame-wise joint error to BGR color.
    
    CRITICAL: Uses error[t][j] from frame_joint_errors, NOT aggregated values.
    
    Thresholds:
        GREEN: error ≤ E_mean (good performance)
        YELLOW: E_mean < error ≤ E_mean + E_std (needs attention)
        RED: error > E_mean + E_std (critical deviation)
    
    Args:
        error_value: Frame-wise joint error value
        thresholds: Dict with 'green_max' and 'yellow_max'
    
    Returns:
        (B, G, R) tuple for OpenCV
    
    Design Note:
        Color coding enables immediate visual pattern recognition
        without numerical analysis. Critical for viva defense.
    """
    if np.isnan(error_value):
        # Handle NaN (missing joint) - render as dim gray
        return (100, 100, 100)
    
    if error_value <= thresholds['green_max']:
        return COLOR_GREEN
    elif error_value <= thresholds['yellow_max']:
        return COLOR_YELLOW
    else:
        return COLOR_RED


def get_phase_label(frame_idx: int, total_frames: int) -> str:
    """
    Determine temporal phase label.
    
    Phase boundaries (MUST match Level-3 Step-1):
        EARLY: [0, T//3)
       MID: [T//3, 2*T//3)
        LATE: [2*T//3, T)
    
    Returns: "EARLY", "MID", or "LATE"
    """
    early_end = total_frames // 3
    mid_end = 2 * total_frames // 3
    
    if frame_idx < early_end:
        return "EARLY"
    elif frame_idx < mid_end:
        return "MID"
    else:
        return "LATE"


def scale_pose_for_display(pose: np.ndarray, canvas_size: int) -> np.ndarray:
    """
    Scale pose coordinates to canvas pixel coordinates with proper normalization.
    
    Args:
        pose: (17, 2) pose coordinates (may not be in [0, 1] range)
        canvas_size: Canvas dimension (pixels)
    
    Returns:
        (17, 2) pixel coordinates
    
    Design Note:
        Finds actual min/max of pose and normalizes to fit canvas with padding.
        This handles poses that aren't pre-normalized to [0, 1].
    """
    # Find bounding box of the pose
    valid_joints = ~np.isnan(pose).any(axis=1)
    if not valid_joints.any():
        # All joints are NaN, return center of canvas
        return np.full((17, 2), canvas_size // 2, dtype=np.int32)
    
    valid_pose = pose[valid_joints]
    
    min_x, min_y = valid_pose.min(axis=0)
    max_x, max_y = valid_pose.max(axis=0)
    
    # Calculate scale to fit in canvas with padding
    padding = 50
    available_width = canvas_size - 2 * padding
    available_height = canvas_size - 2 * padding
    
    width = max_x - min_x
    height = max_y - min_y
    
    # Avoid division by zero
    if width < 1e-6:
        width = 1.0
    if height < 1e-6:
        height = 1.0
    
    # Scale to fit (maintain aspect ratio)
    scale = min(available_width / width, available_height / height)
    
    # Normalize and scale
    normalized = (pose - [min_x, min_y]) * scale
    
    # Center in canvas
    pose_width = width * scale
    pose_height = height * scale
    offset_x = padding + (available_width - pose_width) / 2
    offset_y = padding + (available_height - pose_height) / 2
    
    scaled = normalized + [offset_x, offset_y]
    
    # Handle NaN joints (keep them at a safe position)
    scaled = np.nan_to_num(scaled, nan=canvas_size // 2)
    
    return scaled.astype(np.int32)



def render_skeleton(
    canvas: np.ndarray,
    pose: np.ndarray,
    joint_colors: List[Tuple[int, int, int]],
    connections: List[Tuple[int, int]],
    line_thickness: int = LINE_THICKNESS_USER,
    joint_radius: int = JOINT_RADIUS_USER
) -> None:
    """
    Render COCO-17 skeleton on canvas.
    
    Args:
        canvas: Image to draw on (modified in-place)
        pose: (17, 2) joint positions in pixel coordinates
        joint_colors: List of 17 BGR tuples (one per joint)
        connections: COCO-17 bone pairs
        line_thickness: Line width
        joint_radius: Circle radius for joints
    
    Drawing order:
        1. Lines (bones) - colored by average of endpoint colors
        2. Circles (joints) - colored by individual joint colors
    """
    # Draw bones
    for (j1, j2) in connections:
        pt1 = tuple(pose[j1])
        pt2 = tuple(pose[j2])
        
        # Average color of both endpoints
        color1 = np.array(joint_colors[j1])
        color2 = np.array(joint_colors[j2])
        bone_color = tuple(((color1 + color2) / 2).astype(int).tolist())
        
        cv2.line(canvas, pt1, pt2, bone_color, line_thickness)
    
    # Draw joints
    for j in range(17):
        center = tuple(pose[j])
        cv2.circle(canvas, center, joint_radius, joint_colors[j], -1)


def render_expert_reference(
    canvas: np.ndarray,
    expert_pose: np.ndarray,
    connections: List[Tuple[int, int]]
) -> None:
    """
    Render expert skeleton as faint gray reference (optional).
    
    Styling:
        - Color: Light gray (180, 180, 180)
        - Line thickness: 1 (thin)
        - Joint circles: Smaller radius
    
    Design Note:
        Expert is visually secondary to keep focus on user errors.
    """
    # Draw bones
    for (j1, j2) in connections:
        pt1 = tuple(expert_pose[j1])
        pt2 = tuple(expert_pose[j2])
        cv2.line(canvas, pt1, pt2, COLOR_EXPERT, LINE_THICKNESS_EXPERT)
    
    # Draw joints
    for j in range(17):
        center = tuple(expert_pose[j])
        cv2.circle(canvas, center, JOINT_RADIUS_EXPERT, COLOR_EXPERT, -1)


def compose_frame(
    expert_pose: np.ndarray,
    user_pose: np.ndarray,
    frame_errors: Dict[str, float],
    thresholds: Dict[str, float],
    frame_idx: int,
    total_frames: int,
    show_expert: bool = True
) -> np.ndarray:
    """
    Compose complete visualization frame.
    
    CRITICAL DATA FLOW:
        frame_errors (from frame_joint_errors[t])
        → get_joint_color()
        → joint_colors
        → render_skeleton()
    
    Args:
        expert_pose: (17, 2) expert pose in pixel coords
        user_pose: (17, 2) user pose in pixel coords
        frame_errors: {joint_name: error_value} for this frame
        thresholds: Color thresholds
        frame_idx: Current frame index
        total_frames: Total number of frames
        show_expert: Whether to render expert reference
    
    Returns:
        Composed frame (CANVAS_SIZE, CANVAS_SIZE, 3) BGR image
    """
    # Create black canvas
    canvas = np.zeros((CANVAS_SIZE, CANVAS_SIZE, 3), dtype=np.uint8)
    
    # Render expert reference (optional, background)
    if show_expert:
        render_expert_reference(canvas, expert_pose, COCO17_CONNECTIONS)
    
    # Get joint colors from frame-wise errors
    joint_colors = []
    joint_names = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]
    
    for joint_name in joint_names:
        error_value = frame_errors.get(joint_name, 0.0)
        color = get_joint_color(error_value, thresholds)
        joint_colors.append(color)
    
    # Render user skeleton (foreground, color-coded)
    render_skeleton(canvas, user_pose, joint_colors, COCO17_CONNECTIONS)
    
    # Add phase label
    phase = get_phase_label(frame_idx, total_frames)
    cv2.putText(
        canvas,
        f"PHASE: {phase}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )
    
    # Add frame index (subtle, bottom right)
    cv2.putText(
        canvas,
        f"Frame: {frame_idx}/{total_frames}",
        (CANVAS_SIZE - 150, CANVAS_SIZE - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (150, 150, 150),
        1
    )
    
    return canvas


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main entry point for Level-3 visual error localization.
    
    Usage:
        python visualize_level3.py <expert.npy> <user.npy> <errors.json>
    
    Output:
        output_error_localization.mp4
    
    Design Rationale:
        - Errors visualized AFTER DTW: Shows spatial deviations at
          corresponding movement phases (temporal sync already handled)
        - Global thresholds: Prevents color flickering, consistent visual language
        - Color > numbers: Immediate pattern recognition, easier viva explanation
        - Frame-wise coloring: Shows temporal error patterns, not just aggregates
    """
    print("=" * 70)
    print("LEVEL-3 STEP-2: VISUAL ERROR LOCALIZATION")
    print("=" * 70)
    print("\nGenerating color-coded skeleton visualization.")
    print("Scope: Error visualization only (no recomputation).\n")
    
    # ========================================================================
    # Parse Arguments
    # ========================================================================
    if len(sys.argv) != 4:
        print("Usage: python visualize_level3.py <expert.npy> <user.npy> <errors.json>")
        print("\nExample:")
        print("  python visualize_level3.py \\")
        print("      ../../level2/aligned_poses/expert_aligned_user1.npy \\")
        print("      ../../level2/aligned_poses/user_1_aligned.npy \\")
        print("      joint_errors_user1.json")
        sys.exit(1)
    
    expert_path = sys.argv[1]
    user_path = sys.argv[2]
    errors_path = sys.argv[3]
    
    output_path = "output_error_localization.mp4"
    
    # ========================================================================
    # STEP 1: Load Inputs
    # ========================================================================
    print("[STEP 1] Loading aligned poses and error data...")
    
    try:
        expert_poses, user_poses, error_data = load_inputs(expert_path, user_path, errors_path)
        T = expert_poses.shape[0]
        
        print(f"  ✓ Expert poses: {expert_path}")
        print(f"    Shape: {expert_poses.shape}")
        print(f"  ✓ User poses: {user_path}")
        print(f"    Shape: {user_poses.shape}")
        print(f"  ✓ Error data: {errors_path}")
        print(f"  ✓ Temporal consistency verified: T={T} frames")
    except Exception as e:
        print(f"  ✗ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    
    # ========================================================================
    # STEP 2: Compute Color Thresholds
    # ========================================================================
    print("\n[STEP 2] Computing global error thresholds...")
    
    thresholds = compute_error_thresholds(error_data)
    
    print(f"  ✓ Thresholds computed:")
    print(f"    GREEN (good):    error ≤ {thresholds['green_max']:.4f}")
    print(f"    YELLOW (medium): error ≤ {thresholds['yellow_max']:.4f}")
    print(f"    RED (high):      error > {thresholds['yellow_max']:.4f}")
    print(f"  Design: Global thresholds prevent color flickering")
    
    # ========================================================================
    # STEP 3: Render Visualization Video
    # ========================================================================
    print("\n[STEP 3] Rendering color-coded skeleton visualization...")
    
    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, FPS, (CANVAS_SIZE, CANVAS_SIZE))
    
    if not out.isOpened():
        raise RuntimeError(f"Cannot create output video: {output_path}")
    
    frame_joint_errors = error_data['frame_joint_errors']
    
    # Render each frame
    for t in range(T):
        # Scale poses to canvas coordinates
        expert_scaled = scale_pose_for_display(expert_poses[t], CANVAS_SIZE)
        user_scaled = scale_pose_for_display(user_poses[t], CANVAS_SIZE)
        
        # Get frame-wise errors (CRITICAL: uses error[t][j])
        frame_errors = frame_joint_errors[str(t)]
        
        # Compose frame
        frame = compose_frame(
            expert_scaled,
            user_scaled,
            frame_errors,
            thresholds,
            t,
            T,
            show_expert=True
        )
        
        # Write frame
        out.write(frame)
        
        # Progress update
        if (t + 1) % 30 == 0 or (t + 1) == T:
            print(f"    Rendered {t + 1}/{T} frames")
    
    out.release()
    
    print(f"\n  ✓ Output video: {output_path}")
    print(f"    Total frames: {T}")
    print(f"    FPS: {FPS}")
    print(f"    Resolution: {CANVAS_SIZE}x{CANVAS_SIZE}")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("LEVEL-3 VISUAL ERROR LOCALIZATION COMPLETE")
    print("=" * 70)
    print(f"\n✓ Output: {output_path}")
    print(f"  - Color coding: GREEN (good) / YELLOW (medium) / RED (high)")
    print(f"  - Phase labels: EARLY / MID / LATE")
    print(f"  - Expert reference: Faint gray skeleton")
    print(f"\n✓ Visualization answers: 'Which joints are wrong, and when?'")
    print(f"✓ Frame-wise coloring shows temporal error patterns")
    print(f"✓ Ready for viva defense (visually explainable)")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
