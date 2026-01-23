#BUGGED
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

pose_3d = np.load("pose_3d.npy")

# Pick one frame
frame = pose_3d[20]

# MediaPipe pose connections (important)
POSE_CONNECTIONS = [
    (11,13),(13,15),(12,14),(14,16),
    (11,12),(11,23),(12,24),(23,24),
    (23,25),(25,27),(24,26),(26,28)
]

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

x = frame[:, 0]
y = frame[:, 1]
z = frame[:, 2]

ax.scatter(x, y, z)

for a, b in POSE_CONNECTIONS:
    ax.plot(
        [x[a], x[b]],
        [y[a], y[b]],
        [z[a], z[b]],
    )

ax.set_title("3D Pose Skeleton")
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")

plt.show()
