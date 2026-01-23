import numpy as np
from level1_cleaning import clean_level1_poses

# ------------------------------------
# Fake input pose data (simulate MediaPipe)
# ------------------------------------

T = 120     # frames
J = 17      # joints

np.random.seed(42)
poses_raw = np.random.rand(T, J, 2) * 500  # pixel-like values

# Inject noise & missing data
poses_raw[30:35, 5] = 0
poses_raw[60] *= 8

# ------------------------------------
# Run Level 1
# ------------------------------------

poses_clean = clean_level1_poses(poses_raw)

print("Input shape :", poses_raw.shape)
print("Output shape:", poses_clean.shape)

print("Sample frame (clean):")
print(poses_clean[10])
