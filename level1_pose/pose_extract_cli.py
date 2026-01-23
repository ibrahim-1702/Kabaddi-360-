#!/usr/bin/env python3
"""
CLI wrapper for raider pose extraction
Accepts video input and outputs COCO-17 pose format
"""

import sys
import argparse
import numpy as np
import cv2
from ultralytics import YOLO
import mediapipe as mp
from mp33_to_coco17 import mp33_to_coco17
from level1_cleaning import clean_level1_poses

def extract_pose_from_video(video_path, output_path):
    """Extract pose from video and save as COCO-17 format"""
    
    # YOLO (person detection + tracking)
    yolo = YOLO("yolov8n.pt")
    
    # MediaPipe Pose
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.7
    )
    
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
                    
                    # Pose on crop
                    rgb = cv2.cvtColor(raider_crop, cv2.COLOR_BGR2RGB)
                    results_pose = pose.process(rgb)
                    
                    if results_pose.pose_landmarks:
                        for i, lm in enumerate(results_pose.pose_landmarks.landmark):
                            frame_pose_2d[i] = [lm.x, lm.y]
        
        all_frames_2d.append(frame_pose_2d)
    
    cap.release()
    pose.close()
    
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