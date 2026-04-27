"""
Kabaddi Ghost Trainer - Pipeline Runner (PRODUCTION VERSION)
Executes full 4-level pipeline for frontend demo integration

CHANGES FROM PREVIOUS VERSION:
- ❌ NO MORE RANDOM SCORES: Executes actual Level 1-4 algorithms
- ✅ REAL pose extraction using pose_extract_cli.py
- ✅ REAL DTW alignment
- ✅ REAL error computation
- ✅ REAL similarity scores from Level-4
- ✅ Caches expert poses for performance
"""

import subprocess
import os
import json
import sys
import numpy as np
from pathlib import Path
from typing import Dict, Tuple
import time

# Add project root to path for imports
BASE_DIR = Path(__file__).parent.parent.parent.parent.parent  # kabaddi_trainer/ root
# Path: pipeline_runner.py -> backend/ -> frontend/ -> old_frontend/ -> _archive/ -> kabaddi_trainer/
sys.path.insert(0, str(BASE_DIR))  # Add to FRONT of path
sys.path.insert(0, str(BASE_DIR / 'level1_pose'))  # Add level1_pose for relative imports

# Import Level-1 pose extraction function directly
try:
    from level1_pose.pose_extract_cli import extract_pose_from_video
    LEVEL1_AVAILABLE = True
    print("[Init] Level-1 pose extraction loaded successfully")
except ImportError as e:
    print(f"[WARNING] Level-1 not available: {e}")
    LEVEL1_AVAILABLE = False

# Import visualization generator (same directory as this file)
try:
    from visualization_generator import (
        create_level2_visualization,
        create_level3_visualization,
        create_level4_visualization
    )
    VISUALIZATION_AVAILABLE = True
    print("[Init] Visualization generator loaded successfully")
except ImportError as e:
    print(f"[WARNING] Visualization not available: {e}")
    VISUALIZATION_AVAILABLE = False

# We'll implement DTW, error computation, and scoring inline (copied from source)
# This avoids complex import dependencies


# Paths
RESULTS_FOLDER = BASE_DIR / 'data' / 'results'
EXPERT_FOLDER = BASE_DIR / 'data' / 'expert_poses'
USER_FOLDER = BASE_DIR / 'data' / 'user_uploads'
EXPERT_POSE_CACHE = BASE_DIR / 'data' / 'expert_pose_cache'


# ============================================================================
# JSON SANITIZER (Convert NaN/Inf to None for valid JSON)
# ============================================================================

def sanitize_for_json(obj):
    """
    Recursively convert NaN and Infinity values to None (null in JSON)
    
    This is necessary because numpy's NaN and Inf are not valid JSON values
    """
    if isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.floating):  # numpy float types
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.integer):  # numpy int types
        return int(obj)
    else:
        return obj


# Ensure cache directory exists
EXPERT_POSE_CACHE.mkdir(parents=True, exist_ok=True)


# ============================================================================
# LEVEL-2: DTW ALIGNMENT (Imported from visualize_level2.py)
# ============================================================================

def extract_pelvis(poses: np.ndarray) -> np.ndarray:
    """Extract pelvis trajectory from poses (midpoint of hips)"""
    LEFT_HIP = 11
    RIGHT_HIP = 12
    left_hip = poses[:, LEFT_HIP, :]
    right_hip = poses[:, RIGHT_HIP, :]
    pelvis = (left_hip + right_hip) * 0.5
    return pelvis


