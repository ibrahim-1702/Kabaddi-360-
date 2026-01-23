"""
Pipeline Runner - Integration with Kabaddi Ghost Trainer Pipeline
Executes the complete 4-level analysis pipeline and organizes results
"""

import subprocess
import os
import shutil
import json
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_FOLDER = Path(__file__).parent / 'data' / 'results'
EXPERT_FOLDER = Path(__file__).parent / 'data' / 'expert_poses'


def run_analysis_pipeline(session_id, pose_id, user_video_path):
    """
    Execute the complete pipeline analysis
    
    Args:
        session_id: Unique session identifier
        pose_id: Expert pose ID
        user_video_path: Path to user-uploaded video
        
    Returns:
        dict: Analysis results with paths to output videos and scores
    """
    
    # Create session results directory
    session_dir = RESULTS_FOLDER / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Find expert video
    expert_video = None
    for ext in ['mp4', 'avi', 'mov']:
        candidate = EXPERT_FOLDER / f"{pose_id}.{ext}"
        if candidate.exists():
            expert_video = candidate
            break
    
    if not expert_video:
        raise FileNotFoundError(f"Expert video not found for pose_id: {pose_id}")
    
    # Step 1: Extract expert pose (if not already extracted)
    expert_pose_path = EXPERT_FOLDER / f"{pose_id}_pose.npy"
    
    if not expert_pose_path.exists():
        print(f"Extracting expert pose from {expert_video}...")
        extract_cmd = [
            'python',
            str(BASE_DIR / 'level1_pose' / 'pose_extract_cli.py'),
            str(expert_video),
            str(expert_pose_path)
        ]
        subprocess.run(extract_cmd, check=True, cwd=str(BASE_DIR))
    
    # Step 2: Extract user pose
    print(f"Extracting user pose from {user_video_path}...")
    user_pose_path = session_dir / 'user_pose.npy'
    
    extract_cmd = [
        'python',
        str(BASE_DIR / 'level1_pose' / 'pose_extract_cli.py'),
        user_video_path,
        str(user_pose_path)
    ]
    subprocess.run(extract_cmd, check=True, cwd=str(BASE_DIR))
    
    # Step 3: Run complete pipeline
    print("Running pipeline analysis...")
    pipeline_cmd = [
        'python',
        str(BASE_DIR / 'run_pipeline.py'),
        '--expert-pose', str(expert_pose_path),
        '--user-pose', str(user_pose_path),
        '--output-dir', str(session_dir),
        '--no-tts',  # Disable TTS for web demo
        '--verbose'
    ]
    
    result = subprocess.run(
        pipeline_cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Pipeline execution failed: {result.stderr}")
    
    # Step 4: Organize results
    print("Organizing results...")
    
    # Load scores
    scores_file = session_dir / 'scores.json'
    with open(scores_file, 'r') as f:
        scores = json.load(f)
    
    # Check for joint errors (from Level-3)
    joint_errors = None
    error_file = session_dir / 'joint_errors.json'
    if error_file.exists():
        with open(error_file, 'r') as f:
            joint_errors = json.load(f)
    
    # Prepare result structure
    results = {
        'session_id': session_id,
        'scores': {
            'structural': scores.get('structural_score', 0),
            'temporal': scores.get('temporal_score', 0),
            'overall': scores.get('overall_score', 0)
        },
        'videos': {
            'level1_expert': f"/data/results/{session_id}/expert_cleaned.mp4" if (session_dir / 'expert_cleaned.mp4').exists() else None,
            'level1_user': f"/data/results/{session_id}/user_cleaned.mp4" if (session_dir / 'user_cleaned.mp4').exists() else None,
            'level2_alignment': f"/data/results/{session_id}/comparison.mp4" if (session_dir / 'comparison.mp4').exists() else None,
            'level3_errors': f"/data/results/{session_id}/error_visualization.mp4" if (session_dir / 'error_visualization.mp4').exists() else None,
            'level4_scoring': f"/data/results/{session_id}/scoring_visualization.mp4" if (session_dir / 'scoring_visualization.mp4').exists() else None
        },
        'joint_errors': joint_errors,
        'timestamp': scores.get('timestamp', None)
    }
    
    # Save formatted results
    results_file = session_dir / 'results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Analysis complete! Results saved to {session_dir}")
    
    return {
        'success': True,
        'session_id': session_id,
        'message': 'Analysis completed successfully'
    }


def cleanup_old_sessions(max_age_days=7):
    """
    Clean up old session directories
    
    Args:
        max_age_days: Maximum age of sessions to keep
    """
    import time
    
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    for session_dir in RESULTS_FOLDER.iterdir():
        if not session_dir.is_dir():
            continue
        
        # Check directory age
        dir_age = current_time - session_dir.stat().st_mtime
        
        if dir_age > max_age_seconds:
            print(f"Removing old session: {session_dir.name}")
            shutil.rmtree(session_dir)


if __name__ == '__main__':
    # Test pipeline runner
    print("Pipeline Runner Module - Test Mode")
    print("This module is imported by the Flask API")
