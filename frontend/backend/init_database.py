"""
Database Initialization Script
Creates initial expert pose "The Bonus" from samples/kabaddi_clip.mp4
"""

import json
import shutil
from pathlib import Path
import cv2

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
SAMPLES_DIR = BASE_DIR / 'samples'
EXPERT_FOLDER = BASE_DIR / 'frontend' / 'backend' / 'data' / 'expert_poses'
DB_FOLDER = BASE_DIR / 'frontend' / 'backend' / 'data'

# Create directories
EXPERT_FOLDER.mkdir(parents=True, exist_ok=True)

# Expert pose ID (fixed for "The Bonus")
POSE_ID = "the-bonus-001"

def generate_thumbnail(video_path, output_path):
    """Generate thumbnail from video first frame"""
    try:
        cap = cv2.VideoCapture(str(video_path))
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(str(output_path), frame)
            return True
        return False
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return False

def get_video_duration(video_path):
    """Get video duration in seconds"""
    try:
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        
        if fps > 0:
            duration = frame_count / fps
            return f"{int(duration)}s"
        return "N/A"
    except:
        return "N/A"

def initialize_database():
    """Initialize database with 'The Bonus' expert pose"""
    
    print("=" * 70)
    print("Initializing Expert Poses Database")
    print("=" * 70)
    
    # Source video
    source_video = SAMPLES_DIR / 'kabaddi_clip.mp4'
    
    if not source_video.exists():
        print(f"❌ Error: Source video not found at {source_video}")
        return False
    
    print(f"✓ Found source video: {source_video}")
    
    # Copy video to expert folder
    dest_video = EXPERT_FOLDER / f"{POSE_ID}.mp4"
    print(f"Copying to: {dest_video}")
    shutil.copy2(source_video, dest_video)
    print("✓ Video copied")
    
    # Generate thumbnail
    thumbnail_path = EXPERT_FOLDER / f"{POSE_ID}_thumb.jpg"
    print("Generating thumbnail...")
    if generate_thumbnail(dest_video, thumbnail_path):
        print("✓ Thumbnail generated")
    else:
        print("⚠️ Warning: Thumbnail generation failed")
    
    # Get duration
    duration = get_video_duration(dest_video)
    print(f"✓ Video duration: {duration}")
    
    # Create database entry
    pose_data = {
        'id': POSE_ID,
        'name': 'The Bonus',
        'description': 'Professional Kabaddi raider executing standard raid movement with bonus point technique',
        'video_url': f'/data/expert_poses/{POSE_ID}.mp4',
        'thumbnail': f'/data/expert_poses/{POSE_ID}_thumb.jpg',
        'duration': duration,
        'uploaded_at': '2026-01-20T09:00:00'
    }
    
    # Save to database file
    db_file = DB_FOLDER / 'poses_db.json'
    poses_db = [pose_data]
    
    with open(db_file, 'w') as f:
        json.dump(poses_db, f, indent=2)
    
    print("✓ Database created")
    print(f"   Location: {db_file}")
    
    print("\n" + "=" * 70)
    print("Database Initialization Complete!")
    print("=" * 70)
    print("\nExpert Pose Added:")
    print(f"  Name: {pose_data['name']}")
    print(f"  Description: {pose_data['description']}")
    print(f"  Duration: {pose_data['duration']}")
    print(f"  Video: {dest_video}")
    print(f"  Thumbnail: {thumbnail_path}")
    
    print("\n✓ Backend server can now serve this pose")
    print("  Start server: python frontend/backend/app.py")
    
    return True

if __name__ == '__main__':
    initialize_database()
