import numpy as np

# Check the cleaned pose file
pose = np.load('review1/level1_pose/outputs/04_coco17_cleaned.npy')
print(f'Shape: {pose.shape}')
print(f'Data type: {pose.dtype}')
print(f'Min values: {pose.min(axis=(0,1))}')
print(f'Max values: {pose.max(axis=(0,1))}')
