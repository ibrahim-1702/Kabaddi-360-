# Level 1: Pose Extraction and Cleaning - Algorithm Analysis

## Overview
Level 1 implements a 4-stage pose extraction and cleaning pipeline that processes raw video to produce cleaned, normalized 2D skeleton data. Each stage builds upon the previous one.

---

## Algorithm 1.1: YOLO Person Detection and Tracking
**File**: [`visualize_yolo.py`](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/review1/level1_pose/01_yolo_tracking/visualize_yolo.py)

### Purpose
Identify and track the active player (raider) in a multi-person Kabaddi scene using motion-based heuristics.

### Input
- Raw video: `samples/kabaddi_clip.mp4`
- YOLO model: `yolov8n.pt` (YOLOv8 Nano)

### Output
- Visualization video: `review1/level1_pose/outputs/01_yolo_tracking.mp4`

### Core Algorithms

#### 1.1.1 YOLO Object Detection
**Algorithm**: You Only Look Once (YOLO) v8 - Neural Network-based Object Detection

**Mathematical Foundation**:
- **Input**: RGB image frame I with dimensions W × H × 3
- **Output**: Bounding boxes B = {b₁, b₂, ..., bₙ} where each bᵢ = (x₁, y₁, x₂, y₂, confidence, class)
- **Process**: Convolutional Neural Network divides image into grid and predicts bounding boxes + class probabilities

**How it Works**:
1. Divide input frame into an S × S grid
2. For each grid cell, predict B bounding boxes
3. Each bounding box prediction includes:
   - Box coordinates (x, y, w, h)
   - Confidence score: P(Object) × IOU(truth, predicted)
   - Class probabilities: P(Classᵢ | Object)
4. Apply Non-Maximum Suppression (NMS) to eliminate duplicate detections

**Implementation**:
```python
yolo = YOLO(model_path)
results = yolo.track(
    frame,
    persist=True,       # Maintain track IDs across frames
    classes=[0],        # Class 0 = person
    tracker="bytetrack.yaml",
    verbose=False
)
```

---

#### 1.1.2 ByteTrack Multi-Object Tracking
**Algorithm**: ByteTrack - Association-based Object Tracking

**Mathematical Foundation**:
- **State Vector**: s = (x, y, w, h, vₓ, vᵧ) where (x,y) =  bbox center, (w,h) = dimensions, (vₓ,vᵧ) = velocity
- **Association Metric**: IoU (Intersection over Union)

**IoU Formula**:
```
IoU(A, B) = Area(A ∩ B) / Area(A ∪ B)
```

**How it Works**:
1. **Detection**: Get bounding boxes from YOLO for current frame
2. **Prediction**: Use Kalman filter to predict track positions
3. **Association**: Match detections to tracks using IoU
   - High-confidence detections → first pass matching
   - Low-confidence detections → second pass matching
4. **Update**: Update track states with associated detections
5. **ID Maintenance**: Assign persistent IDs to tracks

**Output**: Each person gets a unique `track_id` maintained across frames

---

#### 1.1.3 Motion-Based Raider Selection
**Algorithm**: Cumulative Displacement Heuristic

**Mathematical Foundation**:
```
For each track i:
  trajectory = {(xₜ, yₜ)} for t ∈ [0, T]
  cumulative_motion = Σ ||pₜ - pₜ₋₁||  for t ∈ [1, T]

raider = argmax(cumulative_motion)
```

**How it Works**:
1. **Track History Storage**: For each track ID, store bbox center positions
   ```python
   tracks_history[tid] = [(cx₁, cy₁), (cx₂, cy₂), ...]
   ```

2. **Displacement Calculation**: For each consecutive pair of positions
   ```python
   displacement = np.sqrt((curr_cx - prev_cx)² + (curr_cy - prev_cy)²)
   ```

3. **Cumulative Motion**: Sum all displacements
   ```python
   tracks_motion[tid] += displacement
   ```

4. **Raider Selection**: After minimum 5 frames, select track with maximum motion
   ```python
   raider_id = max(tracks_motion, key=tracks_motion.get)
   ```

**Rationale**: The active raider exhibits more movement than spectators/other players

**Output**:
- Raider ID (persistent across frames)
- Cumulative motion score

---

## Algorithm 1.2: MediaPipe Pose Estimation (MP33)
**File**: [`visualize_mp33.py`](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/review1/level1_pose/02_mediapipe_mp33/visualize_mp33.py)

### Purpose
Extract 33 raw keypoints from the selected raider using MediaPipe Pose.

