#!/usr/bin/env python3
"""
Simple usage example for Level-2 Temporal Alignment
"""

import numpy as np
from temporal_alignment import temporal_alignment, get_alignment_score

def demo_temporal_alignment():
    """Demonstrate temporal alignment with existing pose files."""
    
    # Load Level-1 cleaned poses
    print("Loading Level-1 cleaned poses...")
    user_poses = np.load("user_pose_level1.npy")      # (T_user, 17, 2)
    ghost_poses = np.load("raider_pose_level1.npy")   # (T_ghost, 17, 2)
    
    print(f"User poses shape: {user_poses.shape}")
    print(f"Ghost poses shape: {ghost_poses.shape}")
    
    # Perform temporal alignment
    print("\nPerforming temporal alignment...")
    user_indices, ghost_indices = temporal_alignment(user_poses, ghost_poses)
    
    print(f"Alignment path length: {len(user_indices)}")
    print(f"User frame range: {min(user_indices)} - {max(user_indices)}")
    print(f"Ghost frame range: {min(ghost_indices)} - {max(ghost_indices)}")
    
    # Extract aligned sequences
    aligned_user = user_poses[user_indices]
    aligned_ghost = ghost_poses[ghost_indices]
    
    print(f"Aligned user shape: {aligned_user.shape}")
    print(f"Aligned ghost shape: {aligned_ghost.shape}")
    
    # Optional: compute alignment quality score
    alignment_score = get_alignment_score(user_poses, ghost_poses)
    print(f"Alignment quality score: {alignment_score:.3f}")
    
    print("\n[SUCCESS] Temporal alignment complete")
    return aligned_user, aligned_ghost

if __name__ == "__main__":
    demo_temporal_alignment()