#!/usr/bin/env python3
"""
AR Pose Renderer for Kabaddi Ghost Trainer

This module provides lightweight OpenCV-based visualization for COCO-17 pose sequences.
Supports ghost-only, user-only, and overlay rendering modes.

Key Features:
- No pose data modification (read-only operations)
- Temporal synchronization across sequences
- Suitable output for pose re-extraction validation
- Configurable colors and canvas size

Usage:
    from ar_pose_renderer import COCO17Skeleton, PoseRenderer
    
    renderer = PoseRenderer(canvas_size=(640, 480))
    video_path = renderer.render_ghost_only(ghost_pose, output_path='ghost.mp4')
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
from pathlib import Path


class COCO17Skeleton:
    """
    COCO-17 keypoint skeleton definition.
    
    Provides joint names and limb connectivity for skeletal visualization.
    """
    
    # Joint indices (COCO-17 format)
    NOSE = 0
    LEFT_EYE = 1
    RIGHT_EYE = 2
    LEFT_EAR = 3
    RIGHT_EAR = 4
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_ELBOW = 7
    RIGHT_ELBOW = 8
    LEFT_WRIST = 9
    RIGHT_WRIST = 10
    LEFT_HIP = 11
    RIGHT_HIP = 12
    LEFT_KNEE = 13
    RIGHT_KNEE = 14
    LEFT_ANKLE = 15
    RIGHT_ANKLE = 16
    
    # Joint names in order
    JOINT_NAMES = [
        "nose", "left_eye", "right_eye", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip",
        "left_knee", "right_knee", "left_ankle", "right_ankle"
    ]
    
    # Limb connections (pairs of joint indices)
    # This defines which joints should be connected to form the skeleton
    LIMB_CONNECTIONS = [
        # Face
        (NOSE, LEFT_EYE),
        (NOSE, RIGHT_EYE),
        (LEFT_EYE, LEFT_EAR),
        (RIGHT_EYE, RIGHT_EAR),
        
        # Torso
        (LEFT_SHOULDER, RIGHT_SHOULDER),
        (LEFT_SHOULDER, LEFT_HIP),
        (RIGHT_SHOULDER, RIGHT_HIP),
        (LEFT_HIP, RIGHT_HIP),
        
        # Left arm
        (LEFT_SHOULDER, LEFT_ELBOW),
        (LEFT_ELBOW, LEFT_WRIST),
        
        # Right arm
        (RIGHT_SHOULDER, RIGHT_ELBOW),
        (RIGHT_ELBOW, RIGHT_WRIST),
        
        # Left leg
        (LEFT_HIP, LEFT_KNEE),
        (LEFT_KNEE, LEFT_ANKLE),
        
        # Right leg
        (RIGHT_HIP, RIGHT_KNEE),
        (RIGHT_KNEE, RIGHT_ANKLE),
    ]
    
    @classmethod
    def get_joint_name(cls, index: int) -> str:
        """Get joint name by index."""
        if 0 <= index < len(cls.JOINT_NAMES):
            return cls.JOINT_NAMES[index]
        return f"unknown_{index}"


class PoseRenderer:
    """
    OpenCV-based renderer for COCO-17 pose sequences.
    
    Provides visualization functions for ghost/user/overlay modes with
    temporal synchronization and configurable styling.
    """
    
    # Color schemes (BGR format for OpenCV)
    COLOR_GHOST = (0, 255, 0)      # Green
    COLOR_USER = (255, 128, 0)     # Blue
    COLOR_BACKGROUND = (0, 0, 0)    # Black
    
    def __init__(
        self,
        canvas_size: Tuple[int, int] = (640, 480),
        fps: int = 30,
        line_thickness: int = 2,
        joint_radius: int = 4
    ):
        """
        Initialize pose renderer.
        
        Args:
            canvas_size: Output canvas size (width, height) in pixels
            fps: Frame rate for video output
            line_thickness: Thickness of skeleton limbs
            joint_radius: Radius of joint circles
        """
        self.canvas_size = canvas_size
        self.fps = fps
        self.line_thickness = line_thickness
        self.joint_radius = joint_radius
        
    def _normalize_coords(self, pose: np.ndarray) -> np.ndarray:
        """
        Convert pose coordinates to canvas pixel coordinates.
        
        Handles both normalized (0-1) and absolute pixel coordinates.
        
        Args:
            pose: Single pose frame (17, 2)
        
        Returns:
            Pose in pixel coordinates (17, 2)
        """
        pose_copy = pose.copy()
        
        # Check if coordinates are normalized (assume values < 10 are normalized)
        if np.max(pose_copy) <= 10.0:
            # Normalized coordinates - scale to canvas
            pose_copy[:, 0] *= self.canvas_size[0]  # x
            pose_copy[:, 1] *= self.canvas_size[1]  # y
        
        return pose_copy.astype(np.int32)
    
    def draw_skeleton(
        self,
        canvas: np.ndarray,
        pose: np.ndarray,
        color: Tuple[int, int, int],
        confidence_threshold: float = 0.0
    ) -> np.ndarray:
        """
        Draw a single pose skeleton on the canvas.
        
        Args:
            canvas: Canvas image (H, W, 3)
            pose: Single pose frame (17, 2)
            color: Line color in BGR format
            confidence_threshold: Minimum confidence to draw (not used if no conf data)
        
        Returns:
            Canvas with skeleton drawn
        """
        # Convert to pixel coordinates
        pose_px = self._normalize_coords(pose)
        
        # Draw limb connections
        for joint_a, joint_b in COCO17Skeleton.LIMB_CONNECTIONS:
            pt_a = tuple(pose_px[joint_a])
            pt_b = tuple(pose_px[joint_b])
            
            # Skip if points are invalid (negative or zero)
            if pt_a[0] <= 0 or pt_a[1] <= 0 or pt_b[0] <= 0 or pt_b[1] <= 0:
                continue
            
            cv2.line(canvas, pt_a, pt_b, color, self.line_thickness)
        
        # Draw joint points
        for joint_idx in range(len(pose_px)):
            pt = tuple(pose_px[joint_idx])
            
            # Skip invalid points
            if pt[0] <= 0 or pt[1] <= 0:
                continue
            
            cv2.circle(canvas, pt, self.joint_radius, color, -1)
        
        return canvas
    
    def _interpolate_sequence(
        self,
        pose_sequence: np.ndarray,
        target_length: int
    ) -> np.ndarray:
        """
        Interpolate pose sequence to target length for synchronization.
        
        Args:
            pose_sequence: Input pose (T, 17, 2)
            target_length: Desired number of frames
        
        Returns:
            Interpolated pose (target_length, 17, 2)
        """
        if len(pose_sequence) == target_length:
            return pose_sequence
        
        from scipy.interpolate import interp1d
        
        T, J, C = pose_sequence.shape
        original_indices = np.arange(T)
        target_indices = np.linspace(0, T - 1, target_length)
        
        interpolated = np.zeros((target_length, J, C), dtype=np.float32)
        
        for j in range(J):
            for c in range(C):
                f = interp1d(original_indices, pose_sequence[:, j, c], kind='linear')
                interpolated[:, j, c] = f(target_indices)
        
        return interpolated
    
    def _create_blank_canvas(self) -> np.ndarray:
        """Create a blank canvas for drawing."""
        return np.full(
            (self.canvas_size[1], self.canvas_size[0], 3),
            self.COLOR_BACKGROUND,
            dtype=np.uint8
        )
    
    def render_ghost_only(
        self,
        ghost_pose: np.ndarray,
        output_path: str,
        max_frames: Optional[int] = None
    ) -> str:
        """
        Render ghost pose sequence only.
        
        Args:
            ghost_pose: Ghost pose sequence (T, 17, 2)
            output_path: Path to save output video
            max_frames: Optional limit on number of frames to render
        
        Returns:
            Path to saved video file
        """
        T = len(ghost_pose) if max_frames is None else min(len(ghost_pose), max_frames)
        ghost_seq = ghost_pose[:T]
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, self.canvas_size)
        
        print(f"[Rendering] Ghost-only mode: {T} frames")
        
        for t in range(T):
            canvas = self._create_blank_canvas()
            canvas = self.draw_skeleton(canvas, ghost_seq[t], self.COLOR_GHOST)
            
            # Add frame info
            cv2.putText(
                canvas, f"Ghost | Frame: {t+1}/{T}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 255, 255), 2
            )
            
            out.write(canvas)
        
        out.release()
        print(f"[Done] Saved to: {output_path}")
        
        return output_path
    
    def render_user_only(
        self,
        user_pose: np.ndarray,
        output_path: str,
        max_frames: Optional[int] = None
    ) -> str:
        """
        Render user pose sequence only.
        
        Args:
            user_pose: User pose sequence (T, 17, 2)
            output_path: Path to save output video
            max_frames: Optional limit on number of frames to render
        
        Returns:
            Path to saved video file
        """
        T = len(user_pose) if max_frames is None else min(len(user_pose), max_frames)
        user_seq = user_pose[:T]
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, self.canvas_size)
        
        print(f"[Rendering] User-only mode: {T} frames")
        
        for t in range(T):
            canvas = self._create_blank_canvas()
            canvas = self.draw_skeleton(canvas, user_seq[t], self.COLOR_USER)
            
            # Add frame info
            cv2.putText(
                canvas, f"User | Frame: {t+1}/{T}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 255, 255), 2
            )
            
            out.write(canvas)
        
        out.release()
        print(f"[Done] Saved to: {output_path}")
        
        return output_path
    
    def render_overlay(
        self,
        ghost_pose: np.ndarray,
        user_pose: np.ndarray,
        output_path: str,
        max_frames: Optional[int] = None
    ) -> str:
        """
        Render ghost and user poses as overlay for comparison.
        
        Args:
            ghost_pose: Ghost pose sequence (T1, 17, 2)
            user_pose: User pose sequence (T2, 17, 2)
            output_path: Path to save output video
            max_frames: Optional limit on number of frames to render
        
        Returns:
            Path to saved video file
        """
        # Synchronize sequence lengths by interpolation
        T_ghost = len(ghost_pose)
        T_user = len(user_pose)
        T_target = max(T_ghost, T_user)
        
        if max_frames is not None:
            T_target = min(T_target, max_frames)
        
        print(f"[Rendering] Overlay mode: Synchronizing {T_ghost} ghost frames + {T_user} user frames -> {T_target} frames")
        
        # Interpolate to match lengths
        if T_ghost != T_target:
            ghost_seq = self._interpolate_sequence(ghost_pose, T_target)
        else:
            ghost_seq = ghost_pose[:T_target]
        
        if T_user != T_target:
            user_seq = self._interpolate_sequence(user_pose, T_target)
        else:
            user_seq = user_pose[:T_target]
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, self.canvas_size)
        
        for t in range(T_target):
            canvas = self._create_blank_canvas()
            
            # Draw ghost first (will be behind)
            canvas = self.draw_skeleton(canvas, ghost_seq[t], self.COLOR_GHOST)
            
            # Draw user on top
            canvas = self.draw_skeleton(canvas, user_seq[t], self.COLOR_USER)
            
            # Add frame info with legend
            cv2.putText(
                canvas, f"Overlay | Frame: {t+1}/{T_target}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 255, 255), 2
            )
            cv2.putText(
                canvas, "Ghost (Green) | User (Blue)",
                (10, self.canvas_size[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                (255, 255, 255), 1
            )
            
            out.write(canvas)
        
        out.release()
        print(f"[Done] Saved to: {output_path}")
        
        return output_path
    
    def save_frames(
        self,
        pose_sequence: np.ndarray,
        output_dir: str,
        color: Tuple[int, int, int] = COLOR_GHOST,
        prefix: str = "frame"
    ) -> List[str]:
        """
        Save individual frames as images (for debugging).
        
        Args:
            pose_sequence: Pose sequence (T, 17, 2)
            output_dir: Directory to save frames
            color: Skeleton color
            prefix: Filename prefix
        
        Returns:
            List of saved frame paths
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        saved_paths = []
        T = len(pose_sequence)
        
        print(f"[Saving Frames] {T} frames to {output_dir}")
        
        for t in range(T):
            canvas = self._create_blank_canvas()
            canvas = self.draw_skeleton(canvas, pose_sequence[t], color)
            
            frame_path = str(Path(output_dir) / f"{prefix}_{t:06d}.png")
            cv2.imwrite(frame_path, canvas)
            saved_paths.append(frame_path)
        
        print(f"[Done] Saved {len(saved_paths)} frames")
        
        return saved_paths


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    """
    Minimal test to verify skeleton rendering.
    """
    
    print("=" * 60)
    print("AR Pose Renderer - Skeleton Definition Test")
    print("=" * 60)
    
    # Display skeleton structure
    print(f"\nCOCO-17 Skeleton:")
    print(f"  Joints: {len(COCO17Skeleton.JOINT_NAMES)}")
    print(f"  Limbs: {len(COCO17Skeleton.LIMB_CONNECTIONS)}")
    
    print(f"\nJoint Names:")
    for idx, name in enumerate(COCO17Skeleton.JOINT_NAMES):
        print(f"  {idx:2d}: {name}")
    
    print(f"\nLimb Connections:")
    for i, (a, b) in enumerate(COCO17Skeleton.LIMB_CONNECTIONS):
        name_a = COCO17Skeleton.get_joint_name(a)
        name_b = COCO17Skeleton.get_joint_name(b)
        print(f"  {i+1:2d}. {name_a} → {name_b}")
    
    # Create a dummy pose for visualization test
    print("\n" + "=" * 60)
    print("Creating test visualization...")
    print("=" * 60)
    
    # Create a simple standing pose (normalized coordinates 0-1)
    test_pose = np.array([
        [0.5, 0.1],   # 0: nose
        [0.48, 0.09], # 1: left_eye
        [0.52, 0.09], # 2: right_eye
        [0.46, 0.1],  # 3: left_ear
        [0.54, 0.1],  # 4: right_ear
        [0.4, 0.25],  # 5: left_shoulder
        [0.6, 0.25],  # 6: right_shoulder
        [0.35, 0.4],  # 7: left_elbow
        [0.65, 0.4],  # 8: right_elbow
        [0.3, 0.55],  # 9: left_wrist
        [0.7, 0.55],  # 10: right_wrist
        [0.42, 0.55], # 11: left_hip
        [0.58, 0.55], # 12: right_hip
        [0.4, 0.75],  # 13: left_knee
        [0.6, 0.75],  # 14: right_knee
        [0.38, 0.95], # 15: left_ankle
        [0.62, 0.95], # 16: right_ankle
    ], dtype=np.float32)
    
    # Create a 30-frame sequence (simple standing)
    test_sequence = np.tile(test_pose, (30, 1, 1))
    
    # Add slight movement
    for t in range(30):
        offset = np.sin(t / 5) * 0.02
        test_sequence[t, :, 1] += offset  # Vertical bobbing
    
    # Render test
    renderer = PoseRenderer(canvas_size=(640, 480), fps=30)
    
    output_file = "test_skeleton_render.mp4"
    renderer.render_ghost_only(test_sequence, output_file)
    
    print(f"\n✅ Test complete! Check {output_file}")
    print("\nTo test overlay mode, run demo_ar_playback.py with actual pose data.")
