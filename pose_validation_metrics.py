"""
Pose Validation Metrics for AR-Based Kabaddi Ghost Trainer

This module provides deterministic, explainable metrics for:
1. Ghost Validation: Expert pose vs AR-rendered ghost pose
2. User Evaluation: User pose vs validated ghost pose

Metrics are separated into:
- Structural Accuracy: Spatial positions and joint angles
- Temporal Accuracy: Motion synchronization and timing

Input Format: (T, 17, 2) - COCO-17 normalized pose sequences
Output: 0-100 score (higher is better)
"""

import numpy as np
from typing import Tuple, Dict
from scipy.spatial.distance import euclidean


class PoseValidationMetrics:
    """
    Minimal metric system for pose validation and user evaluation.
    
    Constraints:
    - 2D pose only (no 3D)
    - No deep learning
    - Deterministic and reproducible
    - Explainable components
    """
    
    # COCO-17 joint indices
    NOSE = 0
    LEFT_SHOULDER, RIGHT_SHOULDER = 5, 6
    LEFT_ELBOW, RIGHT_ELBOW = 7, 8
    LEFT_WRIST, RIGHT_WRIST = 9, 10
    LEFT_HIP, RIGHT_HIP = 11, 12
    LEFT_KNEE, RIGHT_KNEE = 13, 14
    LEFT_ANKLE, RIGHT_ANKLE = 15, 16
    
    # Kabaddi-critical joint triplets for angle computation
    KEY_ANGLES = [
        (5, 7, 9),    # Left arm: shoulder-elbow-wrist
        (6, 8, 10),   # Right arm: shoulder-elbow-wrist
        (11, 13, 15), # Left leg: hip-knee-ankle
        (12, 14, 16), # Right leg: hip-knee-ankle
        (5, 11, 13),  # Left torso: shoulder-hip-knee
        (6, 12, 14),  # Right torso: shoulder-hip-knee
    ]
    
    # Kabaddi-specific joint importance weights
    JOINT_WEIGHTS = np.array([
        1.0,  # 0: Nose
        0.8,  # 1: Left Eye
        0.8,  # 2: Right Eye
        0.8,  # 3: Left Ear
        0.8,  # 4: Right Ear
        1.3,  # 5: Left Shoulder
        1.3,  # 6: Right Shoulder
        1.1,  # 7: Left Elbow
        1.1,  # 8: Right Elbow
        1.4,  # 9: Left Wrist (tagging)
        1.4,  # 10: Right Wrist (tagging)
        1.5,  # 11: Left Hip (stance)
        1.5,  # 12: Right Hip (stance)
        1.8,  # 13: Left Knee (critical for raiding)
        1.8,  # 14: Right Knee (critical for raiding)
        1.5,  # 15: Left Ankle
        1.5,  # 16: Right Ankle
    ])
    
    def __init__(self):
        """Initialize pose validation metrics."""
        self.total_weight = np.sum(self.JOINT_WEIGHTS)
    
    # ==================== PREPROCESSING ====================
    
    @staticmethod
    def normalize_by_torso(pose_sequence: np.ndarray) -> np.ndarray:
        """
        Normalize pose by torso height for scale invariance.
        
        Args:
            pose_sequence: Shape (T, 17, 2)
        
        Returns:
            Normalized pose: Shape (T, 17, 2)
        """
        T, J, _ = pose_sequence.shape
        normalized = np.zeros_like(pose_sequence, dtype=np.float32)
        
        for t in range(T):
            # Torso height = distance from left shoulder to left hip
            torso_height = np.linalg.norm(
                pose_sequence[t, 5] - pose_sequence[t, 11]
            ) + 1e-6  # Avoid division by zero
            
            normalized[t] = pose_sequence[t] / torso_height
        
        return normalized
    
    @staticmethod
    def temporal_interpolate(pose_sequence: np.ndarray, target_length: int) -> np.ndarray:
        """
        Interpolate pose sequence to target length for alignment.
        
        Args:
            pose_sequence: Shape (T, 17, 2)
            target_length: Desired number of frames
        
        Returns:
            Interpolated pose: Shape (target_length, 17, 2)
        """
        from scipy.interpolate import interp1d
        
        T, J, C = pose_sequence.shape
        original_indices = np.arange(T)
        target_indices = np.linspace(0, T - 1, target_length)
        
        interpolated = np.zeros((target_length, J, C), dtype=np.float32)
        
        for j in range(J):
            for c in range(C):
                f = interp1d(original_indices, pose_sequence[:, j, c], kind='linear')
                interpolated[:, j, c] = f(target_indices)
        
        return interpolated
    
    # ==================== METRIC 1: STRUCTURAL ACCURACY ====================
    
    def compute_spatial_distance(self, pose_ref: np.ndarray, pose_tar: np.ndarray) -> float:
        """
        Compute weighted spatial distance between poses.
        
        This combines:
        - Joint position accuracy
        - Kabaddi-specific joint importance
        
        Args:
            pose_ref: Reference pose (T, 17, 2) - already normalized
            pose_tar: Target pose (T, 17, 2) - already normalized
        
        Returns:
            Weighted spatial distance (lower is better)
        """
        T, J, _ = pose_ref.shape
        
        # Compute per-joint distances
        distances = np.linalg.norm(pose_ref - pose_tar, axis=2)  # Shape: (T, 17)
        
        # Apply Kabaddi-specific weights
        weighted_distances = distances * self.JOINT_WEIGHTS[np.newaxis, :]
        
        # Average across time and joints
        spatial_dist = np.sum(weighted_distances) / (T * self.total_weight)
        
        return spatial_dist
    
    @staticmethod
    def compute_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """
        Compute angle at p2 formed by points p1-p2-p3.
        
        Args:
            p1, p2, p3: Points as (x, y) arrays
        
        Returns:
            Angle in radians [0, π]
        """
        v1 = p1 - p2
        v2 = p3 - p2
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        
        return np.arccos(cos_angle)
    
    def compute_angle_consistency(self, pose_ref: np.ndarray, pose_tar: np.ndarray) -> float:
        """
        Compute angular consistency across key joint triplets.
        
        Args:
            pose_ref: Reference pose (T, 17, 2)
            pose_tar: Target pose (T, 17, 2)
        
        Returns:
            Mean angle difference in radians (lower is better)
        """
        T = min(len(pose_ref), len(pose_tar))
        angle_diffs = []
        
        for t in range(T):
            for a, b, c in self.KEY_ANGLES:
                angle_ref = self.compute_angle(
                    pose_ref[t, a], pose_ref[t, b], pose_ref[t, c]
                )
                angle_tar = self.compute_angle(
                    pose_tar[t, a], pose_tar[t, b], pose_tar[t, c]
                )
                angle_diffs.append(abs(angle_ref - angle_tar))
        
        return np.mean(angle_diffs)
    
    def structural_accuracy(self, pose_ref: np.ndarray, pose_tar: np.ndarray) -> float:
        """
        Compute overall structural accuracy (0-100 scale).
        
        Combines:
        - Weighted spatial distance (70%)
        - Angular consistency (30%)
        
        Args:
            pose_ref: Reference pose (T, 17, 2) - normalized
            pose_tar: Target pose (T, 17, 2) - normalized, aligned
        
        Returns:
            Structural accuracy score [0, 100]
        """
        # Normalize poses
        pose_ref_norm = self.normalize_by_torso(pose_ref)
        pose_tar_norm = self.normalize_by_torso(pose_tar)
        
        # Align lengths by interpolation
        T_ref = len(pose_ref_norm)
        if len(pose_tar_norm) != T_ref:
            pose_tar_norm = self.temporal_interpolate(pose_tar_norm, T_ref)
        
        # Compute spatial distance
        spatial_dist = self.compute_spatial_distance(pose_ref_norm, pose_tar_norm)
        spatial_score = np.exp(-15 * spatial_dist)  # Exponential decay
        
        # Compute angular consistency
        angle_diff = self.compute_angle_consistency(pose_ref_norm, pose_tar_norm)
        angle_score = np.exp(-angle_diff / np.pi)  # Normalize by π
        
        # Weighted combination
        structural_score = 100 * (0.7 * spatial_score + 0.3 * angle_score)
        
        return float(structural_score)
    
    # ==================== METRIC 2: TEMPORAL ACCURACY ====================
    
    @staticmethod
    def compute_dtw_distance(seq1: np.ndarray, seq2: np.ndarray) -> float:
        """
        Compute Dynamic Time Warping distance between two sequences.
        
        This is a minimal DTW implementation without external dependencies.
        For production, use dtaidistance or fastdtw library.
        
        Args:
            seq1: Sequence 1 - Shape (T1, D)
            seq2: Sequence 2 - Shape (T2, D)
        
        Returns:
            DTW distance (normalized)
        """
        T1, D = seq1.shape
        T2 = seq2.shape[0]
        
        # Initialize DTW matrix
        dtw_matrix = np.full((T1 + 1, T2 + 1), np.inf)
        dtw_matrix[0, 0] = 0.0
        
        # Fill DTW matrix
        for i in range(1, T1 + 1):
            for j in range(1, T2 + 1):
                cost = np.linalg.norm(seq1[i - 1] - seq2[j - 1])
                dtw_matrix[i, j] = cost + min(
                    dtw_matrix[i - 1, j],      # Insertion
                    dtw_matrix[i, j - 1],      # Deletion
                    dtw_matrix[i - 1, j - 1]   # Match
                )
        
        # Normalize by path length
        dtw_dist = dtw_matrix[T1, T2] / max(T1, T2)
        
        return dtw_dist
    
    def temporal_accuracy(self, pose_ref: np.ndarray, pose_tar: np.ndarray) -> float:
        """
        Compute temporal accuracy using DTW alignment (0-100 scale).
        
        Measures how well the motion timing aligns between sequences.
        
        Args:
            pose_ref: Reference pose (T1, 17, 2)
            pose_tar: Target pose (T2, 17, 2)
        
        Returns:
            Temporal accuracy score [0, 100]
        """
        # Flatten poses to (T, 34) for DTW computation
        pose_ref_flat = pose_ref.reshape(len(pose_ref), -1)
        pose_tar_flat = pose_tar.reshape(len(pose_tar), -1)
        
        # Compute DTW distance
        dtw_dist = self.compute_dtw_distance(pose_ref_flat, pose_tar_flat)
        
        # Convert to score (exponential decay with sensitivity=5)
        temporal_score = 100 * np.exp(-5 * dtw_dist)
        
        return float(temporal_score)
    
    # ==================== FINAL SCORING ====================
    
    def ghost_validation_score(
        self, 
        expert_pose: np.ndarray, 
        ghost_pose: np.ndarray
    ) -> Dict[str, float]:
        """
        Validate AR ghost against expert reference.
        
        Args:
            expert_pose: Expert reference pose (T, 17, 2)
            ghost_pose: AR-rendered ghost pose (T, 17, 2)
        
        Returns:
            Dictionary with:
            - 'structural': Structural accuracy [0, 100]
            - 'temporal': Temporal accuracy [0, 100]
            - 'overall': Final validation score [0, 100]
        """
        # Compute structural accuracy
        structural = self.structural_accuracy(expert_pose, ghost_pose)
        
        # Compute temporal accuracy
        temporal = self.temporal_accuracy(expert_pose, ghost_pose)
        
        # Overall score (60% structural, 40% temporal)
        # Ghost should prioritize structural fidelity
        overall = 0.6 * structural + 0.4 * temporal
        
        return {
            'structural': structural,
            'temporal': temporal,
            'overall': overall
        }
    
    def user_evaluation_score(
        self, 
        user_pose: np.ndarray, 
        ghost_pose: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate user performance against validated ghost.
        
        Args:
            user_pose: User's captured pose (T, 17, 2)
            ghost_pose: Validated ghost pose (T, 17, 2)
        
        Returns:
            Dictionary with:
            - 'structural': Structural accuracy [0, 100]
            - 'temporal': Temporal accuracy [0, 100]
            - 'overall': Final evaluation score [0, 100]
        """
        # Compute structural accuracy
        structural = self.structural_accuracy(ghost_pose, user_pose)
        
        # Compute temporal accuracy
        temporal = self.temporal_accuracy(ghost_pose, user_pose)
        
        # Overall score (50% structural, 50% temporal)
        # User evaluation balances both aspects equally
        overall = 0.5 * structural + 0.5 * temporal
        
        return {
            'structural': structural,
            'temporal': temporal,
            'overall': overall
        }
    
    @staticmethod
    def interpret_score(score: float) -> str:
        """
        Provide human-readable interpretation of score.
        
        Args:
            score: Score value [0, 100]
        
        Returns:
            Interpretation string
        """
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Very Good"
        elif score >= 70:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 50:
            return "Needs Improvement"
        else:
            return "Poor"


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    """
    Example usage demonstrating ghost validation and user evaluation.
    """
    
    # Initialize metrics
    metrics = PoseValidationMetrics()
    
    # Example 1: Ghost Validation
    print("=" * 60)
    print("EXAMPLE 1: Ghost Validation")
    print("=" * 60)
    
    # Load expert and ghost poses (T, 17, 2)
    # Replace with actual data loading
    expert_pose = np.random.rand(100, 17, 2) * 100  # Dummy data
    ghost_pose = expert_pose + np.random.randn(100, 17, 2) * 2  # With noise
    
    ghost_scores = metrics.ghost_validation_score(expert_pose, ghost_pose)
    
    print(f"Structural Accuracy: {ghost_scores['structural']:.2f}/100")
    print(f"Temporal Accuracy:   {ghost_scores['temporal']:.2f}/100")
    print(f"Overall Score:       {ghost_scores['overall']:.2f}/100")
    print(f"Interpretation:      {metrics.interpret_score(ghost_scores['overall'])}")
    print()
    
    # Example 2: User Evaluation
    print("=" * 60)
    print("EXAMPLE 2: User Evaluation")
    print("=" * 60)
    
    # Load user and ghost poses
    user_pose = ghost_pose + np.random.randn(100, 17, 2) * 5  # User attempt
    
    user_scores = metrics.user_evaluation_score(user_pose, ghost_pose)
    
    print(f"Structural Accuracy: {user_scores['structural']:.2f}/100")
    print(f"Temporal Accuracy:   {user_scores['temporal']:.2f}/100")
    print(f"Overall Score:       {user_scores['overall']:.2f}/100")
    print(f"Interpretation:      {metrics.interpret_score(user_scores['overall'])}")
    print()
    
    # Example 3: Component-wise Analysis
    print("=" * 60)
    print("EXAMPLE 3: Detailed Component Analysis")
    print("=" * 60)
    
    # Normalize poses
    expert_norm = metrics.normalize_by_torso(expert_pose)
    ghost_norm = metrics.normalize_by_torso(ghost_pose)
    
    # Spatial distance
    spatial_dist = metrics.compute_spatial_distance(expert_norm, ghost_norm)
    print(f"Spatial Distance (raw): {spatial_dist:.4f}")
    
    # Angular consistency
    angle_diff = metrics.compute_angle_consistency(expert_norm, ghost_norm)
    print(f"Angle Difference (rad): {angle_diff:.4f}")
    
    # DTW distance
    expert_flat = expert_pose.reshape(len(expert_pose), -1)
    ghost_flat = ghost_pose.reshape(len(ghost_pose), -1)
    dtw_dist = metrics.compute_dtw_distance(expert_flat, ghost_flat)
    print(f"DTW Distance:           {dtw_dist:.4f}")
