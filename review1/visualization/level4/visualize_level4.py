#!/usr/bin/env python3
"""
Level-4: Scoring Summary Visualization

Purpose:
    Generate clean summary video with neutral skeleton and HUD overlay
    showing overall performance scores.
    
    This is PURE VISUALIZATION of computed scores - no new analysis.

Inputs:
    - expert_aligned.npy: DTW-aligned expert poses (T, 17, 2)
    - user_aligned.npy: DTW-aligned user poses (T, 17, 2)
    - similarity_scores.json: Scores from compute_similarity_scores.py

Outputs:
    - output_scoring_summary.mp4: Summary video with neutral skeleton + HUD

Scope:
    ✓ Neutral skeleton rendering (NO error coloring)
   ✓ Static HUD overlay with scores
    ✗ NO error visualization
    ✗ NO phase labels
    ✗ NO feedback text

Design Rationale:
    - Neutral visualization emphasizes "summary" nature
    - Clean HUD provides at-a-glance performance assessment
    - Complements Level-3 error visualization (separation of concerns)
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


# ============================================================================
# VISUALIZATION PARAMETERS
# ============================================================================

CANVAS_SIZE = 600
FPS = 30

# Skeleton styling (neutral colors)
COLOR_USER = (255, 255, 0)      # Cyan - neutral, visible
COLOR_EXPERT = (180, 180, 180)  # Light gray - subtle reference

LINE_THICKNESS_USER = 2
LINE_THICKNESS_EXPERT = 1
JOINT_RADIUS_USER = 5
JOINT_RADIUS_EXPERT = 3

# HUD styling
HUD_BG_COLOR = (40, 40, 40)      # Dark gray background
HUD_TEXT_COLOR = (255, 255, 255) # White text
HUD_PADDING = 20
HUD_LINE_HEIGHT = 35


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def load_inputs(expert_path: str, user_path: str, scores_path: str) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """
    Load aligned poses and similarity scores.
    
    Validates:
        - Pose files exist and have shape (T, 17, 2)
        - Scores JSON exists and contains required scores
        - Temporal consistency
    
    Returns:
        (expert_poses, user_poses, scores)
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
    
    # Load scores
    if not os.path.exists(scores_path):
        raise FileNotFoundError(f"Scores JSON not found: {scores_path}")
    
    with open(scores_path, 'r') as f:
        scores = json.load(f)
    
    # Validate scores
    required_keys = ['structural_similarity', 'temporal_similarity', 'overall_score']
    for key in required_keys:
        if key not in scores:
            raise ValueError(f"Scores JSON missing required key: '{key}'")
    
    return expert_poses, user_poses, scores


