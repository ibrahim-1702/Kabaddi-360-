# Level 3: Joint Error Computation - Algorithm Analysis

## Overview
Level 3 computes numeric error metrics between DTW-aligned expert and user poses. This is pure data analysis - no visualization, no scoring, just structured error statistics.

---

## Algorithm 3.1: Joint Error Computation
**File**: [`compute_joint_errors.py`](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/review1/visualization/level3/compute_joint_errors.py)

### Purpose
Quantify spatial deviations between aligned expert and user movements using Euclidean distance.

### Input
- Expert aligned: `expert_aligned_user{N}.npy` (T, 17, 2)
- User aligned: `user_{N}_aligned.npy` (T, 17, 2)

### Output
- Error statistics: `joint_errors.json`

---

## Core Algorithms

### 3.1.1: Frame-wise Joint-wise Euclidean Error
**Algorithm**: L2 Norm Distance Computation

**Mathematical Formula**:
```
Given aligned sequences:
  Expert: E(t, j) = (x_E, y_E) for frame t, joint j
  User:   U(t, j) = (x_U, y_U) for frame t, joint j

Error at frame t, joint j:
  error(t, j) = ||E(t, j) - User(t, j)||₂
              = √[(x_E - x_U)² + (y_E - y_U)²]

Result: Error matrix of shape (T, 17)
```

**Why Euclidean Distance?**
1. **Normalized coordinates**: Level-1 cleaning already removed scale/translation
2. **Spatial deviation**: Measures how far apart corresponding joints are
3. **Simple interpretation**: Direct physical meaning (distance in normalized space)
4. **Temporal independence**: DTW already handled timing; this measures ONLY spatial error

**Implementation**:
```python
def compute_joint_errors(expert_poses: np.ndarray, user_poses: np.ndarray) -> np.ndarray:
    T, num_joints, _ = expert_poses.shape
    errors = np.zeros((T, num_joints))
    
    for t in range(T):
        for j in range(num_joints):
            # Compute Euclidean distance for joint j at frame t
            diff = expert_poses[t, j, :] - user_poses[t, j, :]
            errors[t, j] = np.linalg.norm(diff)
    
    return errors  # Shape: (T, 17)
```

**Example**:
```
Frame 0, Left Knee (joint 13):
  Expert: (0.45, 0.78)
  User:   (0.52, 0.71)
  
  diff = (0.45 - 0.52, 0.78 - 0.71) = (-0.07, 0.07)
  error = √[(-0.07)² + (0.07)²] = √[0.0049 + 0.0049] = √0.0098 ≈ 0.099
```

---

### 3.1.2: Joint-wise Temporal Aggregation
**Algorithm**: Statistical Aggregation Across Time

**Purpose**: Summarize each joint's performance over entire sequence

**Mathematical Formulas**:
```
For joint j ∈ [0, 16]:
  
  Joint errors over time: {error(0,j), error(1,j), ..., error(T-1,j)}
  
  Statistics:
    mean_error(j) = (1/T) × Σ error(t, j)  for t ∈ [0, T-1]
    
    max_error(j) = max{error(t, j)}  for t ∈ [0, T-1]
    
    std_error(j) = √[(1/T) × Σ (error(t, j) - mean_error(j))²]
```

**Implementation**:
```python
def aggregate_joint_stats(errors: np.ndarray) -> Dict[str, Dict[str, float]]:
    joint_stats = {}
    
    for joint_idx in range(17):
        joint_name = COCO17_JOINT_NAMES[joint_idx]
        joint_errors = errors[:, joint_idx]  # All frames for this joint
        
        joint_stats[joint_name] = {
            "mean": float(np.nanmean(joint_errors)),  # Temporal average
            "max": float(np.nanmax(joint_errors)),    # Worst frame
            "std": float(np.nanstd(joint_errors))     # Consistency
        }
    
    return joint_stats
```

**Interpretation**:
- **mean**: Overall accuracy for this joint
- **max**: Worst deviation (peak error)
- **std**: Consistency (low std = stable performance)

**Example Output**:
```json
{
  "left_knee": {
    "mean": 0.042,  // Average error across all frames
    "max": 0.089,   // Maximum error in any single frame
    "std": 0.018    // Variation in errors
  },
  "right_shoulder": {
    "mean": 0.055,
    "max": 0.112,
    "std": 0.025
  }
}
```

---

### 3.1.3: Frame-wise Spatial Aggregation
**Algorithm**: Statistical Aggregation Across Joints

**Purpose**: Summarize overall body alignment at each frame

**Mathematical Formulas**:
```
For frame t ∈ [0, T-1]:
  
  Joint errors at frame t: {error(t, 0), error(t, 1), ..., error(t, 16)}
  
  Statistics:
    mean_error(t) = (1/17) × Σ error(t, j)  for j ∈ [0, 16]
    
    max_error(t) = max{error(t, j)}  for j ∈ [0, 16]
```

