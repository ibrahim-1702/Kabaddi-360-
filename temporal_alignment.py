#!/usr/bin/env python3
"""
Level-2 Temporal Alignment Module

Aligns User and Ghost pose sequences temporally using DTW on pelvis trajectories.
Handles speed differences between sequences before similarity computation.
"""

import numpy as np
from typing import Tuple, List


def extract_pelvis_trajectory(poses: np.ndarray) -> np.ndarray:
    """
    Extract pelvis trajectory from pose sequence using hip midpoint.
    
    Args:
        poses: Pose sequence (T, 17, 2) in COCO-17 format
        
    Returns:
        Pelvis trajectory (T, 2) - hip midpoint coordinates
    """
    # COCO-17: joint 11 = left hip, joint 12 = right hip
    left_hip = poses[:, 11, :]   # (T, 2)
    right_hip = poses[:, 12, :]  # (T, 2)
    
    # Pelvis = midpoint between hips
    pelvis = (left_hip + right_hip) / 2.0
    return pelvis


def compute_distance_matrix(user_pelvis: np.ndarray, ghost_pelvis: np.ndarray) -> np.ndarray:
    """
    Compute pairwise Euclidean distances between pelvis positions.
    
    Args:
        user_pelvis: User pelvis trajectory (T_user, 2)
        ghost_pelvis: Ghost pelvis trajectory (T_ghost, 2)
        
    Returns:
        Distance matrix (T_user, T_ghost)
    """
    T_user, T_ghost = len(user_pelvis), len(ghost_pelvis)
    distances = np.zeros((T_user, T_ghost))
    
    for i in range(T_user):
        for j in range(T_ghost):
            # Euclidean distance between pelvis positions
            diff = user_pelvis[i] - ghost_pelvis[j]
            distances[i, j] = np.sqrt(np.sum(diff ** 2))
    
    return distances


def dtw_alignment(distance_matrix: np.ndarray) -> List[Tuple[int, int]]:
    """
    Compute DTW alignment path using dynamic programming.
    
    Args:
        distance_matrix: Pairwise distances (T_user, T_ghost)
        
    Returns:
        Alignment path as list of (user_idx, ghost_idx) pairs
    """
    T_user, T_ghost = distance_matrix.shape
    
    # Initialize DTW cost matrix
    dtw_matrix = np.full((T_user, T_ghost), np.inf)
    dtw_matrix[0, 0] = distance_matrix[0, 0]
    
    # Fill first row and column
    for i in range(1, T_user):
        dtw_matrix[i, 0] = dtw_matrix[i-1, 0] + distance_matrix[i, 0]
    for j in range(1, T_ghost):
        dtw_matrix[0, j] = dtw_matrix[0, j-1] + distance_matrix[0, j]
    
    # Fill DTW matrix
    for i in range(1, T_user):
        for j in range(1, T_ghost):
            cost = distance_matrix[i, j]
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i-1, j],     # insertion
                dtw_matrix[i, j-1],     # deletion
                dtw_matrix[i-1, j-1]    # match
            )
    
    # Backtrack to find optimal path
    path = []
    i, j = T_user - 1, T_ghost - 1
    
    while i > 0 or j > 0:
        path.append((i, j))
        
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        else:
            # Choose minimum cost predecessor
            costs = [
                dtw_matrix[i-1, j-1],  # diagonal
                dtw_matrix[i-1, j],    # up
                dtw_matrix[i, j-1]     # left
            ]
            min_idx = np.argmin(costs)
            
            if min_idx == 0:    # diagonal
                i, j = i-1, j-1
            elif min_idx == 1:  # up
                i -= 1
            else:               # left
                j -= 1
    
    path.append((0, 0))
    path.reverse()
    
    return path


def temporal_alignment(user_poses: np.ndarray, ghost_poses: np.ndarray) -> Tuple[List[int], List[int]]:
    """
    Align User and Ghost pose sequences temporally using pelvis-based DTW.
    
    Args:
        user_poses: User pose sequence (T_user, 17, 2)
        ghost_poses: Ghost pose sequence (T_ghost, 17, 2)
        
    Returns:
        Tuple of (user_indices, ghost_indices) for aligned sequences
    """
    # Extract pelvis trajectories
    user_pelvis = extract_pelvis_trajectory(user_poses)
    ghost_pelvis = extract_pelvis_trajectory(ghost_poses)
    
    # Compute distance matrix
    distance_matrix = compute_distance_matrix(user_pelvis, ghost_pelvis)
    
    # Find DTW alignment path
    alignment_path = dtw_alignment(distance_matrix)
    
    # Extract frame indices
    user_indices = [pair[0] for pair in alignment_path]
    ghost_indices = [pair[1] for pair in alignment_path]
    
    return user_indices, ghost_indices


def get_alignment_score(user_poses: np.ndarray, ghost_poses: np.ndarray) -> float:
    """
    Compute alignment quality score (optional utility function).
    
    Args:
        user_poses: User pose sequence (T_user, 17, 2)
        ghost_poses: Ghost pose sequence (T_ghost, 17, 2)
        
    Returns:
        Alignment score (0-1, higher = better alignment)
    """
    user_pelvis = extract_pelvis_trajectory(user_poses)
    ghost_pelvis = extract_pelvis_trajectory(ghost_poses)
    distance_matrix = compute_distance_matrix(user_pelvis, ghost_pelvis)
    
    # Compute DTW cost
    T_user, T_ghost = distance_matrix.shape
    dtw_matrix = np.full((T_user, T_ghost), np.inf)
    dtw_matrix[0, 0] = distance_matrix[0, 0]
    
    for i in range(1, T_user):
        dtw_matrix[i, 0] = dtw_matrix[i-1, 0] + distance_matrix[i, 0]
    for j in range(1, T_ghost):
        dtw_matrix[0, j] = dtw_matrix[0, j-1] + distance_matrix[0, j]
    
    for i in range(1, T_user):
        for j in range(1, T_ghost):
            cost = distance_matrix[i, j]
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i-1, j],
                dtw_matrix[i, j-1],
                dtw_matrix[i-1, j-1]
            )
    
    # Normalize DTW cost to 0-1 score
    dtw_cost = dtw_matrix[T_user-1, T_ghost-1]
    max_possible_cost = np.max(distance_matrix) * max(T_user, T_ghost)
    
    if max_possible_cost > 0:
        normalized_cost = dtw_cost / max_possible_cost
        alignment_score = max(0.0, 1.0 - normalized_cost)
    else:
        alignment_score = 1.0
    
    return alignment_score