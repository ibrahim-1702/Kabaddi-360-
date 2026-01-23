from ultralytics import YOLO
import cv2
import numpy as np

model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture("samples/kabaddi_clip.mp4")

# --------- VIDEO WRITER (IMPORTANT) ---------
fps = cap.get(cv2.CAP_PROP_FPS)
fps = fps if fps > 0 else 30
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

out = cv2.VideoWriter(
    "masked_raider.mp4",
    cv2.VideoWriter_fourcc(*"mp4v"),
    fps,
    (width, height)
)

tracks_history = {}

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model.track(
        frame,
        persist=True,
        classes=[0],
        tracker="bytetrack.yaml"
    )

    masked = frame.copy()

    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.cpu().numpy()

        # Store motion history
        for box, pid in zip(boxes, ids):
            cx = (box[0] + box[2]) / 2
            cy = (box[1] + box[3]) / 2
            tracks_history.setdefault(pid, []).append((cx, cy))

        # Raider selection
        raider_id = None
        max_motion = 0

        for pid, pts in tracks_history.items():
            if len(pts) < 5:
                continue
            motion = sum(
                np.linalg.norm(np.array(pts[i]) - np.array(pts[i-1]))
                for i in range(1, len(pts))
            )
            if motion > max_motion:
                max_motion = motion
                raider_id = pid

        # Blur defenders
        for box, pid in zip(boxes, ids):
            if pid != raider_id:
                x1, y1, x2, y2 = map(int, box)
                x1 = max(0, x1); y1 = max(0, y1)
                x2 = min(width, x2); y2 = min(height, y2)

                if x2 > x1 and y2 > y1:
                    masked[y1:y2, x1:x2] = cv2.GaussianBlur(
                        masked[y1:y2, x1:x2],
                        (51, 51),
                        0
                    )

    # --------- SAVE FRAME ---------
    out.write(masked)

    cv2.imshow("Masked Frame", masked)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
out.release()
cv2.destroyAllWindows()

print("Masked video saved as masked_raider.mp4")
