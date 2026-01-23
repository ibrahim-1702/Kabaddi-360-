# AR Visualization Module - Documentation

Lightweight OpenCV-based pose visualization system for AR-Based Kabaddi Ghost Trainer.

---

## Overview

This module provides skeletal stick figure rendering for COCO-17 pose sequences with support for:
- **Ghost-only playback**: Expert/reference pose visualization
- **User-only playback**: User performance visualization  
- **Overlay mode**: Side-by-side comparison with temporal synchronization

**Key Features:**
- ✅ No pose data modification (read-only operations)
- ✅ Temporal synchronization via interpolation
- ✅ Output suitable for pose re-extraction validation
- ✅ Minimal dependencies (OpenCV + NumPy + SciPy)

---

## Files

### [ar_pose_renderer.py](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/ar_pose_renderer.py)

Core rendering module with:
- `COCO17Skeleton`: Skeleton definition class
- `PoseRenderer`: Main rendering engine

### [demo_ar_playback.py](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/demo_ar_playback.py)

Demo script for testing visualization modes.

---

## COCO-17 Skeleton Structure

### Joint Indices

```python
COCO17Skeleton.JOINT_NAMES = [
    0:  "nose",
    1:  "left_eye",
    2:  "right_eye",
    3:  "left_ear",
    4:  "right_ear",
    5:  "left_shoulder",
    6:  "right_shoulder",
    7:  "left_elbow",
    8:  "right_elbow",
    9:  "left_wrist",
    10: "right_wrist",
    11: "left_hip",
    12: "right_hip",
    13: "left_knee",
    14: "right_knee",
    15: "left_ankle",
    16: "right_ankle"
]
```

### Limb Connections

16 limb connections forming the skeletal structure:

**Face**: nose ↔ eyes ↔ ears  
**Torso**: shoulder-shoulder, shoulder-hip, hip-hip  
**Arms**: shoulder → elbow → wrist (both sides)  
**Legs**: hip → knee → ankle (both sides)

---

## API Reference

### COCO17Skeleton

**Static Class**

```python
from ar_pose_renderer import COCO17Skeleton

# Joint information
COCO17Skeleton.JOINT_NAMES      # List of 17 joint names
COCO17Skeleton.LIMB_CONNECTIONS # List of 16 (joint_a, joint_b) pairs

# Helper method
COCO17Skeleton.get_joint_name(index)  # Get name by index
```

### PoseRenderer

**Main Rendering Engine**

#### Initialization

```python
from ar_pose_renderer import PoseRenderer

renderer = PoseRenderer(
    canvas_size=(640, 480),  # Output resolution (width, height)
    fps=30,                   # Video frame rate
    line_thickness=2,         # Skeleton limb thickness
    joint_radius=4            # Joint circle radius
)
```

#### Methods

##### render_ghost_only()

Render ghost pose sequence in green.

```python
renderer.render_ghost_only(
    ghost_pose,         # np.ndarray (T, 17, 2)
    output_path,        # str - path to save MP4 video
    max_frames=None     # Optional frame limit
) -> str  # Returns output_path
```

##### render_user_only()

Render user pose sequence in blue.

```python
renderer.render_user_only(
    user_pose,          # np.ndarray (T, 17, 2)
    output_path,        # str - path to save MP4 video
    max_frames=None     # Optional frame limit
) -> str  # Returns output_path
```

##### render_overlay()

Render ghost (green) and user (blue) poses as overlay.

```python
renderer.render_overlay(
    ghost_pose,         # np.ndarray (T1, 17, 2)
    user_pose,          # np.ndarray (T2, 17, 2)
    output_path,        # str - path to save MP4 video
    max_frames=None     # Optional frame limit
) -> str  # Returns output_path
```

**Note**: Sequences of different lengths are automatically synchronized via linear interpolation.

##### draw_skeleton()

Low-level function to draw a single pose on canvas.

```python
renderer.draw_skeleton(
    canvas,             # np.ndarray (H, W, 3) - BGR image
    pose,               # np.ndarray (17, 2) - single frame
    color,              # Tuple[int, int, int] - BGR color
    confidence_threshold=0.0  # Unused (for future extension)
) -> np.ndarray  # Returns modified canvas
```

---

## Usage Examples

### Example 1: Ghost-Only Playback

