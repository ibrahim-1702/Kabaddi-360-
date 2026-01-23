"""Quick script to check for NaN values in pose files"""
import numpy as np
import os

print("Checking pose files for NaN values...\n")

pose_files = [
    'review1/level2/poses/expert_pose.npy',
    'review1/level2/poses/user_1_pose.npy',
    'review1/level2/poses/user_2_pose.npy',
    'review1/level2/poses/user_3_pose.npy',
    'review1/level2/poses/user_4_pose.npy',
]

for filepath in pose_files:
    if os.path.exists(filepath):
        poses = np.load(filepath)
        nan_count = np.isnan(poses).sum()
        total = poses.size
        percentage = (nan_count / total * 100) if total > 0 else 0
        
        print(f"{os.path.basename(filepath)}:")
        print(f"  Shape: {poses.shape}")
        print(f"  NaN count: {nan_count} / {total} ({percentage:.2f}%)")
        print()
    else:
        print(f"{filepath}: NOT FOUND\n")
