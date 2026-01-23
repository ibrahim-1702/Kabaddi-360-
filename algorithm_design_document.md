# Algorithm Design Document - AR-Based Kabaddi Ghost Trainer

## Document Information
- **Version**: 1.0
- **Date**: 2024-01-15
- **Author**: Algorithm Design Team
- **Classification**: Technical Specification

---

## Table of Contents

1. [Algorithm Overview](#algorithm-overview)
2. [Level-1 Pose Cleaning](#level-1-pose-cleaning)
3. [Level-2 Temporal Alignment](#level-2-temporal-alignment)
4. [Level-3 Error Localization](#level-3-error-localization)
5. [Level-4 Similarity Scoring](#level-4-similarity-scoring)
6. [Pose Extraction Algorithms](#pose-extraction-algorithms)
7. [Performance Analysis](#performance-analysis)
8. [Mathematical Foundations](#mathematical-foundations)

---

## 1. Algorithm Overview

### 1.1 Pipeline Architecture

The AR-Based Kabaddi Ghost Trainer employs a 4-level analytical pipeline with strict semantic separation:

```
Raw Video (MP4)
    ↓ [Pose Extraction]
MediaPipe 33-joint poses (T, 33, 2)
    ↓ [Format Conversion]
COCO-17 poses (T, 17, 2)
    ↓ [Level-1: Pose Cleaning & Normalization]
Cleaned poses (T, 17, 2)
    ↓ [Level-2: Temporal Alignment via DTW]
Aligned user & expert poses
    ↓ [Level-3: Error Localization Analysis]
Error metrics (frame-wise, joint-wise, temporal phases)
    ↓ [Level-4: Similarity Scoring]
Similarity scores (structural, temporal, overall)
```

### 1.2 Algorithm Design Principles

1. **Deterministic Processing**: All algorithms produce reproducible results
2. **Semantic Separation**: Each level has distinct mathematical purpose
3. **Error Propagation**: Graceful handling of upstream errors
4. **Computational Efficiency**: O(n) or O(n log n) complexity where possible
5. **Numerical Stability**: Robust to floating-point precision issues

### 1.3 Data Format Specifications

**Input Format**: COCO-17 pose sequences
```python
pose_sequence = np.array(shape=(T, 17, 2))
# T = number of frames
# 17 = COCO-17 joint count
# 2 = (x, y) coordinates in normalized space [0, 1]
```

**Joint Ordering** (COCO-17 Standard):
```python
COCO_17_JOINTS = [
    "nose",           # 0
    "left_eye",       # 1
    "right_eye",      # 2
    "left_ear",       # 3
    "right_ear",      # 4
    "left_shoulder",  # 5
    "right_shoulder", # 6
    "left_elbow",     # 7
    "right_elbow",    # 8
    "left_wrist",     # 9
    "right_wrist",    # 10
    "left_hip",       # 11
    "right_hip",      # 12
    "left_knee",      # 13
    "right_knee",     # 14
    "left_ankle",     # 15
    "right_ankle"     # 16
]
```

---

## 2. Level-1 Pose Cleaning

### 2.1 Algorithm Purpose

Level-1 cleaning transforms raw pose data into a canonical, normalized format suitable for downstream analysis. This includes noise reduction, outlier detection, and coordinate normalization.

### 2.2 Mathematical Foundation

**Noise Reduction via Gaussian Smoothing**:
```
For each joint j and coordinate c:
smoothed[t, j, c] = Σ(k=-w to w) G(k, σ) * raw[t+k, j, c]

where:
G(k, σ) = (1/√(2πσ²)) * exp(-k²/(2σ²))  # Gaussian kernel
w = 3σ (window size)
σ = 1.0 (standard deviation)
```

**Outlier Detection via Z-Score**:
```
For each joint trajectory:
z_score[t] = |pose[t] - mean(pose)| / std(pose)
outlier[t] = z_score[t] > threshold

where:
threshold = 3.0 (3-sigma rule)
```

**Coordinate Normalization**:
```
For pose sequence P with bounding box (x_min, y_min, x_max, y_max):
normalized[t, j, x] = (P[t, j, x] - x_min) / (x_max - x_min)
normalized[t, j, y] = (P[t, j, y] - y_min) / (y_max - y_min)
```

### 2.3 Implementation Specification

```python
def clean_level1_poses(poses: np.ndarray, config: dict = None) -> np.ndarray:
    """
    Apply Level-1 pose cleaning pipeline.
    
    Args:
        poses: Input pose sequence (T, 17, 2)
        config: Cleaning parameters
        
    Returns:
        Cleaned pose sequence (T, 17, 2)
    """
    if config is None:
        config = {
            'gaussian_sigma': 1.0,
            'outlier_threshold': 3.0,
            'interpolation_method': 'linear',
            'normalize_coordinates': True
        }
    
    T, num_joints, num_coords = poses.shape
    cleaned_poses = poses.copy()
    
    # Step 1: Gaussian smoothing
    for j in range(num_joints):
        for c in range(num_coords):
            cleaned_poses[:, j, c] = gaussian_smooth(
                poses[:, j, c], 
                sigma=config['gaussian_sigma']
            )
    
    # Step 2: Outlier detection and interpolation
    for j in range(num_joints):
        joint_trajectory = cleaned_poses[:, j, :]
        outliers = detect_outliers(joint_trajectory, config['outlier_threshold'])
        
        if np.any(outliers):
            cleaned_poses[:, j, :] = interpolate_outliers(
                joint_trajectory, 
                outliers, 
                method=config['interpolation_method']
            )
    
    # Step 3: Coordinate normalization
    if config['normalize_coordinates']:
        cleaned_poses = normalize_coordinates(cleaned_poses)
    
    # Step 4: Temporal consistency check
    cleaned_poses = ensure_temporal_consistency(cleaned_poses)
    
    return cleaned_poses

def gaussian_smooth(signal: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian smoothing to 1D signal."""
    from scipy import ndimage
    return ndimage.gaussian_filter1d(signal, sigma=sigma, mode='nearest')

def detect_outliers(trajectory: np.ndarray, threshold: float) -> np.ndarray:
    """Detect outliers using z-score method."""
    # Compute frame-wise distances from mean position
    mean_pos = np.mean(trajectory, axis=0)
    distances = np.linalg.norm(trajectory - mean_pos, axis=1)
    
    # Z-score based outlier detection
    z_scores = np.abs(distances - np.mean(distances)) / np.std(distances)
    return z_scores > threshold

def interpolate_outliers(trajectory: np.ndarray, outliers: np.ndarray, method: str) -> np.ndarray:
    """Interpolate outlier frames."""
    from scipy.interpolate import interp1d
    
    T = len(trajectory)
    valid_frames = ~outliers
    
    if np.sum(valid_frames) < 2:
        # Not enough valid frames for interpolation
        return trajectory
    
    # Create interpolation function
    valid_indices = np.where(valid_frames)[0]
    valid_positions = trajectory[valid_frames]
    
    if method == 'linear':
        interp_func = interp1d(
            valid_indices, 
            valid_positions, 
            axis=0, 
            kind='linear',
            bounds_error=False,
            fill_value='extrapolate'
        )
    else:
        raise ValueError(f"Unsupported interpolation method: {method}")
    
    # Interpolate outlier frames
    result = trajectory.copy()
    outlier_indices = np.where(outliers)[0]
    result[outlier_indices] = interp_func(outlier_indices)
    
    return result

def normalize_coordinates(poses: np.ndarray) -> np.ndarray:
    """Normalize coordinates to [0, 1] range."""
    T, num_joints, num_coords = poses.shape
    
    # Compute bounding box across all frames
    x_coords = poses[:, :, 0].flatten()
    y_coords = poses[:, :, 1].flatten()
    
    # Remove NaN values for bounding box calculation
    x_coords = x_coords[~np.isnan(x_coords)]
    y_coords = y_coords[~np.isnan(y_coords)]
    
    if len(x_coords) == 0 or len(y_coords) == 0:
        return poses  # No valid coordinates
    
    x_min, x_max = np.min(x_coords), np.max(x_coords)
    y_min, y_max = np.min(y_coords), np.max(y_coords)
    
    # Avoid division by zero
    x_range = x_max - x_min if x_max > x_min else 1.0
    y_range = y_max - y_min if y_max > y_min else 1.0
    
    # Normalize coordinates
    normalized_poses = poses.copy()
    normalized_poses[:, :, 0] = (poses[:, :, 0] - x_min) / x_range
    normalized_poses[:, :, 1] = (poses[:, :, 1] - y_min) / y_range
    
    return normalized_poses

def ensure_temporal_consistency(poses: np.ndarray) -> np.ndarray:
    """Ensure temporal consistency by limiting frame-to-frame changes."""
    max_change_threshold = 0.1  # Maximum normalized change per frame
    
    consistent_poses = poses.copy()
    T = poses.shape[0]
    
    for t in range(1, T):
        frame_change = np.linalg.norm(poses[t] - poses[t-1], axis=1)
        excessive_change = frame_change > max_change_threshold
        
        if np.any(excessive_change):
            # Limit excessive changes
            change_direction = poses[t] - poses[t-1]
            change_magnitude = np.linalg.norm(change_direction, axis=1, keepdims=True)
            
            # Normalize and scale
            normalized_change = change_direction / (change_magnitude + 1e-8)
            limited_change = normalized_change * np.minimum(
                change_magnitude, max_change_threshold
            )
            
            consistent_poses[t] = poses[t-1] + limited_change
    
    return consistent_poses
```

### 2.4 Performance Characteristics

**Time Complexity**: O(T × J × C)
- T = number of frames
- J = number of joints (17)
- C = number of coordinates (2)

**Space Complexity**: O(T × J × C) for intermediate arrays

**Typical Performance**:
- 150 frames: ~10ms processing time
- 300 frames: ~20ms processing time
- Memory usage: ~2x input size during processing

---

## 3. Level-2 Temporal Alignment

### 3.1 Algorithm Purpose

Level-2 temporal alignment synchronizes user and expert pose sequences using Dynamic Time Warping (DTW) on pelvis trajectories. This handles speed variations between performances.

### 3.2 Mathematical Foundation

**Pelvis Trajectory Extraction**:
```
For COCO-17 format:
pelvis[t] = (left_hip[t] + right_hip[t]) / 2
where:
left_hip = poses[t, 11, :]   # Joint index 11
right_hip = poses[t, 12, :]  # Joint index 12
```

**Distance Matrix Computation**:
```
D[i, j] = ||pelvis_user[i] - pelvis_expert[j]||₂

where:
||·||₂ is the Euclidean distance
i ∈ [0, T_user-1]
j ∈ [0, T_expert-1]
```

**DTW Recurrence Relation**:
```
DTW[i, j] = D[i, j] + min(
    DTW[i-1, j],     # insertion
    DTW[i, j-1],     # deletion  
    DTW[i-1, j-1]    # match
)

Base cases:
DTW[0, 0] = D[0, 0]
DTW[i, 0] = DTW[i-1, 0] + D[i, 0]  for i > 0
DTW[0, j] = DTW[0, j-1] + D[0, j]  for j > 0
```

**Optimal Path Backtracking**:
```
Starting from (T_user-1, T_expert-1), choose predecessor with minimum cost:
- (i-1, j-1): diagonal move (match)
- (i-1, j): vertical move (insertion)
- (i, j-1): horizontal move (deletion)
```

### 3.3 Implementation Specification

```python
def temporal_alignment(user_poses: np.ndarray, expert_poses: np.ndarray) -> Tuple[List[int], List[int]]:
    """
    Align user and expert pose sequences using DTW on pelvis trajectories.
    
    Args:
        user_poses: User pose sequence (T_user, 17, 2)
        expert_poses: Expert pose sequence (T_expert, 17, 2)
        
    Returns:
        Tuple of (user_indices, expert_indices) for aligned sequences
    """
    # Extract pelvis trajectories
    user_pelvis = extract_pelvis_trajectory(user_poses)
    expert_pelvis = extract_pelvis_trajectory(expert_poses)
    
    # Compute distance matrix
    distance_matrix = compute_distance_matrix(user_pelvis, expert_pelvis)
    
    # Apply DTW algorithm
    alignment_path = dtw_alignment(distance_matrix)
    
    # Extract frame indices
    user_indices = [pair[0] for pair in alignment_path]
    expert_indices = [pair[1] for pair in alignment_path]
    
    return user_indices, expert_indices

def extract_pelvis_trajectory(poses: np.ndarray) -> np.ndarray:
    """Extract pelvis trajectory from pose sequence."""
    # COCO-17: joint 11 = left hip, joint 12 = right hip
    left_hip = poses[:, 11, :]   # (T, 2)
    right_hip = poses[:, 12, :]  # (T, 2)
    
    # Pelvis = midpoint between hips
    pelvis = (left_hip + right_hip) / 2.0
    return pelvis

def compute_distance_matrix(user_pelvis: np.ndarray, expert_pelvis: np.ndarray) -> np.ndarray:
    """Compute pairwise Euclidean distances between pelvis positions."""
    T_user, T_expert = len(user_pelvis), len(expert_pelvis)
    distances = np.zeros((T_user, T_expert))
    
    for i in range(T_user):
        for j in range(T_expert):
            # Euclidean distance between pelvis positions
            diff = user_pelvis[i] - expert_pelvis[j]
            distances[i, j] = np.sqrt(np.sum(diff ** 2))
    
    return distances

def dtw_alignment(distance_matrix: np.ndarray) -> List[Tuple[int, int]]:
    """Compute DTW alignment path using dynamic programming."""
    T_user, T_expert = distance_matrix.shape
    
    # Initialize DTW cost matrix
    dtw_matrix = np.full((T_user, T_expert), np.inf)
    dtw_matrix[0, 0] = distance_matrix[0, 0]
    
    # Fill first row and column
    for i in range(1, T_user):
        dtw_matrix[i, 0] = dtw_matrix[i-1, 0] + distance_matrix[i, 0]
    for j in range(1, T_expert):
        dtw_matrix[0, j] = dtw_matrix[0, j-1] + distance_matrix[0, j]
    
    # Fill DTW matrix using recurrence relation
    for i in range(1, T_user):
        for j in range(1, T_expert):
            cost = distance_matrix[i, j]
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i-1, j],     # insertion
                dtw_matrix[i, j-1],     # deletion
                dtw_matrix[i-1, j-1]    # match
            )
    
    # Backtrack to find optimal path
    path = []
    i, j = T_user - 1, T_expert - 1
    
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

def get_alignment_quality_score(user_poses: np.ndarray, expert_poses: np.ndarray) -> float:
    """Compute alignment quality score (0-1, higher = better)."""
    user_pelvis = extract_pelvis_trajectory(user_poses)
    expert_pelvis = extract_pelvis_trajectory(expert_poses)
    distance_matrix = compute_distance_matrix(user_pelvis, expert_pelvis)
    
    # Compute DTW cost
    T_user, T_expert = distance_matrix.shape
    dtw_matrix = np.full((T_user, T_expert), np.inf)
    dtw_matrix[0, 0] = distance_matrix[0, 0]
    
    for i in range(1, T_user):
        dtw_matrix[i, 0] = dtw_matrix[i-1, 0] + distance_matrix[i, 0]
    for j in range(1, T_expert):
        dtw_matrix[0, j] = dtw_matrix[0, j-1] + distance_matrix[0, j]
    
    for i in range(1, T_user):
        for j in range(1, T_expert):
            cost = distance_matrix[i, j]
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i-1, j],
                dtw_matrix[i, j-1],
                dtw_matrix[i-1, j-1]
            )
    
    # Normalize DTW cost to 0-1 score
    dtw_cost = dtw_matrix[T_user-1, T_expert-1]
    max_possible_cost = np.max(distance_matrix) * max(T_user, T_expert)
    
    if max_possible_cost > 0:
        normalized_cost = dtw_cost / max_possible_cost
        alignment_score = max(0.0, 1.0 - normalized_cost)
    else:
        alignment_score = 1.0
    
    return alignment_score
```

### 3.4 Performance Characteristics

**Time Complexity**: O(T_user × T_expert)
**Space Complexity**: O(T_user × T_expert)

**Optimization Strategies**:
1. **Sakoe-Chiba Band**: Limit warping path to diagonal band
2. **Itakura Parallelogram**: Constrain warping within parallelogram
3. **FastDTW**: Approximate DTW with O(n) complexity

**Typical Performance**:
- 150×150 frames: ~50ms processing time
- 300×300 frames: ~200ms processing time
- Memory usage: 8 bytes × T_user × T_expert for DTW matrix

---

## 4. Level-3 Error Localization

### 4.1 Algorithm Purpose

Level-3 error localization computes detailed frame-wise and joint-wise error metrics between aligned pose sequences. This provides the primary diagnostic output for coaching feedback.

### 4.2 Mathematical Foundation

**Frame-wise Error Computation**:
```
For aligned sequences U (user) and E (expert):
error[t, j] = ||U[t, j] - E[t, j]||₂

where:
t ∈ [0, T-1] (aligned frame index)
j ∈ [0, 16] (joint index)
||·||₂ is Euclidean distance
```

**Joint-wise Aggregation**:
```
For each joint j:
mean_error[j] = (1/T) × Σ(t=0 to T-1) error[t, j]
max_error[j] = max(t=0 to T-1) error[t, j]
std_error[j] = sqrt((1/T) × Σ(t=0 to T-1) (error[t, j] - mean_error[j])²)
```

**Temporal Phase Segmentation**:
```
Phase boundaries:
early_phase = [0, T/3)
mid_phase = [T/3, 2T/3)
late_phase = [2T/3, T)

For each phase p and joint j:
phase_error[p, j] = mean(error[t, j]) for t ∈ phase_p
```

### 4.3 Implementation Specification

```python
def compute_error_metrics(
    aligned_user_poses: np.ndarray,
    aligned_trainer_poses: np.ndarray,
    enable_temporal_phases: bool = True
) -> Dict:
    """
    Compute comprehensive error localization metrics.
    
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
            "std": float(np.std(joint_errors)),
            "median": float(np.median(joint_errors)),
            "percentile_75": float(np.percentile(joint_errors, 75)),
            "percentile_95": float(np.percentile(joint_errors, 95))
        }
    
    # Build result dictionary
    result = {
        "frame_errors": {
            "shape": list(frame_errors.shape),
            "data": frame_errors.tolist(),
            "statistics": {
                "global_mean": float(np.mean(frame_errors)),
                "global_max": float(np.max(frame_errors)),
                "global_std": float(np.std(frame_errors)),
                "global_median": float(np.median(frame_errors))
            }
        },
        "joint_aggregates": joint_aggregates,
        "metadata": {
            "total_frames": T,
            "joints_count": num_joints,
            "coordinate_system": "normalized",
            "error_metric": "euclidean_distance"
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
            phase_statistics = {}
            
            for j, joint_name in enumerate(COCO_17_JOINTS):
                phase_joint_errors = phase_errors[:, j]
                phase_joint_means[joint_name] = float(np.mean(phase_joint_errors))
            
            phase_statistics = {
                "frame_range": f"{start_idx}-{end_idx-1}",
                "duration_frames": end_idx - start_idx,
                "mean_error": float(np.mean(phase_errors)),
                "max_error": float(np.max(phase_errors)),
                "std_error": float(np.std(phase_errors))
            }
            
            temporal_phases[phase] = {
                "joint_means": phase_joint_means,
                "statistics": phase_statistics
            }
        
        result["temporal_phases"] = temporal_phases
        result["metadata"]["phase_boundaries"] = phase_boundaries
    
    return result

def get_joint_ranking(error_metrics: Dict, metric: str = "mean") -> List[Tuple[str, float]]:
    """
    Get joints ranked by error magnitude.
    
    Args:
        error_metrics: Output from compute_error_metrics
        metric: "mean", "max", "std", "median", "percentile_75", "percentile_95"
        
    Returns:
        List of (joint_name, error_value) tuples sorted by error descending
    """
    joint_errors = []
    for joint_name, stats in error_metrics["joint_aggregates"].items():
        if metric in stats:
            joint_errors.append((joint_name, stats[metric]))
        else:
            raise ValueError(f"Metric '{metric}' not found in joint statistics")
    
    return sorted(joint_errors, key=lambda x: x[1], reverse=True)

def get_problematic_frames(error_metrics: Dict, threshold_percentile: float = 95) -> List[int]:
    """
    Identify frames with errors above threshold.
    
    Args:
        error_metrics: Output from compute_error_metrics
        threshold_percentile: Percentile threshold for problematic frames
        
    Returns:
        List of frame indices with high errors
    """
    frame_errors = np.array(error_metrics["frame_errors"]["data"])
    
    # Compute per-frame total error (sum across joints)
    frame_total_errors = np.sum(frame_errors, axis=1)
    
    # Determine threshold
    threshold = np.percentile(frame_total_errors, threshold_percentile)
    
    # Find problematic frames
    problematic_frames = np.where(frame_total_errors > threshold)[0].tolist()
    
    return problematic_frames

def analyze_error_patterns(error_metrics: Dict) -> Dict:
    """
    Analyze error patterns for coaching insights.
    
    Args:
        error_metrics: Output from compute_error_metrics
        
    Returns:
        Dictionary with pattern analysis results
    """
    frame_errors = np.array(error_metrics["frame_errors"]["data"])
    T, num_joints = frame_errors.shape
    
    # Temporal error progression
    temporal_trend = np.mean(frame_errors, axis=1)  # Average error per frame
    
    # Detect increasing/decreasing trends
    from scipy.stats import linregress
    frame_indices = np.arange(T)
    slope, intercept, r_value, p_value, std_err = linregress(frame_indices, temporal_trend)
    
    # Joint correlation analysis
    joint_correlations = np.corrcoef(frame_errors.T)
    
    # Identify joint groups with high correlation
    high_correlation_pairs = []
    for i in range(num_joints):
        for j in range(i+1, num_joints):
            if abs(joint_correlations[i, j]) > 0.7:  # High correlation threshold
                high_correlation_pairs.append({
                    "joint1": COCO_17_JOINTS[i],
                    "joint2": COCO_17_JOINTS[j],
                    "correlation": float(joint_correlations[i, j])
                })
    
    # Error consistency analysis
    joint_consistency = {}
    for j, joint_name in enumerate(COCO_17_JOINTS):
        joint_errors = frame_errors[:, j]
        coefficient_of_variation = np.std(joint_errors) / (np.mean(joint_errors) + 1e-8)
        joint_consistency[joint_name] = {
            "coefficient_of_variation": float(coefficient_of_variation),
            "consistency_level": "high" if coefficient_of_variation < 0.5 else 
                               "medium" if coefficient_of_variation < 1.0 else "low"
        }
    
    return {
        "temporal_analysis": {
            "trend_slope": float(slope),
            "trend_significance": float(p_value),
            "trend_direction": "improving" if slope < -0.001 else 
                             "degrading" if slope > 0.001 else "stable",
            "r_squared": float(r_value ** 2)
        },
        "joint_correlations": {
            "high_correlation_pairs": high_correlation_pairs,
            "correlation_matrix_shape": list(joint_correlations.shape)
        },
        "consistency_analysis": joint_consistency
    }
```

### 4.4 Performance Characteristics

**Time Complexity**: O(T × J)
- T = number of aligned frames
- J = number of joints (17)

**Space Complexity**: O(T × J) for frame error matrix

**Typical Performance**:
- 150 frames: ~5ms processing time
- 300 frames: ~10ms processing time
- Memory usage: 8 bytes × T × J for error matrix

---

## 5. Level-4 Similarity Scoring

### 5.1 Algorithm Purpose

Level-4 similarity scoring computes high-level performance metrics by aggregating error localization results into interpretable scores on a 0-100 scale.

### 5.2 Mathematical Foundation

**Structural Similarity Score**:
```
structural_score = 100 × max(0, 1 - mean_position_error / max_error_threshold)

where:
mean_position_error = mean(frame_errors)
max_error_threshold = 0.1 (normalized coordinates)
```

**Temporal Similarity Score**:
```
For velocity-based temporal analysis:
user_velocities[t] = user_poses[t+1] - user_poses[t]
expert_velocities[t] = expert_poses[t+1] - expert_poses[t]

velocity_errors = ||user_velocities - expert_velocities||₂
temporal_score = 100 × max(0, 1 - mean_velocity_error / max_velocity_threshold)

where:
max_velocity_threshold = 0.05 (normalized coordinates per frame)
```

**Overall Score Computation**:
```
overall_score = w₁ × structural_score + w₂ × temporal_score

Default weights:
w₁ = 0.6 (structural weight)
w₂ = 0.4 (temporal weight)
```

### 5.3 Implementation Specification

```python
def compute_similarity_scores(
    aligned_user_poses: np.ndarray, 
    aligned_expert_poses: np.ndarray,
    config: Dict = None
) -> Dict[str, float]:
    """
    Compute multi-component similarity scores.
    
    Args:
        aligned_user_poses: User pose sequence (T, 17, 2)
        aligned_expert_poses: Expert pose sequence (T, 17, 2)
        config: Scoring configuration parameters
        
    Returns:
        Dictionary with similarity scores
    """
    if config is None:
        config = {
            'max_position_error': 0.1,      # Normalized coordinates
            'max_velocity_error': 0.05,     # Normalized coordinates per frame
            'structural_weight': 0.6,       # Weight for structural component
            'temporal_weight': 0.4,         # Weight for temporal component
            'smoothing_sigma': 1.0          # Gaussian smoothing for velocities
        }
    
    # Structural similarity (position accuracy)
    position_errors = np.linalg.norm(
        aligned_user_poses - aligned_expert_poses, axis=2
    )
    mean_position_error = np.mean(position_errors)
    
    structural_score = 100.0 * max(
        0.0, 
        1.0 - mean_position_error / config['max_position_error']
    )
    
    # Temporal similarity (motion consistency)
    if aligned_user_poses.shape[0] > 1:
        # Compute velocities
        user_velocities = np.diff(aligned_user_poses, axis=0)
        expert_velocities = np.diff(aligned_expert_poses, axis=0)
        
        # Apply smoothing to reduce noise
        if config['smoothing_sigma'] > 0:
            user_velocities = smooth_velocities(user_velocities, config['smoothing_sigma'])
            expert_velocities = smooth_velocities(expert_velocities, config['smoothing_sigma'])
        
        # Compute velocity errors
        velocity_errors = np.linalg.norm(user_velocities - expert_velocities, axis=2)
        mean_velocity_error = np.mean(velocity_errors)
        
        temporal_score = 100.0 * max(
            0.0,
            1.0 - mean_velocity_error / config['max_velocity_error']
        )
    else:
        temporal_score = 100.0  # Single frame case
    
    # Overall score (weighted combination)
    overall_score = (
        config['structural_weight'] * structural_score + 
        config['temporal_weight'] * temporal_score
    )
    
    # Additional component scores
    component_scores = compute_component_scores(
        aligned_user_poses, 
        aligned_expert_poses, 
        config
    )
    
    return {
        "structural": float(structural_score),
        "temporal": float(temporal_score),
        "overall": float(overall_score),
        **component_scores
    }

def smooth_velocities(velocities: np.ndarray, sigma: float) -> np.ndarray:
    """Apply Gaussian smoothing to velocity sequences."""
    from scipy import ndimage
    
    T, num_joints, num_coords = velocities.shape
    smoothed = velocities.copy()
    
    for j in range(num_joints):
        for c in range(num_coords):
            smoothed[:, j, c] = ndimage.gaussian_filter1d(
                velocities[:, j, c], 
                sigma=sigma, 
                mode='nearest'
            )
    
    return smoothed

def compute_component_scores(
    aligned_user_poses: np.ndarray,
    aligned_expert_poses: np.ndarray,
    config: Dict
) -> Dict[str, float]:
    """Compute additional component-specific scores."""
    
    # Joint group analysis
    joint_groups = {
        'head': [0, 1, 2, 3, 4],  # nose, eyes, ears
        'torso': [5, 6, 11, 12],  # shoulders, hips
        'arms': [7, 8, 9, 10],    # elbows, wrists
        'legs': [13, 14, 15, 16]  # knees, ankles
    }
    
    component_scores = {}
    
    for group_name, joint_indices in joint_groups.items():
        # Extract joint group poses
        user_group = aligned_user_poses[:, joint_indices, :]
        expert_group = aligned_expert_poses[:, joint_indices, :]
        
        # Compute group-specific error
        group_errors = np.linalg.norm(user_group - expert_group, axis=2)
        mean_group_error = np.mean(group_errors)
        
        # Convert to score
        group_score = 100.0 * max(
            0.0,
            1.0 - mean_group_error / config['max_position_error']
        )
        
        component_scores[f"{group_name}_accuracy"] = float(group_score)
    
    # Movement fluidity (acceleration consistency)
    if aligned_user_poses.shape[0] > 2:
        user_accelerations = np.diff(aligned_user_poses, n=2, axis=0)
        expert_accelerations = np.diff(aligned_expert_poses, n=2, axis=0)
        
        acceleration_errors = np.linalg.norm(
            user_accelerations - expert_accelerations, axis=2
        )
        mean_acceleration_error = np.mean(acceleration_errors)
        
        fluidity_score = 100.0 * max(
            0.0,
            1.0 - mean_acceleration_error / (2 * config['max_velocity_error'])
        )
        
        component_scores["movement_fluidity"] = float(fluidity_score)
    else:
        component_scores["movement_fluidity"] = 100.0
    
    # Pose stability (variance analysis)
    user_variance = np.var(aligned_user_poses, axis=0)
    expert_variance = np.var(aligned_expert_poses, axis=0)
    
    variance_similarity = 1.0 - np.mean(np.abs(user_variance - expert_variance))
    stability_score = 100.0 * max(0.0, variance_similarity)
    
    component_scores["pose_stability"] = float(stability_score)
    
    return component_scores

def compute_confidence_intervals(
    aligned_user_poses: np.ndarray,
    aligned_expert_poses: np.ndarray,
    n_bootstrap: int = 1000
) -> Dict[str, Dict[str, float]]:
    """
    Compute confidence intervals for scores using bootstrap sampling.
    
    Args:
        aligned_user_poses: User pose sequence
        aligned_expert_poses: Expert pose sequence
        n_bootstrap: Number of bootstrap samples
        
    Returns:
        Dictionary with confidence intervals for each score
    """
    T = aligned_user_poses.shape[0]
    bootstrap_scores = []
    
    for _ in range(n_bootstrap):
        # Bootstrap sample frames
        sample_indices = np.random.choice(T, size=T, replace=True)
        
        user_sample = aligned_user_poses[sample_indices]
        expert_sample = aligned_expert_poses[sample_indices]
        
        # Compute scores for sample
        sample_scores = compute_similarity_scores(user_sample, expert_sample)
        bootstrap_scores.append(sample_scores)
    
    # Compute confidence intervals
    confidence_intervals = {}
    score_keys = bootstrap_scores[0].keys()
    
    for key in score_keys:
        values = [scores[key] for scores in bootstrap_scores]
        confidence_intervals[key] = {
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "ci_lower": float(np.percentile(values, 2.5)),
            "ci_upper": float(np.percentile(values, 97.5)),
            "median": float(np.median(values))
        }
    
    return confidence_intervals
```

### 5.4 Performance Characteristics

**Time Complexity**: O(T × J)
**Space Complexity**: O(T × J) for intermediate calculations

**Typical Performance**:
- 150 frames: ~3ms processing time
- 300 frames: ~6ms processing time
- Bootstrap confidence intervals: +100ms per 1000 samples

---

## 6. Pose Extraction Algorithms

### 6.1 MediaPipe to COCO-17 Conversion

**Joint Mapping**:
```python
MP_TO_COCO17_MAPPING = {
    0: 0,   # nose -> nose
    2: 1,   # left_eye_inner -> left_eye
    5: 2,   # right_eye_inner -> right_eye
    7: 3,   # left_ear -> left_ear
    8: 4,   # right_ear -> right_ear
    11: 5,  # left_shoulder -> left_shoulder
    12: 6,  # right_shoulder -> right_shoulder
    13: 7,  # left_elbow -> left_elbow
    14: 8,  # right_elbow -> right_elbow
    15: 9,  # left_wrist -> left_wrist
    16: 10, # right_wrist -> right_wrist
    23: 11, # left_hip -> left_hip
    24: 12, # right_hip -> right_hip
    25: 13, # left_knee -> left_knee
    26: 14, # right_knee -> right_knee
    27: 15, # left_ankle -> left_ankle
    28: 16  # right_ankle -> right_ankle
}
```

### 6.2 Person Detection and Tracking

**YOLO-based Person Detection**:
```python
def detect_and_track_person(frame: np.ndarray, yolo_model, tracker_state: Dict) -> Optional[np.ndarray]:
    """
    Detect and track the most active person (raider) in frame.
    
    Args:
        frame: Input video frame (H, W, 3)
        yolo_model: YOLO detection model
        tracker_state: Tracking state dictionary
        
    Returns:
        Bounding box [x1, y1, x2, y2] or None if no person detected
    """
    # Run YOLO detection
    results = yolo_model.track(
        frame,
        persist=True,
        classes=[0],  # person class
        tracker="bytetrack.yaml",
        verbose=False
    )
    
    if not results or not results[0].boxes:
        return None
    
    # Extract person detections
    boxes = results[0].boxes
    person_detections = []
    
    for i, box in enumerate(boxes):
        if box.id is not None:  # Tracked person
            person_detections.append({
                'id': int(box.id.item()),
                'bbox': box.xyxy[0].cpu().numpy(),
                'confidence': float(box.conf.item())
            })
    
    if not person_detections:
        return None
    
    # Select most active person (raider)
    selected_person = select_most_active_person(person_detections, tracker_state)
    
    return selected_person['bbox'] if selected_person else None

def select_most_active_person(detections: List[Dict], tracker_state: Dict) -> Optional[Dict]:
    """Select person with highest motion activity."""
    if not detections:
        return None
    
    # Update tracking history
    for detection in detections:
        person_id = detection['id']
        bbox_center = get_bbox_center(detection['bbox'])
        
        if person_id not in tracker_state:
            tracker_state[person_id] = {'positions': [], 'motion_score': 0.0}
        
        tracker_state[person_id]['positions'].append(bbox_center)
        
        # Keep only recent positions (last 30 frames)
        if len(tracker_state[person_id]['positions']) > 30:
            tracker_state[person_id]['positions'].pop(0)
    
    # Compute motion scores
    for person_id in tracker_state:
        positions = tracker_state[person_id]['positions']
        if len(positions) >= 5:
            # Compute total displacement
            total_motion = sum(
                np.linalg.norm(np.array(positions[i]) - np.array(positions[i-1]))
                for i in range(1, len(positions))
            )
            tracker_state[person_id]['motion_score'] = total_motion
        else:
            tracker_state[person_id]['motion_score'] = 0.0
    
    # Select person with highest motion score among current detections
    best_person = None
    max_motion = 0.0
    
    for detection in detections:
        person_id = detection['id']
        motion_score = tracker_state.get(person_id, {}).get('motion_score', 0.0)
        
        if motion_score > max_motion:
            max_motion = motion_score
            best_person = detection
    
    return best_person

def get_bbox_center(bbox: np.ndarray) -> Tuple[float, float]:
    """Get center point of bounding box."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)
```

---

## 7. Performance Analysis

### 7.1 Computational Complexity Summary

| Algorithm | Time Complexity | Space Complexity | Typical Runtime |
|-----------|----------------|------------------|-----------------|
| Level-1 Cleaning | O(T × J × C) | O(T × J × C) | 10-20ms |
| Level-2 DTW | O(T₁ × T₂) | O(T₁ × T₂) | 50-200ms |
| Level-3 Error Analysis | O(T × J) | O(T × J) | 5-10ms |
| Level-4 Scoring | O(T × J) | O(T × J) | 3-6ms |
| **Total Pipeline** | **O(T₁ × T₂)** | **O(T₁ × T₂)** | **~300ms** |

### 7.2 Memory Usage Analysis

**Peak Memory Usage**:
```
For typical sequences (T₁=150, T₂=150):
- DTW matrix: 150 × 150 × 8 bytes = 180 KB
- Pose data: 2 × 150 × 17 × 2 × 8 bytes = 81.6 KB
- Error matrices: 150 × 17 × 8 bytes = 20.4 KB
- Total peak usage: ~300 KB
```

### 7.3 Optimization Strategies

**Level-2 DTW Optimization**:
1. **Sakoe-Chiba Band**: Limit warping to ±20% of diagonal
2. **Early Termination**: Stop if DTW cost exceeds threshold
3. **Coarse-to-Fine**: Multi-resolution DTW for long sequences

**Memory Optimization**:
1. **Streaming Processing**: Process frames in batches
2. **In-place Operations**: Reuse arrays where possible
3. **Sparse Matrices**: Use sparse representation for large DTW matrices

---

## 8. Mathematical Foundations

### 8.1 Distance Metrics

**Euclidean Distance** (Primary):
```
d(p₁, p₂) = √(Σᵢ(p₁ᵢ - p₂ᵢ)²)

Properties:
- Metric space: d(x,y) ≥ 0, d(x,x) = 0, d(x,y) = d(y,x), triangle inequality
- Sensitive to coordinate scaling
- Appropriate for normalized pose coordinates
```

**Manhattan Distance** (Alternative):
```
d(p₁, p₂) = Σᵢ|p₁ᵢ - p₂ᵢ|

Properties:
- Less sensitive to outliers
- Computationally efficient
- May be preferred for joint-wise analysis
```

### 8.2 Statistical Measures

**Coefficient of Variation**:
```
CV = σ/μ

where:
σ = standard deviation
μ = mean

Interpretation:
CV < 0.5: Low variability (consistent performance)
0.5 ≤ CV < 1.0: Medium variability
CV ≥ 1.0: High variability (inconsistent performance)
```

**Percentile-based Robust Statistics**:
```
Robust measures less sensitive to outliers:
- Median instead of mean
- Interquartile range (IQR) instead of standard deviation
- 95th percentile for outlier detection
```

### 8.3 Temporal Analysis

**Velocity Computation**:
```
v[t] = (p[t+1] - p[t]) / Δt

For normalized time (Δt = 1):
v[t] = p[t+1] - p[t]
```

**Acceleration Computation**:
```
a[t] = (v[t+1] - v[t]) / Δt = p[t+2] - 2p[t+1] + p[t]
```

**Smoothing Kernels**:
```
Gaussian kernel: G(x) = (1/√(2πσ²)) × exp(-x²/(2σ²))
Moving average: MA(x) = (1/w) × Σᵢ₌₋w/₂^w/₂ x[i]
Savitzky-Golay: Polynomial fitting in local windows
```

---

## 9. Conclusion

This Algorithm Design Document provides comprehensive mathematical foundations and implementation specifications for all algorithms in the AR-Based Kabaddi Ghost Trainer pipeline. Key design principles include:

1. **Mathematical Rigor**: All algorithms have well-defined mathematical foundations
2. **Computational Efficiency**: Optimized for real-time processing requirements
3. **Numerical Stability**: Robust to floating-point precision and edge cases
4. **Semantic Clarity**: Each level has distinct analytical purpose
5. **Extensibility**: Modular design allows for algorithm improvements

The algorithms collectively enable accurate pose analysis, temporal synchronization, detailed error localization, and interpretable performance scoring for kabaddi movement assessment.

---

**Document Control**:
- Version: 1.0
- Last Updated: 2024-01-15
- Next Review: 2024-04-15
- Approval: Algorithm Design Team