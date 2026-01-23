#!/usr/bin/env python3
"""
L1.2 — MediaPipe Pose Estimation (MP33) Visualization

Purpose:
    Visualizes MediaPipe Pose extraction of 33 raw keypoints from the 
    YOLO-selected raider.

Process:
    1. Detect and track all persons using YOLO + ByteTrack
    2. Select raider via cumulative motion heuristic (max motion)
    3. For each frame:
       - Crop raider bbox with padding
       - Run MediaPipe Pose (33 landmarks)
       - Store normalized coordinates (lm.x, lm.y)
    4. Visualize skeleton with MediaPipe connections
    5. Save video + pose tensor

Semantic Truth:
    "These are the RAW pose keypoints extracted via MediaPipe"

Input:
    samples/kabaddi_clip.mp4

Outputs:
    review1/level1_pose/outputs/02_mediapipe_mp33.mp4  (visualization)
    review1/level1_pose/outputs/02_mediapipe_mp33.npy  (pose tensor)

Logic Source:
    Ported from level1_pose/raider_pose_extract_2d.py (working implementation)
"""

import cv2
import numpy as np
import sys
import os
from ultralytics import YOLO
import mediapipe as mp


# ---------------- CONFIG ----------------
VIDEO_PATH = "samples/kabaddi_clip.mp4"
OUTPUT_VIDEO = "review1/level1_pose/outputs/02_mediapipe_mp33.mp4"
OUTPUT_NPY = "review1/level1_pose/outputs/02_mediapipe_mp33.npy"
YOLO_MODEL = "yolov8n.pt"
PAD = 40  # padding around raider bbox (EXACT SAME AS SOURCE)
FRAME_JOINTS = 33
# ---------------------------------------


