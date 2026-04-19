# Level-1 Pose Cleaning - Documentation

## Overview

The Level-1 cleaning module (`level1_cleaning.py`) preprocesses raw 2D pose sequences to make them suitable for pose validation and comparison. This module applies a series of transformations to handle missing data, normalize poses, and smooth trajectories.

---

## Main Function: `clean_level1_poses()`

### Purpose

Accepts raw COCO-17 pose sequences and applies a 6-step cleaning pipeline.

### Function Signature

```python
def clean_level1_poses(poses_2d):
    """
    Input:
        poses_2d → (T, J, 2)

    Output:
        clean poses → (T, J, 2)
    """
```

---

## Input Format

### Expected Input

`clean_level1_poses()` strictly enforces the following input requirements:

| Property | Required Value | Description |
|----------|---------------|-------------|
| **Type** | `numpy.ndarray` | Must be a NumPy array |
| **Dimensions** | `3` | Shape must be `(T, J, 2)` |
| **Frames (T)** | `≥ 1` | At least 1 frame required |
| **Joints (J)** | `17` | COCO-17 format only |
| **Coordinates** | `2` | `(x, y)` coordinates only |

> [!IMPORTANT]
> **COCO-17 (17 joints) is strictly enforced.** Other formats such as MediaPipe (33 joints) will be rejected.

### Valid Input Example

```python
import numpy as np
from level1_cleaning import clean_level1_poses

# Valid: (100 frames, 17 joints, 2 coordinates)
poses = np.random.rand(100, 17, 2)
result = clean_level1_poses(poses)
```

---

## Failure Modes

### 1. Invalid Type

**Error:** `TypeError`

**Trigger:** Input is not a NumPy array

**Message:**
```
Expected numpy.ndarray, got <type>
```

**Example:**
```python
# ❌ FAILS - list instead of ndarray
clean_level1_poses([[1, 2], [3, 4]])
```

---

### 2. Invalid Dimensions

**Error:** `ValueError`

**Trigger:** Input is not a 3D array

**Message:**
```
Expected 3D array (T, J, 2), got shape <shape>
```

**Example:**
```python
# ❌ FAILS - 2D array (100, 34)
poses = np.random.rand(100, 34)
clean_level1_poses(poses)
```

---

### 3. Invalid Coordinates

**Error:** `ValueError`

**Trigger:** Last dimension is not 2

**Message:**
```
Expected last dimension = 2 (x, y), got <value>
```

**Example:**
```python
# ❌ FAILS - 3D coordinates
poses = np.random.rand(100, 17, 3)
clean_level1_poses(poses)
```

---

### 4. Invalid Joint Count

**Error:** `ValueError`

**Trigger:** Joint count is not exactly 17

**Message:**
```
Expected 17 joints (COCO-17), got <value>
```

**Example:**
```python
# ❌ FAILS - MediaPipe format (33 joints)
poses = np.random.rand(100, 33, 2)
clean_level1_poses(poses)
```

> [!CAUTION]
> If you have MediaPipe poses, you **must** convert them to COCO-17 format using the adapter (`mp33_to_coco17.py`) before calling this function.

---

### 5. Empty Sequence

**Error:** `ValueError`

**Trigger:** Zero frames provided

**Message:**
```
Expected at least 1 frame, got 0
```

**Example:**
```python
# ❌ FAILS - empty sequence
poses = np.random.rand(0, 17, 2)
clean_level1_poses(poses)
```

---

## Cleaning Pipeline Steps

After validation, the function applies the following transformations in sequence:

### 1. Temporal Interpolation
- **Function:** `interpolate_missing_joints()`
- **Purpose:** Fills invalid/missing joints using linear interpolation
- **Detection:** Invalid joints are marked as NaN or all-zero coordinates

### 2. Pelvis Centering
- **Function:** `pelvis_centering()`
- **Purpose:** Translates poses so pelvis center is at origin
- **Pelvis:** Midpoint of left hip and right hip

### 3. Scale Normalization
- **Function:** `scale_normalization()`
- **Purpose:** Normalizes poses by torso length
- **Torso:** Distance between shoulder center and hip center

### 4. Outlier Frame Suppression
- **Function:** `suppress_outlier_frames()`
- **Purpose:** Replaces frames with extreme velocity using z-score thresholding
- **Threshold:** `z > 3.0`

### 5. Temporal Smoothing
- **Function:** `ema_smoothing()`
- **Purpose:** Applies exponential moving average smoothing
- **Alpha:** `0.75`

---

## Usage in Pipeline

### Standalone Usage

```python
from level1_cleaning import clean_level1_poses
import numpy as np

# Load raw COCO-17 poses
poses_raw = np.load('user_pose_raw.npy')  # Shape: (T, 17, 2)

# Apply cleaning
poses_clean = clean_level1_poses(poses_raw)

# Save cleaned poses
np.save('user_pose_cleaned.npy', poses_clean)
```

### Integrated with Adapter

```python
from mp33_to_coco17 import mp33_to_coco17
from level1_cleaning import clean_level1_poses
import numpy as np

# Load MediaPipe poses
mp33_poses = np.load('user_pose_mp33.npy')  # Shape: (T, 33, 2)

# Convert to COCO-17
coco17_poses = mp33_to_coco17(mp33_poses)   # Shape: (T, 17, 2)

# Apply cleaning
clean_poses = clean_level1_poses(coco17_poses)

np.save('user_pose_level1.npy', clean_poses)
```

---

## Testing

### Validation Tests

The module includes comprehensive input validation tests in `test_validation.py`:

```bash
cd level1_pose
python test_validation.py
```

**Test Coverage:**
1. ✓ Valid input `(100, 17, 2)` passes successfully
2. ✓ Invalid type (list) raises `TypeError`
3. ✓ Invalid dimensions (2D) raises `ValueError`
4. ✓ Invalid coordinates (3D) raises `ValueError`
5. ✓ Invalid joint count (33) raises `ValueError`
6. ✓ Empty sequence (0 frames) raises `ValueError`

---

## COCO-17 Joint Format

The module requires COCO-17 keypoint format (17 joints):

```
 0: nose
 1: left_eye
 2: right_eye
 3: left_ear
 4: right_ear
 5: left_shoulder
 6: right_shoulder
 7: left_elbow
 8: right_elbow
 9: left_wrist
10: right_wrist
11: left_hip
12: right_hip
13: left_knee
14: right_knee
15: left_ankle
16: right_ankle
```

Joint indices used internally are defined in `joints.py`.

---

## Related Modules

- **`mp33_to_coco17.py`** — Converts MediaPipe (33 joints) → COCO-17 (17 joints)
- **`joints.py`** — Joint index constants (LEFT_HIP, RIGHT_HIP, etc.)
- **`run_pipeline.py`** — Orchestrates cleaning in the full pipeline
- **`test_validation.py`** — Input validation test suite

---

## Error Handling Strategy

> [!NOTE]
> **Fail-fast philosophy:** The function validates all inputs immediately and raises descriptive errors before any processing begins. This prevents silent failures and ensures data correctness.

When validation fails:
1. No processing occurs
2. Descriptive error is raised immediately
3. Error message clearly states what was expected vs. what was received

---

**Status:** ✅ Fully validated and tested  
**Input Validation:** Enforced in Phase 3  
**Joint Format:** COCO-17 (17 joints) only
