#!/usr/bin/env python3
"""
L1.3 — MP33 → COCO-17 Conversion with Raider Visualization

Purpose:
    Converts MediaPipe MP33 (33 joints) to COCO-17 (17 joints) format,
    visualizing the COCO-17 skeleton overlaid on the YOLO-selected raider.

Process:
    1. Run YOLO tracking to select raider (same as L1.2)
    2. Run MediaPipe Pose on raider crop (same as L1.2)
    3. Convert MP33 landmarks → COCO-17 joints
    4. Visualize COCO-17 skeleton (RED) on raider
    5. Save COCO-17 pose tensor and video

Semantic Truth:
    "These are the COCO-17 keypoints derived from MediaPipe MP33"

Input:
    samples/kabaddi_clip.mp4

Outputs:
    review1/level1_pose/outputs/03_coco17_raw.mp4  (visualization)
    review1/level1_pose/outputs/03_coco17_raw.npy  (T, 17, 2) pixel coordinates

Logic Source:
    Combines raider-locking from L1.2 + COCO-17 conversion
"""

import cv2
import numpy as np
import sys
import os
from ultralytics import YOLO
import mediapipe as mp


# ---------------- CONFIG ----------------
VIDEO_PATH = "samples/kabaddi_clip.mp4"
OUTPUT_VIDEO = "review1/level1_pose/outputs/03_coco17_raw.mp4"
OUTPUT_NPY = "review1/level1_pose/outputs/03_coco17_raw.npy"
YOLO_MODEL = "yolov8n.pt"
PAD = 40  # padding around raider bbox (SAME AS L1.2)
# ---------------------------------------

# MediaPipe to COCO-17 joint mapping
MP_TO_COCO_MAPPING = {
    0: 0,   # nose
    1: 2,   # left_eye
    2: 5,   # right_eye
    3: 7,   # left_ear
    4: 8,   # right_ear
    5: 11,  # left_shoulder
    6: 12,  # right_shoulder
    7: 13,  # left_elbow
    8: 14,  # right_elbow
    9: 15,  # left_wrist
    10: 16, # right_wrist
    11: 23, # left_hip
    12: 24, # right_hip
    13: 25, # left_knee
    14: 26, # right_knee
    15: 27, # left_ankle
    16: 28, # right_ankle
}

# COCO-17 skeleton connections
COCO_CONNECTIONS = [
    (5, 6),                    # shoulders
    (5, 7), (7, 9),           # left arm
    (6, 8), (8, 10),          # right arm
    (11, 12),                 # hips
    (11, 13), (13, 15),       # left leg
    (12, 14), (14, 16),       # right leg
    (5, 11),                  # left torso
    (6, 12),                  # right torso
]