def dtw_align(expert_pelvis: np.ndarray, user_pelvis: np.ndarray) -> Tuple:
    """Perform DTW alignment on pelvis trajectories"""
    T_expert = len(expert_pelvis)
    T_user = len(user_pelvis)
    
    # Initialize cost matrix
    cost_matrix = np.full((T_expert + 1, T_user + 1), np.inf)
    cost_matrix[0, 0] = 0
    
    # Fill cost matrix
    for i in range(1, T_expert + 1):
        for j in range(1, T_user + 1):
            distance = np.linalg.norm(expert_pelvis[i - 1] - user_pelvis[j - 1])
            cost_matrix[i, j] = distance + min(
                cost_matrix[i - 1, j],
                cost_matrix[i, j - 1],
                cost_matrix[i - 1, j - 1]
            )
    
    # Backtrack to find optimal path
    path_expert = []
    path_user = []
    
    i, j = T_expert, T_user
    while i > 0 and j > 0:
        path_expert.append(i - 1)
        path_user.append(j - 1)
        
        candidates = [
            cost_matrix[i - 1, j - 1],
            cost_matrix[i - 1, j],
            cost_matrix[i, j - 1]
        ]
        min_idx = np.argmin(candidates)
        
        if min_idx == 0:
            i -= 1
            j -= 1
        elif min_idx == 1:
            i -= 1
        else:
            j -= 1
    
    path_expert.reverse()
    path_user.reverse()
    
    return path_expert, path_user


def run_level2_dtw(expert_poses: np.ndarray, user_poses: np.ndarray) -> Tuple:
    """
    Run Level-2 DTW alignment
    
    Returns:
        Tuple of (aligned_expert, aligned_user, T_aligned)
    """
    print("[Level-2] Running DTW alignment...")
    
    # Extract pelvis trajectories
    expert_pelvis = extract_pelvis(expert_poses)
    user_pelvis = extract_pelvis(user_poses)
    
    # Perform DTW
    expert_indices, user_indices = dtw_align(expert_pelvis, user_pelvis)
    T_aligned = len(expert_indices)
    
    # Create aligned sequences
    aligned_expert = expert_poses[expert_indices]
    aligned_user = user_poses[user_indices]
    
    print(f"  ✓ DTW aligned: {T_aligned} frames")
    return aligned_expert, aligned_user, T_aligned


# ============================================================================
# LEVEL-3: ERROR COMPUTATION (Inline Implementation)
# ============================================================================

COCO17_JOINT_NAMES = {
    0: "nose", 1: "left_eye", 2: "right_eye", 3: "left_ear", 4: "right_ear",
    5: "left_shoulder", 6: "right_shoulder", 7: "left_elbow", 8: "right_elbow",
    9: "left_wrist", 10: "right_wrist", 11: "left_hip", 12: "right_hip",
    13: "left_knee", 14: "right_knee", 15: "left_ankle", 16: "right_ankle"
}

def compute_joint_errors(expert_poses: np.ndarray, user_poses: np.ndarray) -> np.ndarray:
    """Compute frame-wise, joint-wise Manhattan (L1) errors"""
    return np.sum(np.abs(expert_poses - user_poses), axis=2)


def aggregate_joint_stats(errors: np.ndarray) -> Dict:
    """Aggregate error statistics across time for each joint"""
    joint_stats = {}
    
    for joint_idx in range(17):
        joint_name = COCO17_JOINT_NAMES[joint_idx]
        joint_errors = errors[:, joint_idx]
        
        joint_stats[joint_name] = {
            "mean": float(np.nanmean(joint_errors)),
            "max": float(np.nanmax(joint_errors)),
            "std": float(np.nanstd(joint_errors))
        }
    
    return joint_stats


def aggregate_frame_stats(errors: np.ndarray) -> Dict:
    """Aggregate error statistics across joints for each frame"""
    T = errors.shape[0]
    frame_stats = {}
    
    for t in range(T):
        frame_errors = errors[t, :]
        frame_stats[t] = {
            "mean_error": float(np.nanmean(frame_errors)),
            "max_error": float(np.nanmax(frame_errors))
        }
    
    return frame_stats


def compute_phase_stats(errors: np.ndarray) -> Dict:
    """Compute per-phase joint error statistics"""
    T = errors.shape[0]
    
    early_end = T // 3
    mid_end = 2 * T // 3
    
    phase_stats = {}
    
    # Early phase
    early_errors = errors[0:early_end, :]
    phase_stats["early"] = {}
    for joint_idx in range(17):
        joint_name = COCO17_JOINT_NAMES[joint_idx]
        phase_stats["early"][joint_name] = float(np.nanmean(early_errors[:, joint_idx]))
    
    # Mid phase
    mid_errors = errors[early_end:mid_end, :]
    phase_stats["mid"] = {}
    for joint_idx in range(17):
        joint_name = COCO17_JOINT_NAMES[joint_idx]
        phase_stats["mid"][joint_name] = float(np.nanmean(mid_errors[:, joint_idx]))
    
    # Late phase
    late_errors = errors[mid_end:, :]
    phase_stats["late"] = {}
    for joint_idx in range(17):
        joint_name = COCO17_JOINT_NAMES[joint_idx]
        phase_stats["late"][joint_name] = float(np.nanmean(late_errors[:, joint_idx]))
    
    return phase_stats


