#!/usr/bin/env python3
"""
CLI wrapper for raider pose extraction
Accepts video input and outputs COCO-17 pose format

Compatible with MediaPipe >= 0.10.18 (Tasks API)
"""

import sys
import os
import argparse
import numpy as np
import cv2
from pathlib import Path
from ultralytics import YOLO
import mediapipe as mp
from mp33_to_coco17 import mp33_to_coco17
from level1_cleaning import clean_level1_poses

# Path to the PoseLandmarker .task model (downloaded separately)
_SCRIPT_DIR = Path(__file__).resolve().parent
_MODEL_PATH = _SCRIPT_DIR / 'pose_landmarker_heavy.task'


def _create_pose_landmarker():
    """Create a PoseLandmarker using the new Tasks API."""
    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    if not _MODEL_PATH.exists():
        raise FileNotFoundError(
            f"PoseLandmarker model not found at {_MODEL_PATH}\n"
            "Download it with:\n"
            "  curl -L -o pose_landmarker_heavy.task "
            "https://storage.googleapis.com/mediapipe-models/"
            "pose_landmarker/pose_landmarker_heavy/float16/1/"
            "pose_landmarker_heavy.task"
        )

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(_MODEL_PATH)),
        running_mode=VisionRunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_tracking_confidence=0.7,
    )
    return PoseLandmarker.create_from_options(options)


def extract_pose_from_video(video_path, output_path):
    """Extract pose from video and save as COCO-17 format"""

    # YOLO (person detection + tracking)
    yolo = YOLO("yolov8n.pt")

    # MediaPipe Pose (new Tasks API)
    landmarker = _create_pose_landmarker()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {video_path}")

    tracks_history = {}
    all_frames_2d = []
    PAD = 40
    FRAME_JOINTS = 33

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # YOLO tracking
        results = yolo.track(
            frame,
            persist=True,
            classes=[0],  # person
            tracker="bytetrack.yaml",
            verbose=False
        )

        # Default frame (NaNs)
        frame_pose_2d = np.full((FRAME_JOINTS, 2), np.nan)

        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy()

            # Track motion
            for box, pid in zip(boxes, ids):
                cx = (box[0] + box[2]) / 2
                cy = (box[1] + box[3]) / 2
                tracks_history.setdefault(pid, []).append((cx, cy))

            # Select raider (most motion)
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
                # Crop raider
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

                    # Pose on crop (new Tasks API)
                    rgb = cv2.cvtColor(raider_crop, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(
                        image_format=mp.ImageFormat.SRGB, data=rgb
                    )
                    pose_result = landmarker.detect(mp_image)

                    if pose_result.pose_landmarks:
                        landmarks = pose_result.pose_landmarks[0]
                        for i, lm in enumerate(landmarks):
                            frame_pose_2d[i] = [lm.x, lm.y]

        all_frames_2d.append(frame_pose_2d)

    cap.release()
    landmarker.close()

    # Convert MP33 to COCO17
    mp33_poses = np.array(all_frames_2d)
    coco17_poses = mp33_to_coco17(mp33_poses)

    # Apply Level-1 cleaning
    cleaned_poses = clean_level1_poses(coco17_poses)

    # Save output
    np.save(output_path, cleaned_poses)
    print(f"Saved COCO-17 poses: {cleaned_poses.shape}")

def main():
    parser = argparse.ArgumentParser(description='Extract pose from video')
    parser.add_argument('video_path', help='Input video path')
    parser.add_argument('output_path', help='Output .npy file path')

    args = parser.parse_args()

    try:
        extract_pose_from_video(args.video_path, args.output_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()