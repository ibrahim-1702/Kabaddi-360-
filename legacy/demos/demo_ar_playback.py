#!/usr/bin/env python3
"""
Demo AR Playback Script

Demonstrates AR pose visualization using the ar_pose_renderer module.
Tests ghost-only, user-only, and overlay rendering modes.

Usage Examples:
    # Ghost-only playback
    python demo_ar_playback.py --pose pose_3d.npy --mode ghost --output ghost_demo.mp4
    
    # User-only playback
    python demo_ar_playback.py --pose raider_pose_3d.npy --mode user --output user_demo.mp4
    
    # Overlay mode (ghost vs user comparison)
    python demo_ar_playback.py --ghost raider_pose_3d.npy --user pose_3d.npy --mode overlay --output comparison.mp4
    
    # Limit frames for quick testing
    python demo_ar_playback.py --pose pose_3d.npy --mode ghost --output test.mp4 --max-frames 30
"""

import argparse
import numpy as np
from pathlib import Path
from ar_pose_renderer import PoseRenderer, COCO17Skeleton


def load_pose_from_npy(filepath: str) -> np.ndarray:
    """
    Load pose sequence from .npy file.
    
    Args:
        filepath: Path to .npy file
    
    Returns:
        Pose sequence (T, 17, 2)
    """
    pose = np.load(filepath)
    print(f"[Loaded] {filepath}")
    print(f"  Shape: {pose.shape}")
    print(f"  Data type: {pose.dtype}")
    print(f"  Value range: [{pose.min():.3f}, {pose.max():.3f}]")
    
    # Validate shape
    if pose.ndim == 3:
        T, J, C = pose.shape
        if J == 17 and C == 2:
            print(f"  ✅ Valid COCO-17 format: {T} frames")
            return pose
        elif J == 17 and C == 3:
            # Has confidence scores - extract only x,y
            print(f"  ⚠️  3D data detected (T, 17, 3) - extracting x,y only")
            return pose[:, :, :2]
        else:
            print(f"  ❌ Unexpected shape! Expected (T, 17, 2) or (T, 17, 3)")
            raise ValueError(f"Invalid pose shape: {pose.shape}")
    else:
        print(f"  ❌ Unexpected dimensions! Expected 3D array (T, J, C)")
        raise ValueError(f"Invalid pose dimensions: {pose.ndim}")


def main(args):
    """Main demo execution."""
    
    print("=" * 70)
    print("AR Pose Playback Demo")
    print("=" * 70)
    print()
    
    # Display COCO-17 skeleton info
    print("COCO-17 Skeleton Structure:")
    print(f"  Joints: {len(COCO17Skeleton.JOINT_NAMES)}")
    print(f"  Limb connections: {len(COCO17Skeleton.LIMB_CONNECTIONS)}")
    print()
    
    # Initialize renderer
    renderer = PoseRenderer(
        canvas_size=(args.width, args.height),
        fps=args.fps,
        line_thickness=args.line_thickness,
        joint_radius=args.joint_radius
    )
    
    print(f"Renderer Configuration:")
    print(f"  Canvas size: {args.width}x{args.height}")
    print(f"  FPS: {args.fps}")
    print(f"  Line thickness: {args.line_thickness}")
    print(f"  Joint radius: {args.joint_radius}")
    print()
    
    # Execute based on mode
    if args.mode == 'ghost':
        # Ghost-only mode
        if not args.pose:
            print("❌ ERROR: --pose argument required for ghost mode")
            return
        
        print("=" * 70)
        print("Mode: GHOST-ONLY")
        print("=" * 70)
        print()
        
        ghost_pose = load_pose_from_npy(args.pose)
        print()
        
        output_path = args.output or "ghost_playback.mp4"
        renderer.render_ghost_only(ghost_pose, output_path, args.max_frames)
        
    elif args.mode == 'user':
        # User-only mode
        if not args.pose:
            print("❌ ERROR: --pose argument required for user mode")
            return
        
        print("=" * 70)
        print("Mode: USER-ONLY")
        print("=" * 70)
        print()
        
        user_pose = load_pose_from_npy(args.pose)
        print()
        
        output_path = args.output or "user_playback.mp4"
        renderer.render_user_only(user_pose, output_path, args.max_frames)
        
    elif args.mode == 'overlay':
        # Overlay mode
        if not args.ghost or not args.user:
            print("❌ ERROR: Both --ghost and --user arguments required for overlay mode")
            return
        
        print("=" * 70)
        print("Mode: OVERLAY (Ghost vs User)")
        print("=" * 70)
        print()
        
        print("Loading Ghost pose:")
        ghost_pose = load_pose_from_npy(args.ghost)
        print()
        
        print("Loading User pose:")
        user_pose = load_pose_from_npy(args.user)
        print()
        
        output_path = args.output or "overlay_playback.mp4"
        renderer.render_overlay(ghost_pose, user_pose, output_path, args.max_frames)
    
    else:
        print(f"❌ ERROR: Invalid mode '{args.mode}'. Use 'ghost', 'user', or 'overlay'")
        return
    
    print()
    print("=" * 70)
    print("✅ DEMO COMPLETE")
    print("=" * 70)
    print(f"Output saved to: {output_path}")
    print()
    print("Next steps:")
    print("  1. Open the video file to verify visual quality")
    print("  2. For validation: extract pose from rendered video using extract_pose.py")
    print("  3. Compare original vs re-extracted using pose_validation_metrics.py")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Demo script for AR pose playback visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ghost-only mode
  python demo_ar_playback.py --pose pose_3d.npy --mode ghost --output ghost.mp4
  
  # User-only mode
  python demo_ar_playback.py --pose raider_pose_3d.npy --mode user --output user.mp4
  
  # Overlay comparison
  python demo_ar_playback.py --ghost raider_pose_3d.npy --user pose_3d.npy --mode overlay --output comparison.mp4
  
  # Quick test with limited frames
  python demo_ar_playback.py --pose pose_3d.npy --mode ghost --max-frames 30 --output test.mp4
        """
    )
    
    # Mode selection
    parser.add_argument(
        '--mode',
        type=str,
        required=True,
        choices=['ghost', 'user', 'overlay'],
        help="Rendering mode: 'ghost' (ghost-only), 'user' (user-only), or 'overlay' (comparison)"
    )
    
    # Input files
    parser.add_argument(
        '--pose',
        type=str,
        help="Path to pose .npy file (for ghost/user mode)"
    )
    parser.add_argument(
        '--ghost',
        type=str,
        help="Path to ghost pose .npy file (for overlay mode)"
    )
    parser.add_argument(
        '--user',
        type=str,
        help="Path to user pose .npy file (for overlay mode)"
    )
    
    # Output
    parser.add_argument(
        '--output',
        type=str,
        help="Output video path (default: auto-generated based on mode)"
    )
    
    # Rendering options
    parser.add_argument(
        '--width',
        type=int,
        default=640,
        help="Canvas width in pixels (default: 640)"
    )
    parser.add_argument(
        '--height',
        type=int,
        default=480,
        help="Canvas height in pixels (default: 480)"
    )
    parser.add_argument(
        '--fps',
        type=int,
        default=30,
        help="Output video FPS (default: 30)"
    )
    parser.add_argument(
        '--line-thickness',
        type=int,
        default=2,
        help="Skeleton line thickness (default: 2)"
    )
    parser.add_argument(
        '--joint-radius',
        type=int,
        default=4,
        help="Joint circle radius (default: 4)"
    )
    parser.add_argument(
        '--max-frames',
        type=int,
        default=None,
        help="Limit number of frames to render (for testing)"
    )
    
    args = parser.parse_args()
    main(args)
