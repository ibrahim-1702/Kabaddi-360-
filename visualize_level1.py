import numpy as np
import cv2

# ---------------- CONFIG ----------------
POSE_FILE = "raider_pose_level1.npy"
IMG_SIZE = 600
JOINT_RADIUS = 4
# ----------------------------------------

# COCO-17 skeleton connections
COCO_CONNECTIONS = [
    (5, 6),    # shoulders
    (5, 7), (7, 9),      # left arm
    (6, 8), (8, 10),     # right arm
    (11, 12), # hips
    (11, 13), (13, 15),  # left leg
    (12, 14), (14, 16),  # right leg
    (5, 11),  # left torso
    (6, 12),  # right torso
]

# Load Level-1 pose
poses = np.load(POSE_FILE)   # (T, 17, 2)
T = poses.shape[0]

print("Loaded Level-1 poses:", poses.shape)

# Normalize for visualization
scale = IMG_SIZE // 3

for t in range(T):
    frame = np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)

    pose = poses[t]

    # Convert canonical coords → image coords
    pts = []
    for j in range(17):
        if np.any(np.isnan(pose[j])):
            pts.append(None)
            continue

        x = int(pose[j, 0] * scale + IMG_SIZE // 2)
        y = int(pose[j, 1] * scale + IMG_SIZE // 2)
        pts.append((x, y))

        cv2.circle(frame, (x, y), JOINT_RADIUS, (0, 255, 255), -1)

    # Draw skeleton
    for a, b in COCO_CONNECTIONS:
        if pts[a] is not None and pts[b] is not None:
            cv2.line(frame, pts[a], pts[b], (0, 255, 0), 2)

    cv2.putText(
        frame,
        f"Frame {t+1}/{T}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2
    )

    cv2.imshow("Level-1 Pose Visualization", frame)
    if cv2.waitKey(40) & 0xFF == 27:
        break

cv2.destroyAllWindows()
