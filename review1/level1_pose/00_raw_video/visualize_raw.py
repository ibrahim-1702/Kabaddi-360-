#!/usr/bin/env python3
"""
L1.0 — Raw Video Reference Visualization

Purpose:
    Creates a reference copy of the raw input video with informational overlays.
    This serves as the baseline for comparison with processed stages.

Overlays:
    - Frame counter (top-left)
    - Timestamp in seconds (top-right)
    - Watermark: "RAW VIDEO — NO PROCESSING" (center-top)

Input:
    samples/kabaddi_clip.mp4

Output:
    review1/level1_pose/outputs/00_raw_reference.mp4
"""

import cv2
import sys
import os

def visualize_raw_video(input_path, output_path):
    """
    Create raw video reference with informational overlays.
    
    Args:
        input_path: Path to input video file
        output_path: Path to output video file
    """
    
    # Open input video
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video file: {input_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0  # fallback
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Input video: {input_path}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps}")
    print(f"Total frames: {total_frames}")
    
    # Initialize video writer
    # Use mp4v codec for compatibility
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        raise RuntimeError(f"Cannot create output video: {output_path}")
    
    frame_count = 0
    
    # Process each frame
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Calculate timestamp in seconds
        timestamp_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

        
        # ===== OVERLAY 1: Frame counter (top-left) =====
        frame_text = f"Frame: {frame_count:04d}"
        cv2.putText(
            frame,
            frame_text,
            (20, 40),  # Position: top-left with margin
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,  # Font scale
            (255, 255, 255),  # White color (BGR)
            2,  # Thickness
            cv2.LINE_AA  # Anti-aliasing for smooth text
        )
        
        # ===== OVERLAY 2: Timestamp (top-right) =====
        timestamp_text = f"{timestamp_sec:.2f}s"
        
        # Calculate text width to right-align
        (text_width, text_height), baseline = cv2.getTextSize(
            timestamp_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            2
        )
        
        cv2.putText(
            frame,
            timestamp_text,
            (width - text_width - 20, 40),  # Position: top-right with margin
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        
        # ===== OVERLAY 3: Watermark (center-top) =====
        watermark_text = "RAW VIDEO - NO PROCESSING"
        
        # Calculate text width to center-align
        (wm_width, wm_height), wm_baseline = cv2.getTextSize(
            watermark_text,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,  # Slightly smaller font for watermark
            2
        )
        
        watermark_x = (width - wm_width) // 2
        watermark_y = 40
        
        # Add semi-transparent background for watermark readability
        # Create a rectangle behind the text
       # Create a copy for overlay rendering
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
        
        # Progress indicator (every 30 frames = ~1 second at 30fps)
        if frame_count % 30 == 0:
            print(f"Processing frame {frame_count}/{total_frames} ({timestamp_sec:.1f}s)")
    
    # Release resources
    cap.release()
    out.release()
    
    print(f"\nOutput video saved: {output_path}")
    print(f"Total frames processed: {frame_count}")


def main():
    """Main entry point for the script."""
    
    # Define input and output paths relative to project root
    # Assuming script is run from project root: kabaddi_trainer/
    input_video = "samples/kabaddi_clip.mp4"
    output_video = "review1/level1_pose/outputs/00_raw_reference.mp4"
    
    # Validate input file exists
    if not os.path.exists(input_video):
        print(f"Error: Input video not found: {input_video}", file=sys.stderr)
        print("Please run this script from the project root directory.", file=sys.stderr)
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_video)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        visualize_raw_video(input_video, output_video)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