def scale_pose_for_display(pose: np.ndarray, canvas_size: int) -> np.ndarray:
    """
    Scale pose coordinates to canvas pixel coordinates with proper normalization.
    
    (Same as Level-3 scaling function)
    """
    # Find bounding box of the pose
    valid_joints = ~np.isnan(pose).any(axis=1)
    if not valid_joints.any():
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
    
    # Handle NaN joints
    scaled = np.nan_to_num(scaled, nan=canvas_size // 2)
    
    return scaled.astype(np.int32)


def render_neutral_skeleton(
    canvas: np.ndarray,
    pose: np.ndarray,
    connections: List[Tuple[int, int]],
    color: Tuple[int, int, int],
    line_thickness: int,
    joint_radius: int
) -> None:
    """
    Render skeleton in neutral color (no error coding).
    
    Args:
        canvas: Image to draw on (modified in-place)
        pose: (17, 2) joint positions in pixel coordinates
        connections: COCO-17 bone pairs
        color: BGR color tuple
        line_thickness: Line width
        joint_radius: Circle radius for joints
    
    Design Note:
        Neutral coloring emphasizes "summary" nature - no error details.
    """
    # Draw bones
    for (j1, j2) in connections:
        pt1 = tuple(pose[j1])
        pt2 = tuple(pose[j2])
        cv2.line(canvas, pt1, pt2, color, line_thickness)
    
    # Draw joints
    for j in range(17):
        center = tuple(pose[j])
        cv2.circle(canvas, center, joint_radius, color, -1)


def get_score_color(score: float) -> Tuple[int, int, int]:
    """
    Get color for overall score (for visual feedback in HUD).
    
    Args:
        score: Overall score (0-100)
    
    Returns:
        BGR color tuple
    """
    if score >= 80:
        return (0, 255, 0)      # Green - good
    elif score >= 60:
        return (0, 255, 255)    # Yellow - medium
    else:
        return (0, 0, 255)      # Red - needs improvement


def render_hud(canvas: np.ndarray, scores: Dict) -> None:
    """
    Render static HUD overlay with scores.
    
    Layout (top-left box):
        PERFORMANCE SUMMARY
        ─────────────────────
        Structural: XX.X%
        Temporal:   XX.X%
        Overall:    XX.X%
    
    Design Note:
        - Semi-transparent background for readability
        - Large, clear font
        - Color-coded overall score
        - Static (same for all frames) - emphasizes summary nature
    """
    # Extract scores
    structural = scores['structural_similarity']
    temporal = scores['temporal_similarity']
    overall = scores['overall_score']
    
    # HUD dimensions
    hud_width = 280
    hud_height = 160
    hud_x = HUD_PADDING
    hud_y = HUD_PADDING
    
    # Draw semi-transparent background
    overlay = canvas.copy()
    cv2.rectangle(
        overlay,
        (hud_x, hud_y),
        (hud_x + hud_width, hud_y + hud_height),
        HUD_BG_COLOR,
        -1
    )
    cv2.addWeighted(overlay, 0.7, canvas, 0.3, 0, canvas)
    
    # Draw border
    cv2.rectangle(
        canvas,
        (hud_x, hud_y),
        (hud_x + hud_width, hud_y + hud_height),
        (100, 100, 100),
        2
    )
    
    # Title
    cv2.putText(
        canvas,
        "PERFORMANCE SUMMARY",
        (hud_x + 15, hud_y + 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        HUD_TEXT_COLOR,
        1
    )
    
    # Separator line
    cv2.line(
        canvas,
        (hud_x + 15, hud_y + 40),
        (hud_x + hud_width - 15, hud_y + 40),
        (100, 100, 100),
        1
    )
    
    # Scores
    y_offset = hud_y + 70
    
    # Structural
    cv2.putText(
        canvas,
        f"Structural: {structural:.1f}%",
        (hud_x + 20, y_offset),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        HUD_TEXT_COLOR,
        1
    )
    
    # Temporal
    y_offset += HUD_LINE_HEIGHT
    cv2.putText(
        canvas,
        f"Temporal:   {temporal:.1f}%",
        (hud_x + 20, y_offset),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        HUD_TEXT_COLOR,
        1
    )
    
    # Overall (color-coded)
    y_offset += HUD_LINE_HEIGHT
    overall_color = get_score_color(overall)
    cv2.putText(
        canvas,
        f"Overall:    {overall:.1f}%",
        (hud_x + 20, y_offset),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        overall_color,
        2
    )


def compose_frame(
    expert_pose: np.ndarray,
    user_pose: np.ndarray,
    scores: Dict,
    frame_idx: int,
    total_frames: int,
    show_expert: bool = True
) -> np.ndarray:
    """
    Compose complete summary frame.
    
    Args:
        expert_pose: (17, 2) expert pose in pixel coords
        user_pose: (17, 2) user pose in pixel coords
        scores: Similarity scores dictionary
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
        render_neutral_skeleton(
            canvas,
            expert_pose,
            COCO17_CONNECTIONS,
            COLOR_EXPERT,
            LINE_THICKNESS_EXPERT,
            JOINT_RADIUS_EXPERT
        )
    
    # Render user skeleton (foreground, neutral cyan)
    render_neutral_skeleton(
        canvas,
        user_pose,
        COCO17_CONNECTIONS,
        COLOR_USER,
        LINE_THICKNESS_USER,
        JOINT_RADIUS_USER
    )
    
    # Add HUD overlay
    render_hud(canvas, scores)
    
    # Add frame counter (subtle, bottom right)
    cv2.putText(
        canvas,
        f"Frame: {frame_idx + 1}/{total_frames}",
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
    Main entry point for Level-4 scoring summary visualization.
    
    Usage:
        python visualize_level4.py <expert.npy> <user.npy> <scores.json>
    
    Output:
        output_scoring_summary.mp4
    """
    print("=" * 70)
    print("LEVEL-4: SCORING SUMMARY VISUALIZATION")
    print("=" * 70)
    print("\nGenerating neutral skeleton with HUD overlay.")
    print("Scope: Summary visualization only (no error details).\n")
    
    # ========================================================================
    # Parse Arguments
    # ========================================================================
    if len(sys.argv) != 4:
        print("Usage: python visualize_level4.py <expert.npy> <user.npy> <scores.json>")
        print("\nExample:")
        print("  python visualize_level4.py \\")
        print("      ../../level2/aligned_poses/expert_aligned_user1.npy \\")
        print("      ../../level2/aligned_poses/user_1_aligned.npy \\")
        print("      similarity_scores.json")
        sys.exit(1)
    
    expert_path = sys.argv[1]
    user_path = sys.argv[2]
    scores_path = sys.argv[3]
    
    output_path = "output_scoring_summary.mp4"
    
    # ========================================================================
    # STEP 1: Load Inputs
    # ========================================================================
    print("[STEP 1] Loading aligned poses and similarity scores...")
    
    try:
        expert_poses, user_poses, scores = load_inputs(expert_path, user_path, scores_path)
        T = expert_poses.shape[0]
        
        print(f"  ✓ Expert poses: {expert_path}")
        print(f"    Shape: {expert_poses.shape}")
        print(f"  ✓ User poses: {user_path}")
        print(f"    Shape: {user_poses.shape}")
        print(f"  ✓ Scores: {scores_path}")
        print(f"    Structural: {scores['structural_similarity']:.1f}%")
        print(f"    Temporal: {scores['temporal_similarity']:.1f}%")
        print(f"    Overall: {scores['overall_score']:.1f}%")
    except Exception as e:
        print(f"  ✗ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    
    # ========================================================================
    # STEP 2: Render Summary Video
    # ========================================================================
    print("\n[STEP 2] Rendering neutral skeleton with HUD overlay...")
    
    # Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, FPS, (CANVAS_SIZE, CANVAS_SIZE))
    
    if not out.isOpened():
        raise RuntimeError(f"Cannot create output video: {output_path}")
    
    # Render each frame
    for t in range(T):
        # Scale poses to canvas coordinates
        expert_scaled = scale_pose_for_display(expert_poses[t], CANVAS_SIZE)
        user_scaled = scale_pose_for_display(user_poses[t], CANVAS_SIZE)
        
        # Compose frame
        frame = compose_frame(
            expert_scaled,
            user_scaled,
            scores,
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
    print("LEVEL-4 SCORING SUMMARY VISUALIZATION COMPLETE")
    print("=" * 70)
    print(f"\n✓ Output: {output_path}")
    print(f"  - Neutral skeleton (cyan user / gray expert)")
    print(f"  - HUD overlay with performance scores")
    print(f"  - No error coloring (summary-level visualization)")
    print(f"\n✓ Provides at-a-glance performance assessment")
    print(f"✓ Complements Level-3 detailed error visualization")
    print(f"✓ Ready for review presentation")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