### Input
- Raw video: `samples/kabaddi_clip.mp4`
- YOLO model: `yolov8n.pt`

### Output
- Pose tensor: `02_mediapipe_mp33.npy` (T, 33, 2)
- Visualization video: `02_mediapipe_mp33.mp4`

### Core Algorithms

#### 1.2.1 Raider Bounding Box Extraction
**Algorithm**: Raider-Locked Cropping with Padding

**Formula**:
```
Given raider bbox (x₁, y₁, x₂, y₂):
  x₁' = max(0, x₁ - PAD)
  y₁' = max(0, y₁ - PAD)
  x₂' = min(frame_width, x₂ + PAD)
  y₂' = min(frame_height, y₂ + PAD)
  
  raider_crop = frame[y₁':y₂', x₁':x₂']
```

**Parameters**: PAD = 40 pixels

**Rationale**: 
- Padding includes nearby limbs that might extend beyond tight bbox
- Clipping prevents out-of-bounds access

---

#### 1.2.2 MediaPipe Pose Estimation
**Algorithm**: MediaPipe BlazePose - CNN-based Pose Estimation

**Neural Network Architecture**:
1. **Pose Detector**: Detects person and bounding box
2. **Pose Landmark Model**: Predicts 33 3D landmarks

**Configuration**:
```python
pose = mp_pose.Pose(
    static_image_mode=False,        # Video mode (temporal consistency)
    model_complexity=1,              # Balance accuracy/speed
    smooth_landmarks=True,           # Temporal smoothing
    min_detection_confidence=0.5,    # Detection threshold
    min_tracking_confidence=0.7      # Tracking threshold
)
```

**33 Landmarks**:
- 0-10: Face (nose, eyes, ears, mouth)
- 11-16: Upper body (shoulders, elbows, wrists)
- 17-22: Torso/hands
- 23-32: Lower body (hips, knees, ankles, feet)

**Coordinate System**:
- Normalized coordinates relative to image: x, y ∈ [0, 1]
- Origin at top-left corner
- Also provides z (depth) and visibility score (not used in 2D pipeline)

**How it Works**:
1. Convert crop to RGB: `rgb = cv2.cvtColor(raider_crop, cv2.COLOR_BGR2RGB)`
2. Process with pose model: `results = pose.process(rgb)`
3. Extract landmarks:
   ```python
   for i, lm in enumerate(results.pose_landmarks.landmark):
       frame_pose_2d[i] = [lm.x, lm.y]  # Normalized [0,1]
   ```

**Output**:
- Pose tensor: (T, 33, 2) where T = number of frames
- Values in [0, 1] normalized coordinates
- NaN for frames where raider not detected

---

## Algorithm 1.3: MP33 → COCO-17 Conversion
**File**: [`visualize_coco17_raw.py`](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/review1/level1_pose/03_coco17_raw/visualize_coco17_raw.py)

### Purpose
Convert MediaPipe's 33-joint format to COCO-17 standard format for compatibility.

### Input
- Raw video (for raider locking)
- MediaPipe landmarks (extracted on-the-fly)

### Output
- COCO-17 tensor: `03_coco17_raw.npy` (T, 17, 2) in pixel coordinates
- Visualization video: `03_coco17_raw.mp4`

### Core Algorithms

#### 1.3.1 Joint Mapping Algorithm
**Algorithm**: Direct Index Mapping

**Mapping Table**:
```python
MP_TO_COCO_MAPPING = {
    0: 0,   # nose → nose
    1: 2,   # left_eye → left_eye
    2: 5,   # right_eye → right_eye
    3: 7,   # left_ear → left_ear
    4: 8,   # right_ear → right_ear
    5: 11,  # left_shoulder → left_shoulder
    6: 12,  # right_shoulder → right_shoulder
    7: 13,  # left_elbow → left_elbow
    8: 14,  # right_elbow → right_elbow
    9: 15,  # left_wrist → left_wrist
    10: 16, # right_wrist → right_wrist
    11: 23, # left_hip → left_hip
    12: 24, # right_hip → right_hip
    13: 25, # left_knee → left_knee
    14: 26, # right_knee → right_knee
    15: 27, # left_ankle → left_ankle
    16: 28, # right_ankle → right_ankle
}
```

**COCO-17 Joint Indices**:
0. Nose
1. Left Eye
2. Right Eye
3. Left Ear
4. Right Ear
5. Left Shoulder
6. Right Shoulder
7. Left Elbow
8. Right Elbow
9. Left Wrist
10. Right Wrist
11. Left Hip
12. Right Hip
13. Left Knee
14. Right Knee
15. Left Ankle
16. Right Ankle

