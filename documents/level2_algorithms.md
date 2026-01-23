# Level 2: Temporal Alignment (DTW) - Algorithm Analysis

## Overview
Level 2 implements Dynamic Time Warping (DTW) to temporally align expert and user motion sequences, enabling frame-by-frame comparison despite different execution speeds.

---

## Algorithm 2.1: Dynamic Time Warping (DTW) Alignment
**File**: [`visualize_level2.py`](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/review1/level2/visualize_level2.py)

### Purpose
Align expert and user movement sequences in time domain to isolate spatial (form) errors from temporal (timing) differences.

### Input
- Expert pose: `poses/expert_pose.npy` (T_expert, 17, 2)
- User poses: `poses/user_{1-4}_pose.npy` (T_user, 17, 2)

### Output
- Aligned videos: `Outputs/output_temporal_alignment_user{1-4}.mp4`
- Aligned pose sequences: `aligned_poses/expert_aligned_user{N}.npy` and `user_{N}_aligned.npy`

---

## Core Algorithms

### 2.1.1: Pelvis Trajectory Extraction
**Algorithm**: Anatomical Anchor Point Selection

**Purpose**: Use pelvis as temporal synchronization anchor (most stable body point)

**Mathematical Formula**:
```
Given pose sequence P with shape (T, 17, 2):
  LEFT_HIP = joint index 11
  RIGHT_HIP = joint index 12

For each frame t:
  pelvis(t) = (P[t, LEFT_HIP] + P[t, RIGHT_HIP]) / 2
  
Result: pelvis_trajectory with shape (T, 2)
```

**Implementation**:
```python
def extract_pelvis(poses: np.ndarray) -> np.ndarray:
    left_hip = poses[:, 11, :]   # (T, 2)
    right_hip = poses[:, 12, :]  # (T, 2)
    pelvis = (left_hip + right_hip) * 0.5
    return pelvis  # (T, 2)
```

**Rationale**:
- Pelvis is anatomically central and stable
- Less affected by limb variation than individual joints
- Represents overall body position/trajectory
- Provides clear temporal progression signal

---

### 2.1.2: DTW Cost Matrix Computation
**Algorithm**: Dynamic Programming for Sequence Alignment

**Mathematical Foundation**:

Given two sequences:
- Expert pelvis: **E** = {e₁, e₂, ..., e_m} where m = T_expert
- User pelvis: **U** = {u₁, u₂, ..., u_n} where n = T_user

**Distance Metric**: Euclidean Distance
```
d(eᵢ, uⱼ) = ||eᵢ - uⱼ|| = √[(eᵢ.x - uⱼ.x)² + (eᵢ.y - uⱼ.y)²]
```

**Cost Matrix**: D is (m+1) × (n+1) matrix

**Initialization**:
```
D[0, 0] = 0
D[i, 0] = ∞ for i > 0
D[0, j] = ∞ for j > 0
```

**Recurrence Relation**:
```
For i ∈ [1, m], j ∈ [1, n]:
  
  D[i, j] = d(eᵢ₋₁, uⱼ₋₁) + min{
    D[i-1, j],     # Insert expert frame (vertical move)
    D[i, j-1],     # Insert user frame (horizontal move)
    D[i-1, j-1]    # Match frames (diagonal move)
  }
```

**Interpretation**:
- **Diagonal step**: Both sequences advance (ideal match)
- **Vertical step**: Expert frame repeats (user slower)
- **Horizontal step**: User frame repeats (user faster)

**Implementation**:
```python
def dtw_align(expert_pelvis: np.ndarray, user_pelvis: np.ndarray):
    T_expert = len(expert_pelvis)
    T_user = len(user_pelvis)
    
    # Initialize cost matrix with infinity
    cost_matrix = np.full((T_expert + 1, T_user + 1), np.inf)
    cost_matrix[0, 0] = 0
    
    # Fill cost matrix
    for i in range(1, T_expert + 1):
        for j in range(1, T_user + 1):
            # Euclidean distance between pelvis positions
            distance = np.linalg.norm(expert_pelvis[i - 1] - user_pelvis[j - 1])
            
            # DTW recurrence
            cost_matrix[i, j] = distance + min(
                cost_matrix[i - 1, j],      # insertion (vertical)
                cost_matrix[i, j - 1],      # deletion (horizontal)
                cost_matrix[i - 1, j - 1]   # match (diagonal)
            )
    
    return cost_matrix
```

**Computational Complexity**:
- Time: O(m × n)
- Space: O(m × n)

---

### 2.1.3: Optimal Path Backtracking
**Algorithm**: Reverse Traceback from Bottom-Right

