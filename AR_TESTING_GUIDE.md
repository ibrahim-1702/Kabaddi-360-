# AR Visualization - Testing and Verification Guide

Complete guide for testing the AR Playback & Visualization module.

---

## Quick Start Testing

### Test 1: Module Import Verification

```bash
cd "c:/Users/msibr/Documents/MCA/SEM 4/Project/kabaddi_trainer"
venv\Scripts\python.exe -c "from ar_pose_renderer import COCO17Skeleton; print(f'Joints: {len(COCO17Skeleton.JOINT_NAMES)}, Limbs: {len(COCO17Skeleton.LIMB_CONNECTIONS)}')"
```

**Expected Output:**
```
Joints: 17, Limbs: 16
```

### Test 2: Skeleton Test Rendering

```bash
venv\Scripts\python.exe ar_pose_renderer.py
```

**Expected Output:**
- Console output showing COCO-17 structure
- Creates `test_skeleton_render.mp4` with 30-frame animation

### Test 3: Ghost-Only Playback

```bash
venv\Scripts\python.exe demo_ar_playback.py --pose pose_3d.npy --mode ghost --output test_ghost.mp4 --max-frames 30
```

**Expected Output:**
- Video file `test_ghost.mp4` with green skeleton
- 30 frames rendered

### Test 4: User-Only Playback

```bash
venv\Scripts\python.exe demo_ar_playback.py --pose raider_pose_3d.npy --mode user --output test_user.mp4 --max-frames 30
```

**Expected Output:**
- Video file `test_user.mp4` with blue skeleton
- 30 frames rendered

### Test 5: Overlay Comparison (Full Test)

```bash
venv\Scripts\python.exe demo_ar_playback.py --ghost raider_pose_3d.npy --user pose_3d.npy --mode overlay --output test_overlay.mp4 --max-frames 30
```

**Expected Output:**
- Video file `test_overlay.mp4` with green (ghost) and blue (user) skeletons overlaid
- Synchronized to 30 frames
- Console shows interpolation message

---

## Manual Verification Checklist

### Visual Quality Assessment

Open each generated video and verify:

**Ghost-Only** (`test_ghost.mp4`):
- [ ] Green skeleton visible and connected
- [ ] 17 joint points clearly visible
- [ ] Limbs correctly connected (16 connections)
- [ ] Smooth animation (no jittering)
- [ ] Frame counter displayed at top

**User-Only** (`test_user.mp4`):
- [ ] Blue skeleton visible and connected
- [ ] All joints and limbs visible
- [ ] Smooth temporal progression
- [ ] Frame counter displayed at top

**Overlay** (`test_overlay.mp4`):
- [ ] Both green and blue skeletons visible
- [ ] Skeletons are temporally synchronized
- [ ] Legend shows "Ghost (Green) | User (Blue)" at bottom
- [ ] No visual artifacts or overlapping issues

### Pose Data Integrity Verification

Verify NO pose data modification:

```python
import numpy as np

# Load original
original = np.load('pose_3d.npy')
print(f"Original shape: {original.shape}")
print(f"Original hash: {hash(original.tobytes())}")

# After rendering, verify original is unchanged
reloaded = np.load('pose_3d.npy')
print(f"Reloaded shape: {reloaded.shape}")
print(f"Reloaded hash: {hash(reloaded.tobytes())}")

# Verify identical
assert np.array_equal(original, reloaded), "ERROR: Pose data was modified!"
print("✅ PASS: Pose data unchanged")
```

---

## Round-Trip Validation Test

**Purpose**: Verify rendered output is suitable for pose re-extraction

### Step 1: Render Expert Pose

```bash
venv\Scripts\python.exe demo_ar_playback.py --pose raider_pose_3d.npy --mode ghost --output ghost_rendered.mp4
```

### Step 2: Re-Extract Pose from Rendered Video

```bash
venv\Scripts\python.exe extract_pose.py --video ghost_rendered.mp4 --outdir re_extracted_pose --model movenet_lightning.tflite --max-frames 100
```

### Step 3: Convert JSONs to NumPy Array

```python
import json
import numpy as np
from pathlib import Path

# Script to convert extracted JSONs to .npy format
json_files = sorted(Path('re_extracted_pose').glob('frame_*.json'))
poses = []

for jf in json_files:
    with open(jf) as f:
        data = json.load(f)
    # Extract x, y coordinates
    joints = np.array([[j['x'], j['y']] for j in data['joints']])
    poses.append(joints)

re_extracted = np.array(poses, dtype=np.float32)
print(f"Re-extracted pose shape: {re_extracted.shape}")
np.save('re_extracted.npy', re_extracted)
```

Save this as `convert_json_to_npy.py` and run:

```bash
venv\Scripts\python.exe convert_json_to_npy.py
```

### Step 4: Compare Using Validation Metrics

