# L1.1 — YOLO Person Detection & Tracking

## Purpose

Visualizes YOLO-based person detection and tracking to demonstrate raider selection from a multi-person kabaddi scene.

## Semantic Truth

**"This is WHO we're analyzing — raider isolated via motion heuristic"**

## Input

- **Video**: `samples/kabaddi_clip.mp4`
- **YOLO Model**: `yolov8n.pt` (in project root)

## Output

- **File**: `review1/level1_pose/outputs/01_yolo_tracking.mp4`

## Process

1. **Detect persons** using YOLOv8 (class 0)
2. **Track** across frames using ByteTrack
3. **Compute cumulative motion** per track (bbox center displacement)
4. **Select raider** = track with maximum cumulative motion
5. **Visualize** all detections with color-coded track IDs

## Raider Selection Algorithm

**Heuristic**: Active player moves most in multi-person scene

```python
# For each track:
cumulative_motion = sum of frame-to-frame bbox center displacements

# After 5+ frames:
raider_id = track with max(cumulative_motion)
```

**Why this works**: In kabaddi clips, the raider (active player) typically exhibits more motion than defenders/observers.

## Visualization

### Bounding Boxes

| Type | Color | Thickness | Label |
|------|-------|-----------|-------|
| **Selected Raider** | GREEN | 3px | `ID:<n> [RAIDER]` |
| **Other People** | GRAY | 1px | `ID:<n>` |

### Overlays

- **Frame counter** (top-left)
- **Timestamp** (top-right)
- **Watermark** (center-top): `YOLO PERSON TRACKING — RAIDER SELECTION`
- **Motion score** (optional, below raider box): `motion: 45.2`

## Usage

```bash
# From project root
python review1\level1_pose\01_yolo_tracking\visualize_yolo.py
```

## Dependencies

- OpenCV (`cv2`)
- Ultralytics YOLO (`ultralytics`)
- NumPy
- Python 3.10+

## Validation

✅ All detected persons have track IDs  
✅ Track IDs are stable across frames  
✅ Exactly one person marked as `[RAIDER]`  
✅ Raider selection deterministic (same input → same output)  
✅ No pose skeletons or keypoints drawn

## Examiner Takeaway

**Proves**: The system can reliably isolate the active player (raider) from a multi-person scene using motion-based heuristics, providing clean input for downstream pose extraction.

## Notes

- **Minimum frames**: Raider selected after 5+ frames to ensure reliable motion data
- **Deterministic**: ByteTrack produces consistent IDs for same input
- **No ML for selection**: Motion-based heuristic only (transparent, explainable)