**Purpose**: Find optimal alignment path from filled cost matrix

**Mathematical Foundation**:
```
Start at: (m, n) (bottom-right corner)
Goal: Reach (0, 0) (top-left corner)

At each step (i, j):
  1. Record current position: path_expert.append(i-1), path_user.append(j-1)
  2. Move to minimum-cost predecessor:
     
     candidates = [
       D[i-1, j-1],  # diagonal
       D[i-1, j],    # up
       D[i, j-1]     # left
     ]
     
     next_direction = argmin(candidates)
     
     if next_direction == 0: (i, j) ← (i-1, j-1)  # diagonal
     if next_direction == 1: (i, j) ← (i-1, j)    # up
     if next_direction == 2: (i, j) ← (i, j-1)    # left

Continue until (i==0 AND j==0)
```

**Implementation**:
```python
# Backtrack to find optimal path
path_expert = []
path_user = []

i, j = T_expert, T_user

while i > 0 and j > 0:
    # Record current alignment
    path_expert.append(i - 1)
    path_user.append(j - 1)
    
    # Find which direction we came from
    candidates = [
        cost_matrix[i - 1, j - 1],  # diagonal
        cost_matrix[i - 1, j],      # up
        cost_matrix[i, j - 1]       # left
    ]
    min_idx = np.argmin(candidates)
    
    if min_idx == 0:
        i -= 1
        j -= 1
    elif min_idx == 1:
        i -= 1
    else:
        j -= 1

# Reverse paths (we backtracked from end to start)
path_expert.reverse()
path_user.reverse()

return path_expert, path_user
```

**Output**:
- `path_expert`: List of expert frame indices in aligned sequence
- `path_user`: List of user frame indices in aligned sequence
- Both lists have same length T_aligned

**Example**:
```
Expert: 100 frames
User: 120 frames

After DTW:
  path_expert = [0, 1, 1, 2, 3, 3, 4, ...]  (length: 115)
  path_user   = [0, 1, 2, 3, 4, 5, 5, ...]  (length: 115)
  
Notice: frame 1 of expert repeated (user slower here)
        frame 5 of user repeated (user faster here)
```

---

### 2.1.4: Aligned Sequence Generation
**Algorithm**: Index-Based Pose Extraction

**Purpose**: Create synchronized pose sequences using DTW alignment indices

**Mathematical Formula**:
```
Given:
  - Expert poses: E(t) for t ∈ [0, T_expert-1]
  - User poses: U(t) for t ∈ [0, T_user-1]
  - Alignment path: {(e₀,u₀), (e₁,u₁), ..., (e_k,u_k)} where k = T_aligned-1

Create aligned sequences:
  E_aligned[i] = E[eᵢ]
  U_aligned[i] = U[uᵢ]
  
for i ∈ [0, k]
```

**Implementation**:
```python
def create_aligned_sequences(
    expert_poses: np.ndarray,    # (T_expert, 17, 2)
    user_poses: np.ndarray,      # (T_user, 17, 2)
    expert_indices: List[int],   # T_aligned elements
    user_indices: List[int]      # T_aligned elements
) -> Tuple[np.ndarray, np.ndarray]:
    
    aligned_expert = expert_poses[expert_indices]  # (T_aligned, 17, 2)
    aligned_user = user_poses[user_indices]        # (T_aligned, 17, 2)
    
    return aligned_expert, aligned_user
```

**Key Property**: 
```
aligned_expert.shape[0] == aligned_user.shape[0] == T_aligned
```

This enables frame-by-frame comparison in subsequent levels.

---

## DTW Algorithm Properties

### Advantages
1. **Temporal Alignment**: Automatically handles speed variations
2. **Non-Linear Warping**: Can compress/expand different motion phases independently
3. **Optimal Solution**: Guaranteed to find minimum-cost alignment
4. **Robust**: Works even with significant timing differences

### Constraints
1. **Monotonicity**: Time cannot go backwards (i and j never decrease)
2. **Boundary Conditions**: Must start at (0,0) and end at (m,n)
3. **Local Constraint**: Each step moves by at most 1 in either direction

### Distance Metric Choice
**Euclidean Distance** used because:
- Simple and interpretable
- Pelvis is 2D point (x, y coordinates)
- Normalized pose data (scale-invariant from Level-1)
- Computational efficiency

---

## Visualization Components

### 2.2.1: Pose Scaling for Display
**Algorithm**: Normalized to Canvas Coordinates

**Formula**:
```
Given normalized pose (values ≈ [-2, 2] after centering):
  canvas_size = 600 pixels
  scale_factor = canvas_size / 4 = 150
  center = canvas_size / 2 = 300
  
For each joint (x, y):
  x_screen = x × scale_factor + center
  y_screen = y × scale_factor + center
```

