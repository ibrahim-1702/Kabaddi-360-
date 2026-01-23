#!/usr/bin/env python3
"""
L1.1 — YOLO Person Detection & Tracking Visualization

Purpose:
    Visualizes YOLO-based person detection and tracking to demonstrate
    raider selection from a multi-person scene.

Process:
    1. Detect all persons in each frame (YOLO class 0)
    2. Track persons across frames using ByteTrack
    3. Compute cumulative motion per track (bbox center displacement)
    4. Select raider = track with maximum cumulative motion
    5. Visualize all detections with track IDs

Semantic Truth:
    "This is WHO we're analyzing (raider isolated via motion heuristic)"

Input:
    samples/kabaddi_clip.mp4

Output:
    review1/level1_pose/outputs/01_yolo_tracking.mp4
"""

import cv2
import numpy as np
import sys
import os
from ultralytics import YOLO


def visualize_yolo_tracking(input_path, output_path, model_path):
    """
    Create YOLO tracking visualization with raider selection.
    
    Args:
        input_path: Path to input video file
        output_path: Path to output video file
        model_path: Path to YOLO model weights
    """
    
    # Initialize YOLO model
    print(f"Loading YOLO model: {model_path}")
    yolo = YOLO(model_path)
    
    # Open input video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {input_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Input video: {input_path}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"Total frames: {total_frames}")
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        raise RuntimeError(f"Cannot create output video: {output_path}")
    
    # Track history: stores bbox centers for each track ID
    # Format: {track_id: [(cx, cy), (cx, cy), ...]}
    tracks_history = {}
    
    # Cumulative motion per track
    # Format: {track_id: total_motion_distance}
    tracks_motion = {}
    
    frame_count = 0
    raider_id = None  # Will be determined after sufficient tracking
    
    # Minimum frames before selecting raider
    # (ensures we have enough motion data for reliable selection)
    MIN_FRAMES_FOR_SELECTION = 5
    
    # Process each frame
    yolo.tracker = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Run YOLO tracking
        # persist=True maintains track IDs across frames
        # classes=[0] filters for persons only
        # verbose=False suppresses per-frame output
        results = yolo.track(
            frame,
            persist=True,
            classes=[0],  # person class
            tracker="bytetrack.yaml",
            verbose=False
        )
        
        # Extract detections
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()  # [x1, y1, x2, y2]
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            
            # Update track history with bbox centers
            for box, tid in zip(boxes, track_ids):
                x1, y1, x2, y2 = box
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                
                # Initialize track if first detection
                if tid not in tracks_history:
                    tracks_history[tid] = []
                    tracks_motion[tid] = 0.0
                
                # Append center to history
                tracks_history[tid].append((cx, cy))
                
                # Compute motion (frame-to-frame displacement)
                if len(tracks_history[tid]) >= 2:
                    prev_cx, prev_cy = tracks_history[tid][-2]
                    curr_cx, curr_cy = tracks_history[tid][-1]
                    
                    # Euclidean distance between consecutive centers
                    displacement = np.sqrt((curr_cx - prev_cx)**2 + (curr_cy - prev_cy)**2)
                    tracks_motion[tid] += displacement
            
            # Select raider after minimum tracking period
            # Raider = track with maximum cumulative motion
            # This heuristic assumes the active player moves most
            if frame_count >= MIN_FRAMES_FOR_SELECTION:
                # Find track with maximum motion (must have at least MIN_FRAMES_FOR_SELECTION points)
                eligible_tracks = {
                    tid: motion 
                    for tid, motion in tracks_motion.items() 
                    if len(tracks_history[tid]) >= MIN_FRAMES_FOR_SELECTION
                }
                
                if eligible_tracks:
                    raider_id = max(eligible_tracks, key=eligible_tracks.get)
                    print(f"Raider selected: ID={raider_id}, Motion={tracks_motion[raider_id]:.1f}")
            
            # Draw bounding boxes and labels
            for box, tid in zip(boxes, track_ids):
                x1, y1, x2, y2 = map(int, box)
                
                # Determine if this is the selected raider
                is_raider = (tid == raider_id)
                
                # Set visualization parameters based on raider status
                if is_raider:
                    box_color = (0, 255, 0)  # GREEN (BGR)
                    box_thickness = 3
                    label = f"ID:{tid}  [RAIDER]"
                    text_color = (0, 255, 0)
                else:
                    box_color = (128, 128, 128)  # GRAY (BGR)
                    box_thickness = 1
                    label = f"ID:{tid}"
                    text_color = (200, 200, 200)
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, box_thickness)
                
                # Draw label with background
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                label_w, label_h = label_size
                
                # Label background (semi-transparent)
                overlay = frame.copy()
                cv2.rectangle(
                    overlay,
                    (x1, y1 - label_h - 10),
                    (x1 + label_w + 10, y1),
                    (0, 0, 0),
                    -1
                )
                cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
                
                # Label text
                cv2.putText(
                    frame,
                    label,
                    (x1 + 5, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    text_color,
                    2,
                    cv2.LINE_AA
                )
                
                # Optionally show motion score for raider
                if is_raider and tid in tracks_motion:
                    motion_text = f"motion: {tracks_motion[tid]:.1f}"
                    cv2.putText(
                        frame,
                        motion_text,
                        (x1, y2 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        1,
                        cv2.LINE_AA
                    )
        
        # ===== OVERLAYS (same as L1.0) =====
        
        timestamp_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        
        # Frame counter (top-left)
        frame_text = f"Frame: {frame_count:04d}"
        cv2.putText(
            frame,
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
            frame,
            timestamp_text,
            (width - text_width - 20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        
        # Watermark (center-top)
        watermark_text = "YOLO PERSON TRACKING - RAIDER SELECTION"
        (wm_width, wm_height), wm_baseline = cv2.getTextSize(
            watermark_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            2
        )
        
        watermark_x = (width - wm_width) // 2
        watermark_y = 40
        
        # Semi-transparent background for watermark
        # Create a copy for overlay rendering (avoid side effects)
        frame_with_overlay = frame.copy()

        # Add semi-transparent background for watermark readability
        padding = 10
        overlay = frame_with_overlay.copy()
        cv2.rectangle(
            overlay,
            (watermark_x - padding, watermark_y - wm_height - padding),
            (watermark_x + wm_width + padding, watermark_y + wm_baseline + padding),
            (0, 0, 0),
            -1
        )

        # Blend overlay
        cv2.addWeighted(overlay, 0.3, frame_with_overlay, 0.7, 0, frame_with_overlay)

        # Draw watermark text
        cv2.putText(
            frame_with_overlay,
            watermark_text,
            (watermark_x, watermark_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        # Write final frame
        out.write(frame_with_overlay)

        
        frame_count += 1
        
        # Progress indicator
        if frame_count % 30 == 0:
            print(f"Processing frame {frame_count}/{total_frames} ({timestamp_sec:.1f}s)")
    
    # Release resources
    cap.release()
    out.release()
    
    print(f"\nOutput video saved: {output_path}")
    print(f"Total frames processed: {frame_count}")
    print(f"Total tracked persons: {len(tracks_history)}")
    if raider_id is not None:
        print(f"Selected raider: ID={raider_id}, Total motion={tracks_motion[raider_id]:.1f}")


def main():
    """Main entry point for the script."""
    
    # Hardcoded paths (review artifact convention)
    input_video = "samples/kabaddi_clip.mp4"
    output_video = "review1/level1_pose/outputs/01_yolo_tracking.mp4"
    yolo_model = "yolov8n.pt"
    
    # Validate input files exist
    if not os.path.exists(input_video):
        print(f"Error: Input video not found: {input_video}", file=sys.stderr)
        print("Please run this script from the project root directory.", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(yolo_model):
        print(f"Error: YOLO model not found: {yolo_model}", file=sys.stderr)
        print("Please ensure yolov8n.pt is in the project root.", file=sys.stderr)
        sys.exit(1)
    
    # Create output directory if needed
    output_dir = os.path.dirname(output_video)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        visualize_yolo_tracking(input_video, output_video, yolo_model)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