---

#### 1.3.2 Coordinate Transformation
**Algorithm**: Normalized to Pixel Space Conversion

**Mathematical Formula**:
```
Given:
  - MediaPipe landmark: (lm.x, lm.y) in [0, 1]
  - Raider bbox: (x₁, y₁, width, height) in pixels
  - Visibility threshold: visibility ≥ 0.5

Convert:
  x_pixel = x₁ + lm.x × width
  y_pixel = y₁ + lm.y × height

If visibility < 0.5: (x_pixel, y_pixel) = (NaN, NaN)
```

**Implementation**:
```python
def convert_mp33_to_coco17(mp33_landmarks, bbox_x1, bbox_y1, bbox_width, bbox_height):
    coco17_pose = np.full((17, 2), np.nan, dtype=np.float32)
    
    for coco_idx in range(17):
        mp_idx = MP_TO_COCO_MAPPING[coco_idx]
        lm = mp33_landmarks[mp_idx]
        
        if lm.visibility >= 0.5:
            x_px = bbox_x1 + lm.x * bbox_width
            y_px = bbox_y1 + lm.y * bbox_height
            coco17_pose[coco_idx] = [x_px, y_px]
    
    return coco17_pose
```

**Output**:
- 17 joints in pixel space (absolute screen coordinates)
- NaN for invisible or low-confidence joints
- Shape: (T, 17, 2)

---

## Algorithm 1.4: COCO-17 Pose Cleaning and Stabilization
**File**: [`visualize_coco17_cleaned.py`](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/review1/level1_pose/04_coco17_cleaned/visualize_coco17_cleaned.py)

### Purpose
Apply signal processing to clean and stabilize raw pose data: remove outliers, fill gaps, normalize, and smooth.

### Input
- Raw COCO-17: `03_coco17_raw.npy` (T, 17, 2) in pixel space

### Output
- Cleaned COCO-17: `04_coco17_cleaned.npy` (T, 17, 2) normalized
- Comparison video: `04_coco17_cleaned.mp4`

### 5-Step Cleaning Pipeline

#### Step 1: Temporal Interpolation
**Algorithm**: Linear Interpolation for Missing Joints

**Purpose**: Fill gaps in temporal sequences where joints are missing

**Mathematical Formula**:
```
For joint j, coordinate c:
  Given valid points at times t₁, t₂, ..., tₙ
  For any intermediate time t ∈ [tᵢ, tᵢ₊₁]:
  
  value(t) = value(tᵢ) + (value(tᵢ₊₁) - value(tᵢ)) × (t - tᵢ)/(tᵢ₊₁ - tᵢ)
```

**Implementation**:
```python
def interpolate_missing_joints(poses):
    T, J, _ = poses.shape
    valid = mark_valid_joints(poses)  # Identify non-NaN joints
    
    for j in range(J):
        for c in range(2):  # x and y
            series = poses[:, j, c]
            v = valid[:, j]
            
            if v.sum() >= 2:  # Need at least 2 valid points
                poses[:, j, c] = np.interp(
                    np.arange(T),        # All frame indices
                    np.where(v)[0],      # Valid frame indices
                    series[v]            # Valid values
                )
    return poses
```

**Rationale**: Joints temporarily occluded can be inferred from nearby frames

---

#### Step 2: Pelvis Centering
**Algorithm**: Translation Normalization

**Purpose**: Achieve translation invariance (position-independent comparison)

**Mathematical Formula**:
```
pelvis(t) = (hip_left(t) + hip_right(t)) / 2

For all joints j at time t:
  joint_centered(t, j) = joint(t, j) - pelvis(t)
```

**Implementation**:
```python
def pelvis_centering(poses):
    LEFT_HIP = 11
    RIGHT_HIP = 12
    pelvis = (poses[:, LEFT_HIP] + poses[:, RIGHT_HIP]) * 0.5
    return poses - pelvis[:, None, :]  # Broadcast subtraction
```

**Effect**: All poses are centered around (0, 0) at pelvis, removing camera position differences

---

#### Step 3: Scale Normalization
**Algorithm**: Torso-Based Scaling

**Purpose**: Achieve scale invariance (size-independent comparison)

**Mathematical Formula**:
```
shoulders(t) = (shoulder_left(t) + shoulder_right(t)) / 2
hips(t) = (hip_left(t) + hip_right(t)) / 2

torso_length(t) = ||shoulders(t) - hips(t)||

scale_factor(t) = torso_length(t) + ε  (ε = 10⁻⁶ to prevent division by zero)

For all joints j at time t:
  joint_normalized(t, j) = joint(t, j) / scale_factor(t)
```