```python
from pose_validation_metrics import PoseValidationMetrics
import numpy as np

# Load poses
original = np.load('raider_pose_3d.npy')[:, :, :2]  # Extract x,y if 3D
re_extracted = np.load('re_extracted.npy')

# Normalize to 0-1 range (if extracted in pixels)
h, w = 480, 640  # Canvas size
re_extracted_norm = re_extracted.copy()
re_extracted_norm[:, :, 0] /= w
re_extracted_norm[:, :, 1] /= h

# Compare
metrics = PoseValidationMetrics()
scores = metrics.ghost_validation_score(original, re_extracted_norm)

print("=" * 60)
print("Round-Trip Validation Results")
print("=" * 60)
print(f"Structural Accuracy: {scores['structural']:.2f}/100")
print(f"Temporal Accuracy:   {scores['temporal']:.2f}/100")
print(f"Overall Score:       {scores['overall']:.2f}/100")
print(f"Interpretation:      {metrics.interpret_score(scores['overall'])}")
print()

if scores['overall'] >= 85:
    print("✅ PASS: Rendering quality is production-ready!")
elif scores['overall'] >= 70:
    print("⚠️  WARNING: Acceptable but not ideal. Consider:")
    print("  - Increase canvas size (e.g., 1280x720)")
    print("  - Increase line thickness and joint radius")
else:
    print("❌ FAIL: Rendering quality insufficient for validation")
    print("  Action required: Optimize rendering parameters")
```

Save as `validate_round_trip.py` and run:

```bash
venv\Scripts\python.exe validate_round_trip.py
```

**Expected Score**: ≥ 85/100

---

## Integration Test

Verify complete workflow: Extract → Render → Validate → Compare

```bash
# 1. Extract expert pose (if not already done)
# venv\Scripts\python.exe extract_pose.py --video expert_video.mp4 --outdir expert_pose --model movenet_lightning.tflite

# 2. Render ghost
venv\Scripts\python.exe demo_ar_playback.py --pose expert.npy --mode ghost --output ghost.mp4

# 3. Extract user pose
# venv\Scripts\python.exe extract_pose.py --video user_video.mp4 --outdir user_pose --model movenet_lightning.tflite

# 4. Render overlay for comparison
venv\Scripts\python.exe demo_ar_playback.py --ghost expert.npy --user user.npy --mode overlay --output comparison.mp4

# 5. Validate user performance
venv\Scripts\python.exe -c "
from pose_validation_metrics import PoseValidationMetrics
import numpy as np

expert = np.load('expert.npy')
user = np.load('user.npy')

metrics = PoseValidationMetrics()
scores = metrics.user_evaluation_score(user, expert)

print(f'User Performance: {scores[\"overall\"]:.2f}/100')
print(f'  Structural: {scores[\"structural\"]:.2f}')
print(f'  Temporal: {scores[\"temporal\"]:.2f}')
"
```

---

## Performance Benchmarks

Expected performance on modern CPU:

| Operation | Frames | Resolution | Expected Time |
|-----------|--------|------------|---------------|
| Ghost-only | 100 | 640x480 | 1-2 seconds |
| User-only | 100 | 640x480 | 1-2 seconds |
| Overlay | 100 | 640x480 | 2-3 seconds |
| Render + Extract | 100 | 640x480 | 10-15 seconds |

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'cv2'"

**Solution**:
```bash
venv\Scripts\pip install opencv-python
```

### Issue: "ModuleNotFoundError: No module named 'scipy'"

**Solution**:
```bash
venv\Scripts\pip install scipy
```

### Issue: Video file created but empty/corrupted

**Cause**: Codec issue  
**Solution**: Install ffmpeg
- Windows: Download from https://ffmpeg.org/download.html
- Add to PATH

**Alternative**: Change codec in `ar_pose_renderer.py`:
```python
# Line 264, 308, 372: Replace 'mp4v' with 'XVID' or 'MJPG'
fourcc = cv2.VideoWriter_fourcc(*'XVID')
```

### Issue: Overlay sequences look unsynchronized

**Diagnosis**: Check console output for interpolation message  
**Expected**: "Synchronizing X ghost frames + Y user frames -> Z frames"

**If not shown**: Verify pose files have correct shape:
```bash
venv\Scripts\python.exe -c "import numpy as np; p = np.load('pose_3d.npy'); print(p.shape)"
```

Expected: `(T, 17, 2)` or `(T, 17, 3)`

### Issue: Skeleton looks distorted

**Cause**: Coordinate mismatch  
**Solution**: Check value range:
```python
import numpy as np
pose = np.load('pose_3d.npy')
print(f"Min: {pose.min()}, Max: {pose.max()}")
```

- If max > 10: Pixel coordinates (should auto-detect)
- If max ≤ 1: Normalized coordinates (should auto-detect)
- If max > 1000: Divide by canvas size to normalize

---

## Success Criteria

Module is production-ready if ALL of the following pass:

- [x] Files created: `ar_pose_renderer.py`, `demo_ar_playback.py`, `AR_VISUALIZATION_README.md`
- [ ] Import test passes (17 joints, 16 limbs)
- [ ] Skeleton test renders without errors
- [ ] Ghost-only video created successfully
- [ ] User-only video created successfully
- [ ] Overlay video created with synchronization
- [ ] Visual quality: All joints/limbs visible and connected
- [ ] Pose data integrity: Original files unchanged
- [ ] Round-trip score ≥ 85/100
- [ ] No errors or warnings during rendering

---

## Next Steps After Verification

Once all tests pass:

1. **Archive test outputs** for documentation
2. **Integrate with feedback module** for real-time training
3. **Optimize rendering parameters** based on deployment environment
4. **Create deployment script** for production use

---

**Status**: Implementation complete, verification pending  
**Last Updated**: 2026-01-04