**Implementation**:
```python
def aggregate_frame_stats(errors: np.ndarray) -> Dict[int, Dict[str, float]]:
    T = errors.shape[0]
    frame_stats = {}
    
    for t in range(T):
        frame_errors = errors[t, :]  # All joints at this frame
        
        frame_stats[t] = {
            "mean_error": float(np.nanmean(frame_errors)),  # Average across body
            "max_error": float(np.nanmax(frame_errors))     # Worst joint
        }
    
    return frame_stats
```

**Interpretation**:
- **mean_error**: Overall form accuracy at this moment
- **max_error**: Most misaligned joint at this moment

**Use Case**: Identify which frames have the worst overall form

**Example Output**:
```json
{
  "0": {
    "mean_error": 0.035,  // Frame 0: good overall alignment
    "max_error": 0.078
  },
  "45": {
    "mean_error": 0.091,  // Frame 45: poor overall alignment
    "max_error": 0.156
  }
}
```

---

### 3.1.4: Temporal Phase Segmentation
**Algorithm**: Tripartite Movement Phase Analysis

**Purpose**: Analyze error progression through early/mid/late stages of movement

**Phase Definition**:
```
Given T total frames:
  
  early_end = ⌊T / 3⌋
  mid_end = ⌊2T / 3⌋
  
  Phases:
    Early: frames [0, early_end)         (first 33%)
    Mid:   frames [early_end, mid_end)   (middle 33%)
    Late:  frames [mid_end, T)           (final 33%)
```

**Mathematical Formula**:
```
For each phase p ∈ {early, mid, late}:
  For each joint j ∈ [0, 16]:
    
    phase_error(p, j) = (1/|frames_in_phase|) × Σ error(t, j)
                        for t ∈ frames_in_phase
```

**Implementation**:
```python
def compute_phase_stats(errors: np.ndarray) -> Dict[str, Dict[str, float]]:
    T = errors.shape[0]
    
    # Define phase boundaries
    early_end = T // 3
    mid_end = 2 * T // 3
    
    phase_stats = {}
    
    # Early phase [0, T//3)
    early_errors = errors[0:early_end, :]
    phase_stats["early"] = {}
    for joint_idx in range(17):
        joint_name = COCO17_JOINT_NAMES[joint_idx]
        phase_stats["early"][joint_name] = float(np.nanmean(early_errors[:, joint_idx]))
    
    # Mid phase [T//3, 2*T//3)
    mid_errors = errors[early_end:mid_end, :]
    phase_stats["mid"] = {}
    for joint_idx in range(17):
        joint_name = COCO17_JOINT_NAMES[joint_idx]
        phase_stats["mid"][joint_name] = float(np.nanmean(mid_errors[:, joint_idx]))
    
    # Late phase [2*T//3, T)
    late_errors = errors[mid_end:, :]
    phase_stats["late"] = {}
    for joint_idx in range(17):
        joint_name = COCO17_JOINT_NAMES[joint_idx]
        phase_stats["late"][joint_name] = float(np.nanmean(late_errors[:, joint_idx]))
    
    return phase_stats
```

**Example**: Movement with 120 frames
```
Early: frames [0, 40)    → first 33%
Mid:   frames [40, 80)   → middle 33%
Late:  frames [80, 120)  → final 33%
```

**Interpretation Patterns**:

1. **Increasing Error**: Early < Mid < Late
   - Possible cause: Fatigue, form breakdown
   - Example: `left_knee: {early: 0.03, mid: 0.05, late: 0.08}`

2. **Decreasing Error**: Early > Mid > Late
   - Possible cause: Learning/warmup, improved execution
   - Example: `right_shoulder: {early: 0.07, mid: 0.05, late: 0.03}`

3. **Mid-Phase Spike**: Early < Late, Mid high
   - Possible cause: Difficult middle portion
   - Example: `left_ankle: {early: 0.04, mid: 0.09, late: 0.05}`

4. **Consistent Error**: Early ≈ Mid ≈ Late
   - Interpretation: Persistent technique issue
   - Example: `right_hip: {early: 0.06, mid: 0.06, late: 0.06}`

**Example Output**:
```json
{
  "early": {
    "left_knee": 0.040,
    "right_knee": 0.038,
    ...
  },
  "mid": {
    "left_knee": 0.055,
    "right_knee": 0.042,
    ...
  },
  "late": {
    "left_knee": 0.068,
    "right_knee": 0.045,
    ...
  }
}
```

**Design Rationale**:
- **Early errors**: Setup/initialization issues
- **Mid errors**: Core execution technique
- **Late errors**: Endurance/consistency
- Enables temporal coaching feedback (e.g., "left knee collapses in late phase")