```python
import numpy as np
from ar_pose_renderer import PoseRenderer

# Load ghost pose
ghost_pose = np.load('raider_pose_3d.npy')  # Shape: (T, 17, 2)

# Create renderer
renderer = PoseRenderer(canvas_size=(640, 480), fps=30)

# Render
renderer.render_ghost_only(ghost_pose, 'ghost_demo.mp4')
```

### Example 2: User-Only Playback

```python
# Load user pose
user_pose = np.load('user_attempt.npy')  # Shape: (T, 17, 2)

# Render
renderer = PoseRenderer()
renderer.render_user_only(user_pose, 'user_demo.mp4')
```

### Example 3: Overlay Comparison

```python
# Load both sequences
ghost_pose = np.load('expert.npy')    # Shape: (100, 17, 2)
user_pose = np.load('beginner.npy')   # Shape: (85, 17, 2)

# Render overlay (automatic synchronization to 100 frames)
renderer = PoseRenderer()
renderer.render_overlay(ghost_pose, user_pose, 'comparison.mp4')
```

### Example 4: Command-Line Usage

```bash
# Ghost-only
python demo_ar_playback.py --pose pose_3d.npy --mode ghost --output ghost.mp4

# User-only
python demo_ar_playback.py --pose raider_pose_3d.npy --mode user --output user.mp4

# Overlay comparison
python demo_ar_playback.py \
    --ghost raider_pose_3d.npy \
    --user pose_3d.npy \
    --mode overlay \
    --output comparison.mp4

# Quick test (30 frames only)
python demo_ar_playback.py --pose pose_3d.npy --mode ghost --max-frames 30 --output test.mp4
```

---

## Coordinate System

### Input Format

**Expected**: `(T, 17, 2)`  
- `T`: Number of frames  
- `17`: COCO-17 joints  
- `2`: (x, y) coordinates

### Coordinate Handling

The renderer **automatically detects** coordinate format:

1. **Normalized coordinates** (0-1 range): Scaled to canvas size
2. **Pixel coordinates** (>10): Used directly

**Detection logic**: If `max(pose) <= 10.0`, assume normalized.

### 3D Pose Support

If input is `(T, 17, 3)`, only `[:, :, :2]` (x, y) is extracted.

---

## Color Scheme

| Mode | Color | BGR Value |
|------|-------|-----------|
| Ghost | Green | (0, 255, 0) |
| User | Blue | (255, 128, 0) |
| Background | Black | (0, 0, 0) |

**Rationale**: High contrast for visual clarity and re-extraction accuracy.

---

## Temporal Synchronization

When rendering overlay mode with sequences of different lengths:

1. **Target length** = max(T_ghost, T_user)
2. **Interpolation method**: Linear (via SciPy)
3. **Interpolation applies to**: Both x and y coordinates for all joints

**Example**:
- Ghost: 100 frames  
- User: 85 frames  
- Output: 100 frames (user interpolated to 100)

---

## Integration with Existing Modules

### With Pose Extraction

```python
# 1. Extract pose from video
# python extract_pose.py --video expert.mp4 --outdir pose_out --model movenet_lightning.tflite

# 2. Convert JSONs to numpy array (manually or via script)
# Assuming you have pose_array.npy

# 3. Render
from ar_pose_renderer import PoseRenderer
import numpy as np

pose = np.load('pose_array.npy')
renderer = PoseRenderer()
renderer.render_ghost_only(pose, 'ghost.mp4')
```

### With Pose Validation Metrics

```python
from pose_validation_metrics import PoseValidationMetrics
from ar_pose_renderer import PoseRenderer
import numpy as np

# Load poses
expert = np.load('expert.npy')
ghost = np.load('ghost_rendered.npy')  # Re-extracted from video

# Validate rendering quality
metrics = PoseValidationMetrics()
scores = metrics.ghost_validation_score(expert, ghost)

print(f"Ghost validation: {scores['overall']:.2f}/100")

# If score >= 85: rendering is suitable for AR playback
if scores['overall'] >= 85:
    # Render for user comparison
    user = np.load('user.npy')
    renderer = PoseRenderer()
    renderer.render_overlay(ghost, user, 'training_comparison.mp4')
```

---

## Round-Trip Validation

**Purpose**: Verify rendered output is suitable for pose re-extraction.

### Workflow

1. **Render ghost from expert pose**
   ```bash
   python demo_ar_playback.py --pose expert.npy --mode ghost --output ghost_render.mp4
   ```

