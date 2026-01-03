import numpy as np
from mp33_to_coco17 import mp33_to_coco17
from level1_cleaning import clean_level1_poses

# ---------------------------------------
# Load MediaPipe 33-joint 2D pose
# ---------------------------------------
mp33 = np.load("raider_pose_2d_mp33.npy")
print("MP33 input shape:", mp33.shape)

# ---------------------------------------
# Convert MP33 → COCO17
# ---------------------------------------
coco17 = mp33_to_coco17(mp33)
print("COCO17 shape:", coco17.shape)

# ---------------------------------------
# Run LEVEL-1 cleaning
# ---------------------------------------
poses_level1 = clean_level1_poses(coco17)

# ---------------------------------------
# Save output
# ---------------------------------------
np.save("raider_pose_level1.npy", poses_level1)
print("Saved Level-1 poses:", poses_level1.shape)
