import numpy as np

# ===== CONFIG =====
INPUT_POSE = "pose_3d.npy"   # change later for user
OUTPUT_POSE = "user_pose_level1.npy"

# COCO17 joint indices mapped from MediaPipe 33
MP33_TO_COCO17 = [
    0,   # nose
    11,  # left_shoulder
    12,  # right_shoulder
    13,  # left_elbow
    14,  # right_elbow
    15,  # left_wrist
    16,  # right_wrist
    23,  # left_hip
    24,  # right_hip
    25,  # left_knee
    26,  # right_knee
    27,  # left_ankle
    28,  # right_ankle
    5,   # left_eye
    2,   # right_eye
    7,   # left_ear
    8    # right_ear
]

def normalize_pose(pose_2d):
    """
    pose_2d: (T, 17, 2)
    """
    # Center on mid-hip
    hips = (pose_2d[:, 7] + pose_2d[:, 8]) / 2
    pose_2d = pose_2d - hips[:, None, :]

    # Scale by torso length
    shoulders = (pose_2d[:, 1] + pose_2d[:, 2]) / 2
    torso_len = np.linalg.norm(shoulders, axis=1).mean()
    pose_2d /= torso_len + 1e-6

    return pose_2d

def main():
    pose_3d = np.load(INPUT_POSE)           # (T, 33, 3)
    pose_2d = pose_3d[:, MP33_TO_COCO17, :2]  # (T, 17, 2)
    pose_norm = normalize_pose(pose_2d)
    np.save(OUTPUT_POSE, pose_norm)

    print(f"Saved Level-1 pose: {OUTPUT_POSE}")
    print("Shape:", pose_norm.shape)

if __name__ == "__main__":
    main()