**Implementation**:
```python
def scale_pose_for_display(pose: np.ndarray, canvas_size: int = 600) -> np.ndarray:
    scale_factor = canvas_size // 4
    center_x = canvas_size // 2
    center_y = canvas_size // 2
    
    scaled_pose = np.zeros_like(pose)
    for j in range(17):
        if not np.isnan(pose[j]).any():
            x = int(pose[j, 0] * scale_factor + center_x)
            y = int(pose[j, 1] * scale_factor + center_y)
            scaled_pose[j] = [x, y]
    
    return scaled_pose
```

---

### 2.2.2: Skeleton Rendering
**Algorithm**: COCO-17 Connection Drawing

**Skeleton Connections**:
```python
COCO_CONNECTIONS = [
    (5, 6),                    # shoulders
    (5, 7), (7, 9),           # left arm
    (6, 8), (8, 10),          # right arm
    (11, 12),                 # hips
    (11, 13), (13, 15),       # left leg
    (12, 14), (14, 16),       # right leg
    (5, 11),                  # left torso
    (6, 12),                  # right torso
]
```

**Rendering Logic**:
```python
def draw_skeleton(frame, pose, line_color, joint_color):
    # Draw connections (lines)
    for start_idx, end_idx in COCO_CONNECTIONS:
        start_point = pose[start_idx]
        end_point = pose[end_idx]
        
        if not (np.isnan(start_point).any() or np.isnan(end_point).any()):
            cv2.line(frame, start_point, end_point, line_color, 2, cv2.LINE_AA)
    
    # Draw joints (circles)
    for j in range(17):
        point = pose[j]
        if not np.isnan(point).any():
            cv2.circle(frame, point, 4, joint_color, -1, cv2.LINE_AA)
```

**Color Scheme**:
- Expert: CYAN lines (255, 255, 0), YELLOW joints (0, 255, 255)
- User: WHITE lines (255, 255, 255), YELLOW joints (0, 255, 255)

---

### 2.2.3: Progress Bar Visualization
**Algorithm**: Alignment Progress Indicator

**Formula**:
```
current_frame: i ∈ [0, T_aligned-1]
total_frames: T_aligned

progress_ratio = (i + 1) / T_aligned
progress_width = bar_width × progress_ratio
```

**Implementation**:
```python
def draw_alignment_progress_bar(canvas, current_frame, total_frames, x, y, width, height):
    # Background (dark gray)
    cv2.rectangle(canvas, (x, y), (x + width, y + height), (50, 50, 50), -1)
    
    # Progress (cyan)
    progress = int((current_frame + 1) / total_frames * width)
    if progress > 0:
        cv2.rectangle(canvas, (x, y), (x + progress, y + height), (255, 255, 0), -1)
    
    # Border (white)
    cv2.rectangle(canvas, (x, y), (x + width, y + height), (255, 255, 255), 1)
```

---

## Complete DTW Pipeline Summary

**Data Flow**:
```
Expert Pose (100 frames, 17 joints) ──┐
                                       ├─→ Extract Pelvis ──┐
User Pose (120 frames, 17 joints) ────┘                     │
                                                            ↓
                                                    DTW Cost Matrix
                                                         (101×121)
                                                            │
                                                            ↓
                                                    Backtrack Path
                                                            │
                                                            ↓
                                            path_expert, path_user
                                                  (both length 115)
                                                            │
                                                            ↓
                                                    Index-Based Extraction
                                                            │
                                                            ↓
                              Expert Aligned (115, 17, 2) ─┴─ User Aligned (115, 17, 2)
```

**Key Output Properties**:
- ✓ Same temporal length (T_aligned frames)
- ✓ Frame-by-frame correspondence established
- ✓ Original spatial information preserved
- ✓ Temporal differences absorbed by alignment

**Saved Artifacts**:
- `expert_aligned_user{N}.npy`: Expert poses aligned to user N
- `user_{N}_aligned.npy`: User N poses aligned to expert
- `output_temporal_alignment_user{N}.mp4`: Side-by-side visualization

**Parameters**:
| Parameter | Value | Purpose |
|-----------|-------|---------|
| Distance Metric | Euclidean | Pelvis similarity |
| Alignment Anchor | Pelvis (midpoint of hips 11, 12) | Temporal reference |
| Canvas Size | 600×600 px | Visualization |
| FPS | 30 | Video output |
| Color Expert | Cyan/Yellow | Visual distinction |
| Color User | White/Yellow | Visual distinction |

