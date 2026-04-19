import numpy as np

# MediaPipe Pose (33) → COCO (17) mapping
# Index mapping based on MediaPipe documentation
MP33_TO_COCO17 = {
    0: 0,    # nose
    11: 5,   # left shoulder
    12: 6,   # right shoulder
    13: 7,   # left elbow
    14: 8,   # right elbow
    15: 9,   # left wrist
    16: 10,  # right wrist
    23: 11,  # left hip
    24: 12,  # right hip
    25: 13,  # left knee
    26: 14,  # right knee
    27: 15,  # left ankle
    28: 16   # right ankle
}

def mp33_to_coco17(mp33_poses):
    """
    Input : (T, 33, 2)
    Output: (T, 17, 2)
    """
    T = mp33_poses.shape[0]
    coco = np.full((T, 17, 2), np.nan)

    for mp_i, coco_i in MP33_TO_COCO17.items():
        coco[:, coco_i] = mp33_poses[:, mp_i]

    return coco