def export_frame_joint_errors(errors: np.ndarray) -> Dict:
    """Export frame-wise joint errors for visualization"""
    T, num_joints = errors.shape
    frame_joint_errors = {}
    
    for t in range(T):
        frame_joint_errors[t] = {}
        for j in range(num_joints):
            joint_name = COCO17_JOINT_NAMES[j]
            frame_joint_errors[t][joint_name] = float(errors[t, j])
    
    return frame_joint_errors


# ============================================================================
# LEVEL-4: SIMILARITY SCORING (Inline Implementation)
# ============================================================================

MAX_ERROR_THRESHOLD = 1.5
WEIGHT_STRUCTURAL = 0.6
WEIGHT_TEMPORAL = 0.4
TEMPORAL_BASELINE = 85.0
BASELINE_FRAMES = 115


def compute_structural_similarity(error_data: Dict) -> float:
    """Compute structural similarity based on spatial accuracy"""
    joint_stats = error_data['joint_statistics']
    
    mean_errors = [stats['mean'] for stats in joint_stats.values()]
    mean_joint_error = np.nanmean(mean_errors)
    
    structural_similarity = max(0, min(100, (1 - mean_joint_error / MAX_ERROR_THRESHOLD) * 100))
    
    return structural_similarity


def compute_temporal_similarity(error_data: Dict) -> float:
    """Compute temporal similarity based on DTW alignment quality"""
    metadata = error_data.get('metadata', {})
    num_frames = metadata.get('num_frames')
    
    reference_duration = metadata.get('reference_duration', BASELINE_FRAMES)
    
    if not num_frames:
        return TEMPORAL_BASELINE
    
    frame_deviation = abs(num_frames - reference_duration)
    max_acceptable_deviation = reference_duration * 0.5
    
    if frame_deviation >= max_acceptable_deviation:
        temporal_quality = 0.0
    else:
        temporal_quality = 1.0 - (frame_deviation / max_acceptable_deviation)
    
    temporal_similarity = 70 + (temporal_quality * 30)
    
    return temporal_similarity


def compute_overall_score(structural: float, temporal: float) -> float:
    """Compute weighted overall performance score"""
    overall = WEIGHT_STRUCTURAL * structural + WEIGHT_TEMPORAL * temporal
    return overall


# ============================================================================
# PIPELINE EXECUTION
# ============================================================================

def get_or_extract_expert_pose(pose_id: str, expert_video_path: Path) -> Path:
    """
    Get cached expert pose or extract if not cached
    
    Args:
        pose_id: Expert pose ID
        expert_video_path: Path to expert video
        
    Returns:
        Path to expert pose .npy file
    """
    cached_pose_path = EXPERT_POSE_CACHE / f"{pose_id}_pose.npy"
    
    if cached_pose_path.exists():
        print(f"[Cache] Using cached expert pose: {cached_pose_path.name}")
        return cached_pose_path
    
    # Check if Level-1 is available
    if not LEVEL1_AVAILABLE:
        raise RuntimeError(
            "Pose extraction not available! Missing dependencies.\n"
            "Required files: level1_pose/mp33_to_coco17.py and level1_pose/level1_cleaning.py\n"
            "Make sure these files exist in the level1_pose directory."
        )
    
    print(f"[Level-1] Extracting expert pose (first time)...")
    print(f"  Video: {expert_video_path.name}")
    
    try:
        extract_pose_from_video(str(expert_video_path), str(cached_pose_path))
        print(f"  ✓ Expert pose extracted and cached")
        return cached_pose_path
    except Exception as e:
        raise RuntimeError(f"Expert pose extraction failed: {e}")


