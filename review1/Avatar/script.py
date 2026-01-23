import numpy as np
import json
EXPERT_POSE = "04_coco17_cleaned.npy"
pose = np.load(EXPERT_POSE)   # (77,17,3)

frames = []
for f in range(pose.shape[0]):
    frame = {}
    for j in range(17):
        frame[str(j)] = pose[f, j].tolist()
    frames.append(frame)

with open("pose.json", "w") as f:
    json.dump(frames, f)
