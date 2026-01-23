# L1.0 — Raw Video Reference

## Purpose

Creates a reference copy of the raw input video with informational overlays. This serves as the **visual baseline** for comparison with all processed stages.

## Semantic Truth

**"This is what the camera saw — unmodified source material"**

## Input

- **File**: `samples/kabaddi_clip.mp4`
- **Format**: MP4 (H.264)
- **Expected**: Any resolution/FPS (auto-detected)

## Output

- **File**: `review1/level1_pose/outputs/00_raw_reference.mp4`
- **Modifications**: Informational overlays only (no video processing)

## Overlays

1. **Frame Counter** (top-left)
   - Format: `Frame: 0045`
   - Purpose: Precise frame-level debugging

2. **Timestamp** (top-right)
   - Format: `1.50s`
   - Purpose: Temporal reference

3. **Watermark** (center-top)
   - Text: `RAW VIDEO — NO PROCESSING`
   - Background: Semi-transparent black
   - Purpose: Clear stage identification

## Usage

```bash
# From project root directory
cd kabaddi_trainer
python review1/level1_pose/00_raw_video/visualize_raw.py
```

## Dependencies

- OpenCV (`cv2`)
- Python 3.7+

## Validation

✅ Output video plays in VLC/media player  
✅ Frame counter increments correctly  
✅ Timestamp matches video duration  
✅ No dropped frames  
✅ Overlay text readable at all resolutions

## Examiner Takeaway

**Proves**: The system starts with authentic, unmodified video footage. All subsequent processing is applied to this exact source material.
