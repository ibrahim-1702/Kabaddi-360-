"""
Visualization generation functions for pipeline results
Creates videos for Level 2-4 analysis stages
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Dict

# COCO-17 skeleton connections
COCO17_SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),  # Head
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # Arms
    (5, 11), (6, 12), (11, 12),  # Torso
    (11, 13), (13, 15), (12, 14), (14, 16)  # Legs
]

def scale_pose_to_canvas(pose: np.ndarray, canvas_width: int, canvas_height: int) -> np.ndarray:
    """Scale normalized pose coordinates to canvas pixels"""
    scale_factor = min(canvas_width, canvas_height) // 4
    center_x = canvas_width // 2
    center_y = canvas_height // 2
    
    scaled = np.zeros_like(pose)
    for j in range(17):
        if not np.isnan(pose[j]).any():
            x = int(pose[j, 0] * scale_factor + center_x)
            y = int(pose[j, 1] * scale_factor + center_y)
            scaled[j] = [x, y]
        else:
            scaled[j] = [np.nan, np.nan]
    
    return scaled


def draw_skeleton(frame: np.ndarray, pose: np.ndarray, 
                  line_color: Tuple[int, int, int] = (0, 255, 0),
                  joint_color: Tuple[int, int, int] = (0, 255, 255),
                  thickness: int = 2):
    """Draw COCO-17 skeleton on frame"""
    # Draw connections
    for (j1, j2) in COCO17_SKELETON:
        if not (np.isnan(pose[j1]).any() or np.isnan(pose[j2]).any()):
            pt1 = tuple(pose[j1].astype(int))
            pt2 = tuple(pose[j2].astype(int))
            cv2.line(frame, pt1, pt2, line_color, thickness)
    
    # Draw joints
    for j in range(17):
        if not np.isnan(pose[j]).any():
            pt = tuple(pose[j].astype(int))
            cv2.circle(frame, pt, 4, joint_color, -1)


def create_level2_visualization(aligned_expert: np.ndarray, aligned_user: np.ndarray, 
                                output_path: Path, fps: int = 30):
    """
    Create Level-2 DTW alignment side-by-side visualization
    
    Args:
        aligned_expert: Aligned expert poses (T, 17, 2)
        aligned_user: Aligned user poses (T, 17, 2)
        output_path: Output video path
        fps: Frames per second
    """
    T = aligned_expert.shape[0]
    canvas_width = 600
    canvas_height = 600
    
    # Video writer - use H.264 codec for browser compatibility
    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 codec
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (canvas_width * 2, canvas_height))
    
    for t in range(T):
        # Create canvas
        frame = np.zeros((canvas_height, canvas_width * 2, 3), dtype=np.uint8)
        
        # Scale poses
        expert_scaled = scale_pose_to_canvas(aligned_expert[t], canvas_width, canvas_height)
        user_scaled = scale_pose_to_canvas(aligned_user[t], canvas_width, canvas_height)
        
        # Offset user to right side
        user_scaled[:, 0] += canvas_width
        
        # Draw skeletons
        draw_skeleton(frame, expert_scaled, line_color=(0, 255, 0), joint_color=(0, 255, 255))  # Green
        draw_skeleton(frame, user_scaled, line_color=(255, 255, 0), joint_color=(255, 255, 0))  # Cyan
        
        # Add labels
        cv2.putText(frame, f"Expert Frame: {t}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"User Frame: {t}", (canvas_width + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, "DTW TEMPORAL ALIGNMENT", (canvas_width - 150, canvas_height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        writer.write(frame)
    
    writer.release()
    return output_path


def create_level3_visualization(aligned_expert: np.ndarray, aligned_user: np.ndarray, 
                                error_data: Dict, output_path: Path, fps: int = 30):
    """
    Create Level-3 error visualization with color-coded skeleton
    
    Args:
        aligned_expert: Aligned expert poses (T, 17, 2)
        aligned_user: Aligned user poses (T, 17, 2)
        error_data: Error statistics from Level-3
        output_path: Output video path
        fps: Frames per second
    """
    T = aligned_user.shape[0]
    canvas_width = 800
    canvas_height = 600
    
    # Extract joint errors
    joint_stats = error_data['joint_statistics']
    mean_errors = {name: stats['mean'] for name, stats in joint_stats.items()}
    max_val = max(mean_errors.values()) if mean_errors else 1.0
    max_error = max_val if max_val > 0 else 1.0
    
    # Video writer - use H.264 codec for browser compatibility
    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 codec
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (canvas_width, canvas_height))
    
    # Determine phases
    early_end = T // 3
    mid_end = 2 * T // 3
    
    for t in range(T):
        # Create canvas
        frame = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
        
        # Scale poses
        expert_scaled = scale_pose_to_canvas(aligned_expert[t], canvas_width, canvas_height)
        user_scaled = scale_pose_to_canvas(aligned_user[t], canvas_width, canvas_height)
        
        # Determine phase
        if t < early_end:
            phase = "EARLY"
            phase_color = (100, 200, 100)
        elif t < mid_end:
            phase = "MID"
            phase_color = (200, 200, 100)
        else:
            phase = "LATE"
            phase_color = (200, 100, 100)
        
        # Draw expert skeleton first (in gray/white - reference)
        draw_skeleton(frame, expert_scaled, line_color=(100, 100, 100), joint_color=(150, 150, 150), thickness=2)
        
        # Draw user skeleton with error-based coloring (on top)
        # Red = high error, Green = low error
        for (j1, j2) in COCO17_SKELETON:
            if not (np.isnan(user_scaled[j1]).any() or np.isnan(user_scaled[j2]).any()):
                pt1 = tuple(user_scaled[j1].astype(int))
                pt2 = tuple(user_scaled[j2].astype(int))
                # Color based on average error (green=good, red=bad)
                error_ratio = min(mean_errors.get(f"joint_{j1}", 0.5) / max_error, 1.0)
                color = (0, int(255 * (1 - error_ratio)), int(255 * error_ratio))
                cv2.line(frame, pt1, pt2, color, 3)
        
        # Draw user joints (red circles)
        for j in range(17):
            if not np.isnan(user_scaled[j]).any():
                pt = tuple(user_scaled[j].astype(int))
                cv2.circle(frame, pt, 5, (0, 0, 255), -1)
        
        # Add phase label
        cv2.putText(frame, f"PHASE: {phase}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, phase_color, 3)
        cv2.putText(frame, f"Frame: {t}/{T}", (20, canvas_height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Add legend
        cv2.putText(frame, "Gray=Expert, Red=User Errors", (canvas_width - 280, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        writer.write(frame)
    
    writer.release()
    return output_path


def create_level4_visualization(aligned_user: np.ndarray, scores: Dict,
                                output_path: Path, fps: int = 30):
    """
    Create Level-4 scoring visualization with HUD overlay
    
    Args:
        aligned_user: Aligned user poses (T, 17, 2)
        scores: Similarity scores from Level-4
        output_path: Output video path
        fps: Frames per second
    """
    T = aligned_user.shape[0]
    canvas_width = 800
    canvas_height = 600
    
    # Video writer - use H.264 codec for browser compatibility
    fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264 codec
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (canvas_width, canvas_height))
    
    for t in range(T):
        # Create canvas
        frame = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)
        
        # Scale pose
        user_scaled = scale_pose_to_canvas(aligned_user[t], canvas_width, canvas_height)
        
        # Draw skeleton in cyan
        draw_skeleton(frame, user_scaled, line_color=(255, 255, 0), joint_color=(0, 255, 255))
        
        # Draw score HUD
        hud_x = 20
        hud_y = 50
        cv2.putText(frame, "PERFORMANCE SUMMARY", (hud_x, hud_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, f"Structural: {scores['structural']}%", (hud_x, hud_y + 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)
        cv2.putText(frame, f"Temporal: {scores['temporal']}%", (hud_x, hud_y + 75), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 255, 100), 2)
        cv2.putText(frame, f"Overall: {scores['overall']}%", (hud_x, hud_y + 110), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 255, 255), 2)
        
        # Frame counter
        cv2.putText(frame, f"Frame: {t}/{T}", (canvas_width - 150, canvas_height - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        writer.write(frame)
    
    writer.release()
    return output_path