---

### 3.1.5: Frame-Joint Error Export
**Algorithm**: Complete Error Matrix Serialization

**Purpose**: Enable per-frame per-joint visualization without recomputation

**Data Structure**:
```
For each frame t ∈ [0, T-1]:
  For each joint j ∈ [0, 16]:
    Store: error(t, j)
```

**Implementation**:
```python
def export_frame_joint_errors(errors: np.ndarray) -> Dict[int, Dict[str, float]]:
    T, num_joints = errors.shape
    frame_joint_errors = {}
    
    for t in range(T):
        frame_joint_errors[t] = {}
        for j in range(num_joints):
            joint_name = COCO17_JOINT_NAMES[j]
            frame_joint_errors[t][joint_name] = float(errors[t, j])
    
    return frame_joint_errors
```

**Example Output**:
```json
{
  "0": {
    "nose": 0.042,
    "left_eye": 0.031,
    "right_eye": 0.029,
    ...
    "left_knee": 0.068,
    ...
  },
  "1": {
    "nose": 0.045,
    "left_eye": 0.033,
    ...
  }
}
```

**Use Case**: Level-3 visualization can color-code joints based on error without recalculating

---

## Complete JSON Output Schema

```json
{
  "metadata": {
    "num_frames": 115,
    "num_joints": 17,
    "alignment": "DTW_pelvis_based",
    "expert_path": "poses/expert_aligned_user1.npy",
    "user_path": "poses/user_1_aligned.npy"
  },
  
  "joint_statistics": {
    "nose": {"mean": 0.042, "max": 0.089, "std": 0.018},
    "left_eye": {"mean": 0.035, "max": 0.078, "std": 0.015},
    ...
    // All 17 joints
  },
  
  "frame_statistics": {
    "0": {"mean_error": 0.035, "max_error": 0.078},
    "1": {"mean_error": 0.038, "max_error": 0.082},
    ...
    // All T frames
  },
  
  "phase_statistics": {
    "early": {
      "nose": 0.040,
      "left_eye": 0.033,
      ...
    },
    "mid": {
      "nose": 0.048,
      "left_eye": 0.036,
      ...
    },
    "late": {
      "nose": 0.039,
      "left_eye": 0.035,
      ...
    }
  },
  
  "frame_joint_errors": {
    "0": {
      "nose": 0.042,
      "left_eye": 0.031,
      ...
    },
    ...
    // All T frames × 17 joints
  }
}
```

---

## Error Computation Properties

### Why Euclidean Distance?
1. **Post-normalization**: Level-1 cleaned poses are:
   - Translation invariant (pelvis-centered)
   - Scale invariant (torso-normalized)
2. **Post-alignment**: DTW removed temporal differences
3. **Remaining deviation**: Pure spatial form error
4. **Interpretability**: Direct geometric meaning

### Mathematical Properties
- **Non-negative**: error(t, j) ≥ 0
- **Zero-minimal**: error(t, j) = 0 ⟺ perfect alignment
- **Symmetric**: ||E - U|| = ||U - E||
- **Triangle inequality**: Satisfies metric space properties

### Error Range
```
Typical values in normalized space:
  - Excellent: < 0.05
  - Good: 0.05 - 0.10
  - Fair: 0.10 - 0.20
  - Poor: > 0.20

These thresholds determined empirically from training data.
```

---

## Statistical Aggregations Summary

| Aggregation Type | Dimension | Formula | Purpose |
|-----------------|-----------|---------|---------|
| **Joint-wise Temporal** | Per joint across time | mean, max, std | Overall joint performance |
| **Frame-wise Spatial** | Per frame across joints | mean, max | Overall form at each moment |
| **Phase-wise** | Per joint per phase | mean | Temporal progression analysis |
| **Frame-Joint Export** | Complete matrix | raw values | Visualization support |

---

## Data Flow

```
Expert Aligned (T, 17, 2) ──┐
                            ├──→ Compute Euclidean Errors ──→ Error Matrix (T, 17)
User Aligned (T, 17, 2) ────┘                                        │
                                                                     ├──→ Joint Stats (17 joints)
                                                                     ├──→ Frame Stats (T frames)
                                                                     ├──→ Phase Stats (3 phases × 17 joints)
                                                                     └──→ Frame-Joint Errors (T × 17)
                                                                            │
                                                                            ↓
                                                                    joint_errors.json
```

**Parameters**:
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Distance Metric | Euclidean L2 norm | Spatial deviation |
| Phase Count | 3 (early/mid/late) | Temporal progression |
| Phase Split | 33% each | Balanced analysis |
| NaN Handling | nanmean, nanmax | Missing joint robustness |
| Joint Names | COCO-17 standard | Compatibility |