2. **Re-extract pose from rendered video**
   ```bash
   python extract_pose.py --video ghost_render.mp4 --outdir re_extracted --model movenet_lightning.tflite
   ```

3. **Convert JSONs to numpy array** (example script)
   ```python
   import json
   import numpy as np
   from pathlib import Path
   
   json_files = sorted(Path('re_extracted').glob('frame_*.json'))
   poses = []
   
   for jf in json_files:
       with open(jf) as f:
           data = json.load(f)
       joints = np.array([[j['x'], j['y']] for j in data['joints']])
       poses.append(joints)
   
   re_extracted = np.array(poses)  # Shape: (T, 17, 2)
   np.save('re_extracted.npy', re_extracted)
   ```

4. **Compare using metrics**
   ```python
   from pose_validation_metrics import PoseValidationMetrics
   import numpy as np
   
   original = np.load('expert.npy')
   re_extracted = np.load('re_extracted.npy')
   
   metrics = PoseValidationMetrics()
   scores = metrics.ghost_validation_score(original, re_extracted)
   
   print(f"Round-trip score: {scores['overall']:.2f}/100")
   print(f"  Structural: {scores['structural']:.2f}")
   print(f"  Temporal: {scores['temporal']:.2f}")
   ```

**Expected score**: ≥ 85/100 for production-ready rendering.

---

## Performance Notes

### Runtime

Typical performance on modern CPU:
- **Ghost/User-only**: ~1-2 seconds for 100 frames at 640x480
- **Overlay mode**: ~2-3 seconds for 100 frames (due to interpolation)

### Memory

- **Input**: (100, 17, 2) → ~13 KB
- **Output video**: ~500 KB - 2 MB (depends on FPS and duration)

### Optimization Tips

1. **Reduce canvas size** for faster rendering: `canvas_size=(320, 240)`
2. **Limit frames** for testing: `max_frames=30`
3. **Use H.264 codec** (requires ffmpeg): Replace `'mp4v'` with `'avc1'` in code

---

## Troubleshooting

### Issue: Video file not created

**Cause**: OpenCV VideoWriter codec issue  
**Solution**:
```bash
# Install ffmpeg
# Windows: Download from ffmpeg.org
# Linux: sudo apt install ffmpeg
# Mac: brew install ffmpeg
```

### Issue: Skeleton looks distorted

**Cause**: Coordinate mismatch (normalized vs pixel)  
**Solution**: Check pose value range. If >1, coordinates may be pixel-based. Manually normalize:
```python
pose_normalized = pose / pose.max()  # Quick normalization
```

### Issue: Overlay sequences not synchronized

**Cause**: This should be automatic  
**Diagnosis**: Check console output for interpolation messages  
**Workaround**: Manually interpolate before calling render:
```python
from ar_pose_renderer import PoseRenderer

renderer = PoseRenderer()
user_interp = renderer._interpolate_sequence(user_pose, len(ghost_pose))
renderer.render_overlay(ghost_pose, user_interp, 'overlay.mp4')
```

### Issue: Re-extracted pose does not match original

**Cause**: Low rendering resolution or MoveNet detection issues  
**Solution**:
1. Increase canvas size: `canvas_size=(1280, 720)`
2. Increase line thickness: `line_thickness=4`
3. Increase joint radius: `joint_radius=6`

---

## Dependencies

```txt
opencv-python>=4.5.0
numpy>=1.19.0
scipy>=1.5.0  # For interpolation
```

Install via:
```bash
pip install opencv-python numpy scipy
```

---

## Limitations

1. **2D only**: No depth visualization (acceptable for single-view AR)
2. **No occlusion handling**: All joints always visible
3. **Fixed color scheme**: Colors hard-coded (can be modified in source)
4. **MP4 codec dependency**: May require ffmpeg on some systems

---

## Future Enhancements

Potential improvements (not implemented):

- [ ] Configurable color schemes via CLI
- [ ] Real-time playback with keyboard controls (pause/resume)
- [ ] Side-by-side view (split screen) instead of overlay
- [ ] Skeleton thickness based on confidence scores
- [ ] 3D visualization (if depth data available)
- [ ] GIF export for web embedding

---

## License

Part of AR-Based Kabaddi Ghost Trainer project.

---

## Support

For issues or questions:
1. Check this documentation
2. Review [pose_validation_metrics.py](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/pose_validation_metrics.py) for integration examples
3. Test with provided demo script first

**Status**: ✅ Production-ready  
**Last Updated**: 2026-01-04
