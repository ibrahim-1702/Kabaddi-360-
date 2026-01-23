#!/usr/bin/env python3
"""
Minimal end-to-end dry-run test for run_pipeline.py
"""
import subprocess
import os
import json
import tempfile
import sys

def test_pipeline_dryrun():
    """Test that pipeline runs and produces scores.json"""

    # Resolve project root (parent of tests/)
    PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )

    PIPELINE_PATH = os.path.join(PROJECT_ROOT, "run_pipeline.py")

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:

        cmd = [
            sys.executable,
            PIPELINE_PATH,
            "--expert-pose", "raider_pose_level1.npy",
            "--user-pose", "user_pose_level1.npy",
            "--no-tts", "--no-viz",
            "--output-dir", temp_dir
        ]

        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,        # 🔑 critical
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"Pipeline failed:\n{result.stderr}")
            return False

        scores_path = os.path.join(temp_dir, "scores.json")

        if not os.path.exists(scores_path):
            print("scores.json not found")
            return False

        try:
            with open(scores_path, "r") as f:
                json.load(f)
            print("[SUCCESS] Pipeline dry-run test passed")
            return True
        except json.JSONDecodeError:
            print("scores.json is not valid JSON")
            return False


if __name__ == "__main__":
    success = test_pipeline_dryrun()
    sys.exit(0 if success else 1)
