"""
Level-3 Error Localization Module

Computes frame-wise Euclidean errors between aligned user and trainer pose sequences.
Provides joint-wise aggregated statistics and optional temporal phase segmentation.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


# COCO-17 joint names in standard order
COCO_17_JOINTS = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle"
]


def compute_error_metrics(
    aligned_user_poses: np.ndarray,
    aligned_trainer_poses: np.ndarray,
    enable_temporal_phases: bool = True
) -> Dict:
    """
    Compute error localization metrics between aligned pose sequences.
    
    Args:
        aligned_user_poses: (T, 17, 2) - User pose sequence
        aligned_trainer_poses: (T, 17, 2) - Trainer pose sequence  
        enable_temporal_phases: Whether to compute temporal phase errors
        
    Returns:
        Dictionary containing frame errors, joint aggregates, and optional phases
    """
    # Validate inputs
    assert aligned_user_poses.shape == aligned_trainer_poses.shape
    assert aligned_user_poses.shape[1:] == (17, 2), "Expected COCO-17 format (17, 2)"
    
    T, num_joints, _ = aligned_user_poses.shape
    
    # Compute frame-wise Euclidean error per joint
    frame_errors = np.linalg.norm(
        aligned_user_poses - aligned_trainer_poses, axis=2
    )  # Shape: (T, 17)
    
    # Aggregate joint-wise statistics
    joint_aggregates = {}
    for j, joint_name in enumerate(COCO_17_JOINTS):
        joint_errors = frame_errors[:, j]
        joint_aggregates[joint_name] = {
            "mean": float(np.mean(joint_errors)),
            "max": float(np.max(joint_errors)),
            "std": float(np.std(joint_errors))
        }
    
    # Build result dictionary
    result = {
        "frame_errors": {
            "shape": list(frame_errors.shape),
            "data": frame_errors.tolist()
        },
        "joint_aggregates": joint_aggregates,
        "metadata": {
            "total_frames": T,
            "joints_count": num_joints
        }
    }
    
    # Optional temporal phase segmentation
    if enable_temporal_phases:
        phase_boundaries = [0, T//3, 2*T//3, T]
        phases = ["early", "mid", "late"]
        
        temporal_phases = {}
        for i, phase in enumerate(phases):
            start_idx = phase_boundaries[i]
            end_idx = phase_boundaries[i + 1]
            phase_errors = frame_errors[start_idx:end_idx]
            
            phase_joint_means = {}
            for j, joint_name in enumerate(COCO_17_JOINTS):
                phase_joint_means[joint_name] = float(np.mean(phase_errors[:, j]))
            
            temporal_phases[phase] = phase_joint_means
        
        result["temporal_phases"] = temporal_phases
        result["metadata"]["phase_boundaries"] = phase_boundaries
    
    return result


def get_joint_ranking(error_metrics: Dict, metric: str = "mean") -> List[Tuple[str, float]]:
    """
    Get joints ranked by error magnitude.
    
    Args:
        error_metrics: Output from compute_error_metrics
        metric: "mean", "max", or "std"
        
    Returns:
        List of (joint_name, error_value) tuples sorted by error descending
    """
    joint_errors = []
    for joint_name, stats in error_metrics["joint_aggregates"].items():
        joint_errors.append((joint_name, stats[metric]))
    
    return sorted(joint_errors, key=lambda x: x[1], reverse=True)


# Example usage
if __name__ == "__main__":
    # Create sample aligned pose data
    T = 150  # frames
    user_poses = np.random.randn(T, 17, 2) * 10 + 100
    trainer_poses = np.random.randn(T, 17, 2) * 8 + 105
    
    # Compute error metrics
    metrics = compute_error_metrics(user_poses, trainer_poses)
    
    # Display summary
    print(f"Total frames: {metrics['metadata']['total_frames']}")
    print(f"Joints analyzed: {metrics['metadata']['joints_count']}")
    
    # Show top 3 problematic joints
    top_errors = get_joint_ranking(metrics, "mean")[:3]
    print("\nTop 3 joints with highest mean error:")
    for joint, error in top_errors:
        print(f"  {joint}: {error:.2f}")