def convert_mp33_to_coco17(mp33_landmarks, bbox_x1, bbox_y1, bbox_width, bbox_height):
    """
    Convert MediaPipe MP33 landmarks to COCO-17 pixel coordinates.
    
    Args:
        mp33_landmarks: MediaPipe pose landmarks (33 joints)
        bbox_x1, bbox_y1: Top-left corner of raider bbox
        bbox_width, bbox_height: Size of raider bbox
        
    Returns:
        coco17_pose: numpy array (17, 2) with pixel coordinates or NaN
    """
    coco17_pose = np.full((17, 2), np.nan, dtype=np.float32)
    
    for coco_idx in range(17):
        mp_idx = MP_TO_COCO_MAPPING[coco_idx]
        lm = mp33_landmarks[mp_idx]
        
        # Convert normalized coordinates to pixel space if visible
        if lm.visibility >= 0.5:
            x_px = bbox_x1 + lm.x * bbox_width
            y_px = bbox_y1 + lm.y * bbox_height
            coco17_pose[coco_idx] = [x_px, y_px]
        # else: remains NaN
    
    return coco17_pose


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
    
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,  # SAME AS L1.2
        min_detection_confidence=0.5,
        min_tracking_confidence=0.7
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
    
    # ---------------- Track History (SAME AS L1.2) ----------------
    tracks_history = {}
    
    # ---------------- COCO-17 Pose Storage ----------------
    all_coco17_poses = []
    
    frame_count = 0
    raider_detected_count = 0
    
    print("\nExtracting COCO-17 poses and generating visualization...")
    
    # ---------------- Main Loop ----------------
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Create visualization frame
        vis_frame = frame.copy()
        
        # ---------------- YOLO TRACKING (SAME AS L1.2) ----------------
        results = yolo.track(
            frame,
            persist=True,
            classes=[0],  # person
            tracker="bytetrack.yaml",
            verbose=False
        )
        
        # ---------- DEFAULT FRAME (NaNs) ----------
        frame_coco17 = np.full((17, 2), np.nan, dtype=np.float32)
        
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy()
            
            # ---------------- TRACK MOTION (SAME AS L1.2) ----------------
            for box, pid in zip(boxes, ids):
                cx = (box[0] + box[2]) / 2
                cy = (box[1] + box[3]) / 2
                tracks_history.setdefault(pid, []).append((cx, cy))
            
            # ---------------- SELECT RAIDER (SAME AS L1.2) ----------------
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
                # ---------------- CROP RAIDER (SAME AS L1.2) ----------------
                raider_box = None
                for box, pid in zip(boxes, ids):
                    if pid == raider_id:
                        raider_box = box
                        break
                
                if raider_box is not None:
                    raider_detected_count += 1
                    
                    x1, y1, x2, y2 = map(int, raider_box)
                    
                    # SAME PADDING LOGIC AS L1.2
                    x1 = max(0, x1 - PAD)
                    y1 = max(0, y1 - PAD)
                    x2 = min(frame.shape[1], x2 + PAD)
                    y2 = min(frame.shape[0], y2 + PAD)
                    
                    bbox_width = x2 - x1
                    bbox_height = y2 - y1
                    
                    raider_crop = frame[y1:y2, x1:x2]
                    
                    # ---------------- POSE ON CROP (SAME AS L1.2) ----------------
                    rgb = cv2.cvtColor(raider_crop, cv2.COLOR_BGR2RGB)
                    results_pose = pose.process(rgb)
                    
                    if results_pose.pose_landmarks:
                        # ===== NEW: Convert MP33 → COCO-17 =====
                        frame_coco17 = convert_mp33_to_coco17(
                            results_pose.pose_landmarks.landmark,
                            x1, y1, bbox_width, bbox_height
                        )
                        
                        # ===== Visualize COCO-17 skeleton (RED) =====
                        # Draw connections
                        for connection in COCO_CONNECTIONS:
                            start_idx, end_idx = connection
                            start_point = frame_coco17[start_idx]
                            end_point = frame_coco17[end_idx]
                            
                            if not (np.isnan(start_point).any() or np.isnan(end_point).any()):
                                cv2.line(
                                    vis_frame,
                                    (int(start_point[0]), int(start_point[1])),
                                    (int(end_point[0]), int(end_point[1])),
                                    (0, 0, 255),  # RED (BGR)
                                    2,
                                    cv2.LINE_AA
                                )
                        
                        # Draw joints
                        for i in range(17):
                            point = frame_coco17[i]
                            if not np.isnan(point).any():
                                cv2.circle(
                                    vis_frame,
                                    (int(point[0]), int(point[1])),
                                    5,
                                    (0, 0, 255),  # RED (BGR)
                                    -1,
                                    cv2.LINE_AA
                                )
        
        # -------- SAVE FRAME POSE (ALWAYS) --------
        all_coco17_poses.append(frame_coco17)
        
        # ===== OVERLAYS (review artifact conventions) =====
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
        watermark_text = "COCO-17 (RAW) — NO CLEANING"
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
    
    # ---------------- SAVE OUTPUT ----------------
    all_coco17_poses = np.array(all_coco17_poses)
    np.save(OUTPUT_NPY, all_coco17_poses)
    
    # Verification output
    print(f"\n{'='*60}")
    print(f"OUTPUT SUMMARY")
    print(f"{'='*60}")
    print(f"Video saved: {OUTPUT_VIDEO}")
    print(f"Pose tensor saved: {OUTPUT_NPY}")
    print(f"Total frames processed: {frame_count}")
    print(f"Raider detected in: {raider_detected_count}/{frame_count} frames")
    print(f"COCO-17 tensor shape: {all_coco17_poses.shape}")
    print(f"Contains NaN values: {np.isnan(all_coco17_poses).any()}")
    
    # Validate output shape
    assert all_coco17_poses.shape == (frame_count, 17, 2), \
        f"Shape mismatch! Expected ({frame_count}, 17, 2), got {all_coco17_poses.shape}"
    
    print(f"✓ Shape validation passed: {all_coco17_poses.shape}")
    print(f"✓ Logic: L1.2 raider-locking + MP33→COCO-17 conversion")
    print(f"✓ Coordinates: Pixel space ({width}x{height})")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