def extract_user_pose(user_video_path: Path, output_path: Path) -> Path:
    """
    Extract user pose using Level-1 pipeline
    
    Args:
        user_video_path: Path to user video
        output_path: Where to save pose .npy file
        
    Returns:
        Path to extracted pose file
    """
    # Check if Level-1 is available
    if not LEVEL1_AVAILABLE:
        raise RuntimeError(
            "Pose extraction not available! Missing dependencies.\n"
            "Required files: level1_pose/mp33_to_coco17.py and level1_pose/level1_cleaning.py\n"
            "Make sure these files exist in the level1_pose directory."
        )
    
    print(f"[Level-1] Extracting user pose...")
    print(f"  Video: {user_video_path.name}")
    
    try:
        extract_pose_from_video(str(user_video_path), str(output_path))
        print(f"  ✓ User pose extracted: {output_path.name}")
        return output_path
    except Exception as e:
        raise RuntimeError(f"User pose extraction failed: {e}")


def run_level3_errors(aligned_expert: np.ndarray, aligned_user: np.ndarray, reference_duration: int = 115) -> Dict:
    """
    Run Level-3 error computation
    
    Args:
        aligned_expert: Aligned expert poses (T, 17, 2)
        aligned_user: Aligned user poses (T, 17, 2)
        
    Returns:
        Dictionary with error statistics
    """
    print("[Level-3] Computing joint errors...")
    
    # Compute errors
    errors = compute_joint_errors(aligned_expert, aligned_user)
    
    # Aggregate statistics
    joint_stats = aggregate_joint_stats(errors)
    frame_stats = aggregate_frame_stats(errors)
    phase_stats = compute_phase_stats(errors)
    frame_joint_errors = export_frame_joint_errors(errors)
    
    T = errors.shape[0]
    
    error_data = {
        'metadata': {
            'num_frames': int(T),
            'reference_duration': int(reference_duration),
            'num_joints': 17,
            'alignment': 'DTW_pelvis_based'
        },
        'joint_statistics': joint_stats,
        'frame_statistics': {str(k): v for k, v in frame_stats.items()},
        'phase_statistics': phase_stats,
        'frame_joint_errors': {str(k): v for k, v in frame_joint_errors.items()}
    }
    
    print(f"  ✓ Errors computed for {T} frames")
    return error_data


def run_level4_scoring(error_data: Dict) -> Dict:
    """
    Run Level-4 similarity scoring
    
    Args:
        error_data: Error statistics from Level-3
        
    Returns:
        Dictionary with similarity scores
    """
    print("[Level-4] Computing similarity scores...")
    
    # Compute scores using REAL algorithms
    structural = compute_structural_similarity(error_data)
    temporal = compute_temporal_similarity(error_data)
    overall = compute_overall_score(structural, temporal)
    
    scores = {
        'structural': round(structural, 1),
        'temporal': round(temporal, 1),
        'overall': round(overall, 1)
    }
    
    print(f"  ✓ Structural: {scores['structural']}%")
    print(f"  ✓ Temporal: {scores['temporal']}%")
    print(f"  ✓ Overall: {scores['overall']}%")
    
    return scores


