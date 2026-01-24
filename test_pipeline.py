"""Quick test script to verify pipeline_runner works"""
import sys
sys.path.insert(0, 'frontend/backend')

from pipeline_runner import run_demo_pipeline

print("Testing demo pipeline...")

try:
    result = run_demo_pipeline(
        session_id="test-123",
        pose_id="the-bonus-001",
        user_video_path="frontend/backend/data/user_uploads/test.mp4"
    )
    print("✓ Pipeline test successful!")
    print(f"Result: {result}")
except Exception as e:
    print(f"✗ Pipeline test failed: {e}")
    import traceback
    traceback.print_exc()