**Implementation**:
```python
def scale_normalization(poses, eps=1e-6):
    LEFT_SHOULDER = 5
    RIGHT_SHOULDER = 6
    LEFT_HIP = 11
    RIGHT_HIP = 12
    
    shoulders = (poses[:, LEFT_SHOULDER] + poses[:, RIGHT_SHOULDER]) * 0.5
    hips = (poses[:, LEFT_HIP] + poses[:, RIGHT_HIP]) * 0.5
    
    torso_len = np.linalg.norm(shoulders - hips, axis=1)
    scale = torso_len[:, None, None] + eps
    
    return poses / scale
```

**Effect**: Poses normalized to unit torso length, removing distance-from-camera differences

---

#### Step 4: Outlier Suppression
**Algorithm**: Z-Score Velocity-Based Outlier Detection

**Purpose**: Remove sudden unrealistic movements (tracking glitches)

**Mathematical Formula**:
```
velocity(t) = ||pose(t) - pose(t-1)||  (Frobenius norm across all joints)

μ = mean(velocity)
σ = std(velocity)

z_score(t) = (velocity(t) - μ) / σ

If |z_score(t)| > threshold (default: 3.0):
  pose(t) = pose(t-1)  # Replace with previous frame
```

**Implementation**:
```python
def suppress_outlier_frames(poses, z_thresh=3.0):
    velocity = np.linalg.norm(np.diff(poses, axis=0), axis=(1, 2))
    z = (velocity - velocity.mean()) / (velocity.std() + 1e-6)
    
    clean = poses.copy()
    bad = np.where(np.abs(z) > z_thresh)[0] + 1
    
    for f in bad:
        clean[f] = clean[f - 1]
    
    return clean
```

**Threshold**: 3.0 σ (captures  ≈99.7% of normal variations)

**Effect**: Sudden tracking errors (jumps) are smoothed out

---

#### Step 5: Exponential Moving Average (EMA) Smoothing
**Algorithm**: Temporal Low-Pass Filter

**Purpose**: Reduce high-frequency noise while preserving motion dynamics

**Mathematical Formula**:
```
α = smoothing factor (default: 0.75)

pose_smooth(0) = pose(0)

For t > 0:
  pose_smooth(t) = α × pose_smooth(t-1) + (1-α) × pose(t)
```

**Implementation**:
```python
def ema_smoothing(poses, alpha=0.75):
    smooth = poses.copy()
    
    for t in range(1, poses.shape[0]):
        smooth[t] = alpha * smooth[t - 1] + (1 - alpha) * poses[t]
    
    return smooth
```

**Parameter Analysis**:
- α = 0.75: Gives 75% weight to previous smoothed value, 25% to current raw value
- Higher α → more smoothing (slower response)
- Lower α → less smoothing (faster response)

**Effect**: Jitter reduction while maintaining temporal coherence

---

## Complete Level-1 Pipeline

**Summary Formula**:
```
Input: Raw video V
Output: Cleaned poses P_clean

P_clean = EMA(
           Suppress_Outliers(
             Scale_Normalize(
               Pelvis_Center(
                 Interpolate(
                   COCO_Convert(
                     MediaPipe(
                       Crop_Raider(
                         YOLO_Track(V)
```

**Data Flow**:
1. **YOLO** → Raider bbox sequence: (T, 4)
2. **MediaPipe** → MP33 poses: (T, 33, 2) normalized
3. **COCO Convert** → COCO17 poses: (T, 17, 2) pixel space
4. **Cleaning Pipeline** → Final poses: (T, 17, 2) normalized, centered, smoothed

**Key Properties of Output**:
- ✓ Translation invariant (pelvis-centered)
- ✓ Scale invariant (torso-normalized)
- ✓ Temporally smooth (outliers suppressed + EMA)
- ✓ Gap-filled (interpolated)
- ✓ COCO-17 compatible (standard format)

---

## Parameters Summary

| Parameter | Value | Purpose |
|-----------|-------|---------|
| YOLO Class | 0 (person) | Object detection filter |
| Bbox Padding | 40 px | Raider crop margin |
| Min Tracking Frames | 5 | Raider selection stability |
| MP Visibility Threshold | 0.5 | Joint confidence cutoff |
| Z-Score Threshold | 3.0 σ | Outlier detection sensitivity |
| EMA Alpha | 0.75 | Smoothing strength |
| Interpolation | Linear | Gap filling method |

