#!/usr/bin/env python3
"""
Batch script to run Level-3 error computation for all 4 users.

Expects aligned poses from Level-2 in: ../level2/aligned_poses/
Outputs joint_errors_userN.json for each user.
"""

import os
import sys
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compute_joint_errors import (
    load_aligned_poses,
    compute_joint_errors,
    aggregate_joint_stats,
    aggregate_frame_stats,
    compute_phase_stats,
    export_frame_joint_errors,  # NEW: for frame-wise errors
    export_json
)
import numpy as np

def main():
    print("=" * 70)
    print("LEVEL-3: BATCH ERROR COMPUTATION (ALL 4 USERS)")
    print("=" * 70)
    print("\nComputing joint errors for all user performances.\n")
    
    # Paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    aligned_poses_dir = os.path.join(script_dir, "..", "..", "level2", "aligned_poses")
    
    # Check if aligned poses directory exists
    if not os.path.exists(aligned_poses_dir):
        print(f"ERROR: Aligned poses directory not found: {aligned_poses_dir}")
        print("\nPlease run Level-2 visualization first:")
        print("  cd review1/level2")
        print("  python visualize_level2.py")
        sys.exit(1)
    
    # Process each user
    for user_id in range(1, 5):
        print(f"\n{'=' * 70}")
        print(f"PROCESSING USER {user_id}")
        print(f"{'=' * 70}")
        
        # Each user has their own expert aligned file (from their specific DTW alignment)
        expert_path = os.path.join(aligned_poses_dir, f"expert_aligned_user{user_id}.npy")
        user_path = os.path.join(aligned_poses_dir, f"user_{user_id}_aligned.npy")
        output_path = os.path.join(script_dir, f"joint_errors_user{user_id}.json")
        
        # Check if user aligned poses exist
        if not os.path.exists(expert_path):
            print(f"  ✗ Expert aligned poses for user {user_id} not found: {expert_path}")
            print(f"    Skipping user {user_id}")
            continue
        
        if not os.path.exists(user_path):
            print(f"  ✗ User {user_id} aligned poses not found: {user_path}")
            print(f"    Skipping user {user_id}")
            continue
        
        print(f"  User {user_id} aligned poses: {user_path}")
        
        try:
            # Load poses
            print(f"\n  [1/6] Loading aligned poses...")
            expert_poses, user_poses = load_aligned_poses(expert_path, user_path)
            T = expert_poses.shape[0]
            print(f"    ✓ Loaded: T={T} frames")
            
            # Compute errors
            print(f"  [2/6] Computing joint errors...")
            errors = compute_joint_errors(expert_poses, user_poses)
            print(f"    ✓ Mean error: {np.mean(errors):.4f}")
            
            # Aggregate joint stats
            print(f"  [3/6] Aggregating joint statistics...")
            joint_stats = aggregate_joint_stats(errors)
            sorted_joints = sorted(joint_stats.items(), key=lambda x: x[1]["mean"], reverse=True)
            print(f"    ✓ Worst joint: {sorted_joints[0][0]} ({sorted_joints[0][1]['mean']:.4f})")
            
            # Aggregate frame stats
            print(f"  [4/6] Aggregating frame statistics...")
            frame_stats = aggregate_frame_stats(errors)
            print(f"    ✓ Computed for {len(frame_stats)} frames")
            
            # Compute phase stats
            print(f"  [5/6] Computing phase statistics...")
            phase_stats = compute_phase_stats(errors)
            print(f"    ✓ Early/Mid/Late phases computed")
            
            # Export frame-wise joint errors
            print(f"  [6/7] Exporting frame-wise joint errors...")
            frame_joint_errors = export_frame_joint_errors(errors)
            print(f"    ✓ Frame-wise errors: {len(frame_joint_errors)} frames")
            
            # Export JSON
            print(f"  [7/7] Exporting JSON...")
            export_json(
                errors,
                joint_stats,
                frame_stats,
                phase_stats,
                frame_joint_errors,  # NEW: include frame-wise errors
                expert_path,
                user_path,
                output_path
            )
            print(f"    ✓ Saved: {output_path}")
            
        except Exception as e:
            print(f"\n  ✗ ERROR processing user {user_id}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Summary
    print("\n" + "=" * 70)
    print("BATCH ERROR COMPUTATION COMPLETE")
    print("=" * 70)
    
    print("\nGenerated files:")
    for user_id in range(1, 5):
        output_path = os.path.join(script_dir, f"joint_errors_user{user_id}.json")
        if os.path.exists(output_path):
            size_kb = os.path.getsize(output_path) / 1024
            print(f"  ✓ joint_errors_user{user_id}.json ({size_kb:.1f} KB)")
        else:
            print(f"  ✗ joint_errors_user{user_id}.json (not generated)")
    
    print("\nThese files are ready for:")
    print("  - Level-3 visualization (error coloring)")
    print("  - Level-4 scoring (similarity metrics)")
    print("  - LLM feedback generation")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