def main():
    """Main entry point for the script."""
    
    # Validate input files exist
    if not os.path.exists(VIDEO_PATH):
        print(f"Error: Input video not found: {VIDEO_PATH}", file=sys.stderr)
        print("Please run this script from the project root directory.", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(YOLO_MODEL):
        print(f"Error: YOLO model not found: {YOLO_MODEL}", file=sys.stderr)
        print("Please ensure yolov8n.pt is in the project root.", file=sys.stderr)
        sys.exit(1)
    
    # Create output directory if needed
    output_dir = os.path.dirname(OUTPUT_VIDEO)
    os.makedirs(output_dir, exist_ok=True)
    
    # ---------------- YOLO (person detection + tracking) ----------------
    print(f"Loading YOLO model: {YOLO_MODEL}")
    yolo = YOLO(YOLO_MODEL)
    
    # ---------------- MediaPipe Pose ----------------
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,  # EXACT SAME AS SOURCE
        min_detection_confidence=0.5,
        min_tracking_confidence=0.7  # EXACT SAME AS SOURCE
    )
    
    # ---------------- Video Input ----------------
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {VIDEO_PATH}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"\nInput video: {VIDEO_PATH}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"Total frames: {total_frames}")
    
    # ---------------- Video Writer ----------------
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (width, height))
    
    if not out.isOpened():
        raise RuntimeError(f"Cannot create output video: {OUTPUT_VIDEO}")
    
    # ---------------- Track History (EXACT SAME AS SOURCE) ----------------
    tracks_history = {}
    
    # ---------------- Pose Storage (EXACT SAME AS SOURCE) ----------------
    all_frames_2d = []  # <-- IMPORTANT
    
    frame_count = 0
    raider_detected_count = 0
    
    print("\nExtracting poses and generating visualization...")
    
    # ---------------- Main Loop (EXACT SAME CONTROL FLOW AS SOURCE) ----------------
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Create visualization frame
        vis_frame = frame.copy()
        
        # ---------------- YOLO TRACKING (EXACT SAME AS SOURCE) ----------------
        results = yolo.track(
            frame,
            persist=True,
            classes=[0],  # person
            tracker="bytetrack.yaml",
            verbose=False
        )
        
        # ---------- DEFAULT FRAME (NaNs) (EXACT SAME AS SOURCE) ----------
        frame_pose_2d = np.full((FRAME_JOINTS, 2), np.nan)
        
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy()
            
            # ---------------- TRACK MOTION (EXACT SAME AS SOURCE) ----------------
            for box, pid in zip(boxes, ids):
                cx = (box[0] + box[2]) / 2
                cy = (box[1] + box[3]) / 2
                tracks_history.setdefault(pid, []).append((cx, cy))
            
            # ---------------- SELECT RAIDER (EXACT SAME AS SOURCE) ----------------
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
                # ---------------- CROP RAIDER (EXACT SAME AS SOURCE) ----------------
                raider_box = None
                for box, pid in zip(boxes, ids):
                    if pid == raider_id:
                        raider_box = box
                        break
                
                if raider_box is not None:
                    raider_detected_count += 1
                    
                    x1, y1, x2, y2 = map(int, raider_box)
                    
                    # EXACT SAME PADDING LOGIC AS SOURCE
                    x1 = max(0, x1 - PAD)
                    y1 = max(0, y1 - PAD)
                    x2 = min(frame.shape[1], x2 + PAD)
                    y2 = min(frame.shape[0], y2 + PAD)
                    
                    raider_crop = frame[y1:y2, x1:x2]
                    
                    # ---------------- POSE ON CROP (EXACT SAME AS SOURCE) ----------------
                    rgb = cv2.cvtColor(raider_crop, cv2.COLOR_BGR2RGB)
                    results_pose = pose.process(rgb)
                    
                    if results_pose.pose_landmarks:
                        # EXACT SAME COORDINATE STORAGE AS SOURCE (normalized)
                        for i, lm in enumerate(results_pose.pose_landmarks.landmark):
                            frame_pose_2d[i] = [lm.x, lm.y]
                        
                        # Draw on crop for visualization
                        mp_drawing.draw_landmarks(
                            raider_crop,
                            results_pose.pose_landmarks,
                            mp_pose.POSE_CONNECTIONS,
                            mp_drawing.DrawingSpec(color=(255, 255, 0), thickness=2, circle_radius=3),
                            mp_drawing.DrawingSpec(color=(255, 255, 0), thickness=2)
                        )
                        
                        # Place crop back into visualization frame
                        vis_frame[y1:y2, x1:x2] = raider_crop
        
        # -------- SAVE FRAME POSE (ALWAYS) (EXACT SAME AS SOURCE) --------
        all_frames_2d.append(frame_pose_2d)
        
        # ===== OVERLAYS (review artifact addition) =====
        timestamp_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        
        # Frame counter (top-left)
        frame_text = f"Frame: {frame_count:04d}"
        cv2.putText(
            vis_frame,
            frame_text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        
        # Timestamp (top-right)
        timestamp_text = f"{timestamp_sec:.2f}s"
        (text_width, _), _ = cv2.getTextSize(
            timestamp_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            2
        )
        cv2.putText(
            vis_frame,
            timestamp_text,
            (width - text_width - 20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        
        # Watermark (center-top)
        watermark_text = "MEDIAPIPE POSE — MP33 (RAW)"
        (wm_width, wm_height), wm_baseline = cv2.getTextSize(
            watermark_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            2
        )
        
        watermark_x = (width - wm_width) // 2
        watermark_y = 40
        
        # Semi-transparent background for watermark
        vis_frame_with_overlay = vis_frame.copy()
        padding_overlay = 10
        overlay = vis_frame_with_overlay.copy()
        cv2.rectangle(
            overlay,
            (watermark_x - padding_overlay, watermark_y - wm_height - padding_overlay),
            (watermark_x + wm_width + padding_overlay, watermark_y + wm_baseline + padding_overlay),
            (0, 0, 0),
            -1
        )
        cv2.addWeighted(overlay, 0.3, vis_frame_with_overlay, 0.7, 0, vis_frame_with_overlay)
        
        # Draw watermark text
        cv2.putText(
            vis_frame_with_overlay,
            watermark_text,
            (watermark_x, watermark_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        
        # Write frame to output video
        out.write(vis_frame_with_overlay)
        
        frame_count += 1
        
        # Progress indicator
        if frame_count % 30 == 0:
            print(f"Processing frame {frame_count}/{total_frames} ({timestamp_sec:.1f}s)")
    
    # Release resources
    cap.release()
    out.release()
    pose.close()
    
    # ---------------- SAVE OUTPUT (EXACT SAME AS SOURCE) ----------------
    all_frames_2d = np.array(all_frames_2d)
    np.save(OUTPUT_NPY, all_frames_2d)
    
    # Verification output
    print(f"\n{'='*60}")
    print(f"OUTPUT SUMMARY")
    print(f"{'='*60}")
    print(f"Video saved: {OUTPUT_VIDEO}")
    print(f"Pose tensor saved: {OUTPUT_NPY}")
    print(f"Total frames processed: {frame_count}")
    print(f"Raider detected in: {raider_detected_count}/{frame_count} frames")
    print(f"Pose tensor shape: {all_frames_2d.shape}")
    print(f"Contains NaN values: {np.isnan(all_frames_2d).any()}")
    
    # Validate output shape
    assert all_frames_2d.shape == (frame_count, FRAME_JOINTS, 2), \
        f"Shape mismatch! Expected ({frame_count}, {FRAME_JOINTS}, 2), got {all_frames_2d.shape}"
    
    print(f"✓ Shape validation passed: {all_frames_2d.shape}")
    print(f"✓ Logic ported from: level1_pose/raider_pose_extract_2d.py")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
