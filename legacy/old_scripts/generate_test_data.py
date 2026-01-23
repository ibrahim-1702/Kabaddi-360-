#!/usr/bin/env python3
"""
Test data generator for Level-3 joint error computation.

Creates synthetic DTW-aligned expert and user poses for testing.
"""

import numpy as np
import os

# Create test directory
test_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(test_dir, exist_ok=True)

# Test parameters
T = 99  # Number of frames (divisible by 3 for phase segmentation)
num_joints = 17
num_coords = 2

print("=" * 70)
print("GENERATING TEST DATA FOR LEVEL-3")
print("=" * 70)

# Generate expert poses (smooth, normalized trajectory)
print("\n[1/3] Generating expert poses...")
expert_poses = np.zeros((T, num_joints, num_coords))

for t in range(T):
    for j in range(num_joints):
        # Create smooth sinusoidal movement pattern
        phase = 2 * np.pi * t / T
        expert_poses[t, j, 0] = 0.5 + 0.2 * np.sin(phase + j * 0.1)  # x
        expert_poses[t, j, 1] = 0.5 + 0.2 * np.cos(phase + j * 0.1)  # y

expert_path = os.path.join(test_dir, "test_expert_aligned.npy")
np.save(expert_path, expert_poses)
print(f"  ✓ Saved: {expert_path}")
print(f"    Shape: {expert_poses.shape}")

# Generate user poses (expert + controlled noise)
print("\n[2/3] Generating user poses with errors...")
user_poses = expert_poses.copy()

# Add different error patterns to different joints and phases
np.random.seed(42)  # Deterministic

# Early phase: larger errors (learning)
early_end = T // 3
user_poses[0:early_end, :, :] += np.random.randn(early_end, num_joints, num_coords) * 0.08

# Mid phase: moderate errors
mid_end = 2 * T // 3
user_poses[early_end:mid_end, :, :] += np.random.randn(mid_end - early_end, num_joints, num_coords) * 0.05

# Late phase: increasing errors (fatigue)
user_poses[mid_end:, :, :] += np.random.randn(T - mid_end, num_joints, num_coords) * 0.10

# Add specific large error to left_knee (joint 13) in late phase
user_poses[mid_end:, 13, :] += 0.15

user_path = os.path.join(test_dir, "test_user_aligned.npy")
np.save(user_path, user_poses)
print(f"  ✓ Saved: {user_path}")
print(f"    Shape: {user_poses.shape}")

# Verify data
print("\n[3/3] Verifying test data...")
loaded_expert = np.load(expert_path)
loaded_user = np.load(user_path)

assert loaded_expert.shape == (T, num_joints, num_coords), "Expert shape mismatch"
assert loaded_user.shape == (T, num_joints, num_coords), "User shape mismatch"
assert loaded_expert.shape == loaded_user.shape, "Shape mismatch between expert and user"

print(f"  ✓ Shapes validated")
print(f"  ✓ Sequences aligned (T={T} frames)")

print("\n" + "=" * 70)
print("TEST DATA GENERATION COMPLETE")
print("=" * 70)
print(f"\nGenerated files:")
print(f"  - test_expert_aligned.npy")
print(f"  - test_user_aligned.npy")
print(f"\nUsage:")
print(f"  python compute_joint_errors.py test_expert_aligned.npy test_user_aligned.npy")
print("=" * 70)
