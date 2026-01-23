# WORKING — MODIFIED FOR MP33 2D OUTPUT

import cv2
import numpy as np
from ultralytics import YOLO
import mediapipe as mp

# ---------------- CONFIG ----------------
VIDEO_PATH = "samples/kabaddi_clip.mp4"
OUTPUT_NPY_2D = "raider_pose_2d_mp33.npy"
PAD = 40  # padding around raider bbox
FRAME_JOINTS = 33
# ---------------------------------------

# YOLO (person detection + tracking)
yolo = YOLO("yolov8n.pt")

# MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    smooth_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.7
)

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    raise FileNotFoundError("Cannot open video file")

fps = cap.get(cv2.CAP_PROP_FPS)
fps = fps if fps > 0 else 30
delay = int(1000 / fps)

tracks_history = {}
all_frames_2d = []   # <-- IMPORTANT

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # ---------------- YOLO TRACKING ----------------
    results = yolo.track(
        frame,
        persist=True,
        classes=[0],  # person
        tracker="bytetrack.yaml",
        verbose=False
    )

    # ---------- DEFAULT FRAME (NaNs) ----------
    frame_pose_2d = np.full((FRAME_JOINTS, 2), np.nan)

    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.cpu().numpy()

        # ---------------- TRACK MOTION ----------------
        for box, pid in zip(boxes, ids):
            cx = (box[0] + box[2]) / 2
            cy = (box[1] + box[3]) / 2
            tracks_history.setdefault(pid, []).append((cx, cy))

        # ---------------- SELECT RAIDER ----------------
        raider_id = None
        max_motion = 0

        for pid, pts in tracks_history.items():
            if len(pts) < 5:
                continue
            motion = sum(
                np.linalg.norm(np.array(pts[i]) - np.array(pts[i - 1]))
                for i in range(1, len(pts))
            )
            if motion > max_motion:
                max_motion = motion
                raider_id = pid

        if raider_id is not None:
            # ---------------- CROP RAIDER ----------------
            raider_box = None
            for box, pid in zip(boxes, ids):
                if pid == raider_id:
                    raider_box = box
                    break

            if raider_box is not None:
                x1, y1, x2, y2 = map(int, raider_box)

                x1 = max(0, x1 - PAD)
                y1 = max(0, y1 - PAD)
                x2 = min(frame.shape[1], x2 + PAD)
                y2 = min(frame.shape[0], y2 + PAD)

                raider_crop = frame[y1:y2, x1:x2]

                # ---------------- POSE ON CROP ----------------
                rgb = cv2.cvtColor(raider_crop, cv2.COLOR_BGR2RGB)
                results_pose = pose.process(rgb)

                if results_pose.pose_landmarks:
                    for i, lm in enumerate(results_pose.pose_landmarks.landmark):
                        frame_pose_2d[i] = [lm.x, lm.y]

                    mp_drawing.draw_landmarks(
                        raider_crop,
                        results_pose.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS
                    )

                frame[y1:y2, x1:x2] = raider_crop
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # -------- SAVE FRAME POSE (ALWAYS) --------
    all_frames_2d.append(frame_pose_2d)

    cv2.imshow("Raider Pose", frame)
    if cv2.waitKey(delay) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
pose.close()

# ---------------- SAVE OUTPUT ----------------
all_frames_2d = np.array(all_frames_2d)
np.save(OUTPUT_NPY_2D, all_frames_2d)

print("Saved MP33 2D pose:", all_frames_2d.shape)
