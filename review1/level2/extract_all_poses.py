#!/usr/bin/env python3
"""
Batch pose extraction script for Level-2 DTW visualization
Extracts COCO-17 poses from expert + 4 user videos
"""

import os
import sys

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'level1_pose'))

from pose_extract_cli import extract_pose_from_video

def main():
    print("=" * 70)
    print("LEVEL-2: POSE EXTRACTION FOR DTW VISUALIZATION")
    print("=" * 70)
    
    # Create poses directory
    poses_dir = os.path.join(os.path.dirname(__file__), 'poses')
    os.makedirs(poses_dir, exist_ok=True)
    print(f"\n✓ Poses directory: {poses_dir}")
    
    # Define extraction tasks
    tasks = [
        ("Expert", "../../samples/kabaddi_clip.mp4", "poses/expert_pose.npy"),
        ("User 1", "../../samples/users/user_1.mp4", "poses/user_1_pose.npy"),
        ("User 2", "../../samples/users/user_2.mp4", "poses/user_2_pose.npy"),
        ("User 3", "../../samples/users/user_3.mp4", "poses/user_3_pose.npy"),
        ("User 4", "../../samples/users/user_4.mp4", "poses/user_4_pose.npy"),
    ]
    
    # Execute extractions
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    for idx, (name, video_path, output_path) in enumerate(tasks, 1):
        print(f"\n[{idx}/5] Extracting {name} pose...")
        print(f"  Input:  {video_path}")
        print(f"  Output: {output_path}")
        
        # Convert relative paths to absolute
        video_abs = os.path.abspath(os.path.join(script_dir, video_path))
        output_abs = os.path.abspath(os.path.join(script_dir, output_path))
        
        try:
            extract_pose_from_video(video_abs, output_abs)
            print(f"  ✓ {name} pose extraction complete!")
        except Exception as e:
            print(f"  ✗ ERROR: {e}", file=sys.stderr)
            return 1
    
    print("\n" + "=" * 70)
    print("ALL POSE EXTRACTIONS COMPLETE!")
    print("=" * 70)
    
    # List extracted files
    print("\nExtracted pose files:")
    for filename in sorted(os.listdir(poses_dir)):
        if filename.endswith('.npy'):
            filepath = os.path.join(poses_dir, filename)
            print(f"  ✓ {filename} ({os.path.getsize(filepath):,} bytes)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
