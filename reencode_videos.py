"""
Re-encode Review1 Videos for Browser Compatibility
Uses OpenCV to convert videos to H.264 codec (browser-compatible)
"""

import cv2
import os
from pathlib import Path

def reencode_video(input_path, output_path):
    """Re-encode video with H.264 codec"""
    print(f"  Processing: {input_path.name}")
    
    # Open input video
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        print(f"  ❌ ERROR: Could not open {input_path.name}")
        return False
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"    {width}x{height} @ {fps:.2f} FPS, {total_frames} frames")
    
    # Try multiple codecs until one works
    codecs_to_try = [
        ('mp4v', 'MPEG-4'),
        ('XVID', 'Xvid'),
        ('MJPG', 'Motion JPEG'),
    ]
    
    out = None
    used_codec = None
    
    for fourcc_code, codec_name in codecs_to_try:
        try:
            fourcc = cv2.VideoWriter_fourcc(*fourcc_code)
            out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            
            if out.isOpened():
                used_codec = codec_name
                print(f"    Using codec: {codec_name}")
                break
            else:
                out.release()
                out = None
        except:
            continue
    
    if out is None or not out.isOpened():
        print(f"  ❌ ERROR: Could not create output file")
        cap.release()
        return False
    
    # Process frames
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        out.write(frame)
        frame_count += 1
        
        # Progress indicator
        if frame_count % 30 == 0:
            progress = (frame_count / total_frames) * 100
            print(f"    Progress: {progress:.1f}%", end='\r')
    
    print(f"    Progress: 100.0%")
    
    # Cleanup
    cap.release()
    out.release()
    
    print(f"  ✓ Successfully re-encoded ({frame_count} frames)")
    return True

def main():
    print("=" * 70)
    print("Re-encoding Review1 Videos for Browser Compatibility")
    print("=" * 70)
    print()
    
    base_dir = Path(__file__).parent
    
    # Define all video locations
    videos_to_process = [
        # Level 1 (5 videos)
        base_dir / "review1/level1_pose/outputs/00_raw_reference.mp4",
        base_dir / "review1/level1_pose/outputs/01_yolo_tracking.mp4",
        base_dir / "review1/level1_pose/outputs/02_mediapipe_mp33.mp4",
        base_dir / "review1/level1_pose/outputs/03_coco17_raw.mp4",
        base_dir / "review1/level1_pose/outputs/04_coco17_cleaned.mp4",
        
        # Level 2 (4 videos)
        base_dir / "review1/level2/Outputs/output_temporal_alignment_user1.mp4",
        base_dir / "review1/level2/Outputs/output_temporal_alignment_user2.mp4",
        base_dir / "review1/level2/Outputs/output_temporal_alignment_user3.mp4",
        base_dir / "review1/level2/Outputs/output_temporal_alignment_user4.mp4",
        
        # Level 3 (1 video)
        base_dir / "review1/visualization/level3/output_error_localization.mp4",
        
        # Level 4 (1 video)
        base_dir / "review1/visualization/level4/output_scoring_summary.mp4",
    ]
    
    total = len(videos_to_process)
    succeeded = 0
    failed = 0
    
    for idx, video_path in enumerate(videos_to_process, 1):
        print(f"\n[{idx}/{total}] {video_path.relative_to(base_dir)}")
        
        if not video_path.exists():
            print(f"  ⚠️  File not found, skipping...")
            failed += 1
            continue
        
        # Create backup
        backup_path = video_path.with_suffix('.mp4.original')
        if backup_path.exists():
            print(f"  ℹ️  Backup already exists, skipping...")
            continue
        
        # Create temporary output file
        temp_path = video_path.with_suffix('.mp4.temp')
        
        # Re-encode
        if reencode_video(video_path, temp_path):
            # Replace original with re-encoded version
            video_path.rename(backup_path)
            temp_path.rename(video_path)
            succeeded += 1
        else:
            # Cleanup failed attempt
            if temp_path.exists():
                temp_path.unlink()
            failed += 1
    
    print("\n" + "=" * 70)
    print("Conversion Complete!")
    print("=" * 70)
    print(f"✓ Succeeded: {succeeded}/{total}")
    print(f"✗ Failed: {failed}/{total}")
    
    if succeeded > 0:
        print("\nOriginal files backed up with .original extension")
        print("You can now refresh the Gallery page - videos should play!")
    
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