def run_demo_pipeline(session_id: str, pose_id: str, user_video_path: str) -> Dict:
    """
    Execute complete 4-level pipeline with REAL analysis
    
    Args:
        session_id: Unique session identifier
        pose_id: Expert pose ID
        user_video_path: Path to user-uploaded video
        
    Returns:
        dict: Success response with REAL scores
    """
    
    try:
        start_time = time.time()
        
        # Create session directory
        session_dir = RESULTS_FOLDER / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n{'=' * 70}")
        print(f"KABADDI GHOST TRAINER - PIPELINE EXECUTION")
        print(f"{'=' * 70}")
        print(f"Session ID: {session_id}")
        print(f"Pose ID: {pose_id}")
        print(f"User Video: {Path(user_video_path).name}\n")
        
        # ====================================================================
        # STEP 1: Find Expert Video
        # ====================================================================
        print("[Step 1/5] Locating expert video...")
        
        expert_video = None
        for ext in ['mp4', 'avi', 'mov', 'mkv']:
            candidate = EXPERT_FOLDER / f"{pose_id}.{ext}"
            if candidate.exists():
                expert_video = candidate
                break
        
        if not expert_video:
            raise FileNotFoundError(f"Expert video not found for pose_id: {pose_id}")
        
        print(f"  ✓ Expert video: {expert_video.name}\n")
        
        # ====================================================================
        # STEP 2: Extract Poses (Level-1)
        # ====================================================================
        print("[Step 2/5] Extracting poses (Level-1)...")
        
        # Get or extract expert pose (with caching)
        expert_pose_path = get_or_extract_expert_pose(pose_id, expert_video)
        expert_poses = np.load(expert_pose_path)
        
        # Extract user pose
        user_pose_path = session_dir / 'user_pose.npy'
        extract_user_pose(Path(user_video_path), user_pose_path)
        user_poses = np.load(user_pose_path)
        
        print(f"  Expert shape: {expert_poses.shape}")
        print(f"  User shape: {user_poses.shape}\n")
        
        # ====================================================================
        # STEP 3: DTW Alignment (Level-2)
        # ====================================================================
        print("[Step 3/5] Temporal alignment (Level-2)...")
        
        aligned_expert, aligned_user, T_aligned = run_level2_dtw(expert_poses, user_poses)
        
        # Save aligned poses
        aligned_expert_path = session_dir / 'expert_aligned.npy'
        aligned_user_path = session_dir / 'user_aligned.npy'
        np.save(aligned_expert_path, aligned_expert)
        np.save(aligned_user_path, aligned_user)
        
        print(f"  Aligned shape: ({T_aligned}, 17, 2)")
        
        # Generate Level-2 visualization
        if VISUALIZATION_AVAILABLE:
            print("  Generating Level-2 visualization...")
            level2_video_path = session_dir / 'level2_alignment.mp4'
            create_level2_visualization(aligned_expert, aligned_user, level2_video_path)
            print(f"  ✓ Level-2 video: {level2_video_path.name}")
        
        print()  # Blank line
        
        # ====================================================================
        # STEP 4: Error Computation (Level-3)
        # ====================================================================
        print("[Step 4/5] Error computation (Level-3)...")
        
        reference_duration = expert_poses.shape[0]
        error_data = run_level3_errors(aligned_expert, aligned_user, reference_duration=reference_duration)
        
        # Save error data (sanitize NaN values first)
        error_json_path = session_dir / 'joint_errors.json'
        with open(error_json_path, 'w') as f:
            clean_error_data = sanitize_for_json(error_data)
            json.dump(clean_error_data, f, indent=2)
        
        print(f"  Joint errors saved: {error_json_path.name}")
        
        # Generate Level-3 visualization
        if VISUALIZATION_AVAILABLE:
            print("  Generating Level-3 visualization...")
            level3_video_path = session_dir / 'level3_errors.mp4'
            create_level3_visualization(aligned_expert, aligned_user, error_data, level3_video_path)
            print(f"  ✓ Level-3 video: {level3_video_path.name}")
        
        print()  # Blank line
        
        # ====================================================================
        # STEP 5: Similarity Scoring (Level-4)
        # ====================================================================
        print("[Step 5/5] Similarity scoring (Level-4)...")
        
        scores = run_level4_scoring(error_data)
        
        # Save scores
        scores_json_path = session_dir / 'similarity_scores.json'
        with open(scores_json_path, 'w') as f:
            json.dump(scores, f, indent=2)
        
        print(f"  Scores saved: {scores_json_path.name}")
        
        # Generate Level-4 visualization
        if VISUALIZATION_AVAILABLE:
            print("  Generating Level-4 visualization...")
            level4_video_path = session_dir / 'level4_scoring.mp4'
            create_level4_visualization(aligned_user, scores, level4_video_path)
            print(f"  ✓ Level-4 video: {level4_video_path.name}")
        
        print()  # Blank line
        
        # ====================================================================
        # Save Complete Results
        # ====================================================================
        elapsed_time = time.time() - start_time
        
        results = {
            'session_id': session_id,
            'pose_id': pose_id,
            'scores': scores,  # REAL scores from Level-4
            'expert_video': f"/data/expert_poses/{expert_video.name}",  # For results.html
            'error_statistics': error_data,  # Full error data
            'videos': {
                'user_original': f"/data/user_uploads/{Path(user_video_path).name}",
                'expert_reference': f"/data/expert_poses/{expert_video.name}",
            },
            'visualization_videos': {
                'level1_raw': f"/data/user_uploads/{Path(user_video_path).name}",  # User's uploaded video
                'level2_alignment': f"/data/results/{session_id}/level2_alignment.mp4" if VISUALIZATION_AVAILABLE else None,
                'level3_errors': f"/data/results/{session_id}/level3_errors.mp4" if VISUALIZATION_AVAILABLE else None,
                'level4_scoring': f"/data/results/{session_id}/level4_scoring.mp4" if VISUALIZATION_AVAILABLE else None,
            },
            'pose_files': {
                'expert_aligned': str(aligned_expert_path.relative_to(BASE_DIR)),
                'user_aligned': str(aligned_user_path.relative_to(BASE_DIR)),
                'joint_errors': str(error_json_path.relative_to(BASE_DIR)),
                'similarity_scores': str(scores_json_path.relative_to(BASE_DIR))
            },
            'metadata': {
                'expert_frames': int(expert_poses.shape[0]),
                'user_frames': int(user_poses.shape[0]),
                'aligned_frames': int(T_aligned),
                'processing_time_seconds': round(elapsed_time, 2),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'pipeline_version': 'production_v1'
            }
        }
        
        # Save complete results        
        # Save results.json
        results_file = session_dir / 'results.json'
        with open(results_file, 'w') as f:
            clean_results = sanitize_for_json(results)
            json.dump(clean_results, f, indent=2)
        
        # Generate context.json for LLM Feedback
        try:
            from llm_feedback import generate_context, save_context
            print(f"[CONTEXT] Generating LLM context...")
            context = generate_context(results)
            context_file = session_dir / 'context.json'
            save_context(context, context_file)
            print(f"[CONTEXT] ✓ Context saved: {context_file.relative_to(BASE_DIR)}")
        except Exception as e:
            print(f"[CONTEXT] ⚠ Warning: Failed to generate context: {e}")
            # Don't fail the pipeline if context generation fails
        
        print(f"{'=' * 70}")
        print(f"PIPELINE COMPLETE ✓")
        print(f"{'=' * 70}")
        print(f"Processing time: {elapsed_time:.2f} seconds")
        print(f"Results saved: {results_file.relative_to(BASE_DIR)}")
        print(f"\nFINAL SCORES (REAL, NOT RANDOM):")
        print(f"  Structural: {scores['structural']}%")
        print(f"  Temporal: {scores['temporal']}%")
        print(f"  Overall: {scores['overall']}%")
        print(f"{'=' * 70}\n")
        
        return {
            'success': True,
            'session_id': session_id,
            'message': 'Analysis completed successfully',
            'scores': scores,
            'processing_time': elapsed_time
        }
        
    except Exception as e:
        import traceback
        print(f"\n{'=' * 70}")
        print(f"PIPELINE ERROR ✗")
        print(f"{'=' * 70}")
        print(f"Error: {str(e)}")
        print(f"\nTraceback:")
        traceback.print_exc()
        print(f"{'=' * 70}\n")
        raise


# Backward compatibility
run_analysis_pipeline = run_demo_pipeline


if __name__ == '__main__':
    print("Kabaddi Ghost Trainer - Production Pipeline Runner")
    print("This module executes the FULL 4-level analysis pipeline:")
    print("  Level 1: Pose extraction (YOLO + MediaPipe + Cleaning)")
    print("  Level 2: DTW temporal alignment")
    print("  Level 3: Joint error computation")
    print("  Level 4: Similarity scoring")
    print("\nREAL scores computed from actual algorithms (NO RANDOM VALUES)")
