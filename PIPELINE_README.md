# Pipeline Integration - Quick Start Guide

## What is This?

The **pipeline integration** connects all modules of the AR-Based Kabaddi Ghost Trainer into a single executable script. Run one command to execute the complete workflow from pose extraction to feedback generation.

---

## Quick Start

### Option 1: Pre-Extracted Poses (Fastest)

```bash
python run_pipeline.py \
  --expert-pose raider_pose_level1.npy \
  --user-pose pose_3d.npy \
  --output-dir results
```

### Option 2: Extract from Video

```bash
python run_pipeline.py \
  --expert-pose raider_pose_level1.npy \
  --user-video masked_raider.mp4 \
  --output-dir results
```

### Option 3: Minimal Output (No TTS, No Visualization)

```bash
python run_pipeline.py \
  --expert-pose raider_pose_level1.npy \
  --user-pose pose_3d.npy \
  --output-dir results \
  --no-tts \
  --no-viz
```

### Option 4: Verbose Logging

```bash
python run_pipeline.py \
  --expert-pose raider_pose_level1.npy \
  --user-pose pose_3d.npy \
  --output-dir results \
  --verbose
```

---

## Pipeline Stages

The pipeline executes in **4 stages**:

1. **Load/Extract Expert Pose**
   - Loads pre-extracted `.npy` file or extracts from video
   - Validates shape and format

2. **Load/Extract User Pose + Level-1 Cleaning**
   - Loads or extracts user pose
   - Applies Level-1 cleaning pipeline if extracted from video

3. **Pose Validation**
   - Computes structural and temporal accuracy
   - Saves scores as JSON

4. **Feedback + TTS + Visualization**
   - Generates textual feedback
   - Converts to speech (optional)
   - Renders comparison video (optional)

---

## Output Files

After successful execution, the output directory contains:

```
results/
├── scores.json              # Validation scores
├── feedback.json            # Structured feedback
├── feedback.txt             # Human-readable feedback
├── feedback.wav             # TTS audio (if enabled)
├── comparison.mp4           # Visual comparison (if enabled)
└── user_pose_cleaned.npy    # Cleaned pose (if extracted from video)
```

---

## Command-Line Arguments

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--expert-pose PATH` | Path to expert pose `.npy` file (pre-extracted) |
| `--expert-video PATH` | Path to expert video (will extract pose) |
| `--user-pose PATH` | Path to user pose `.npy` file (pre-extracted) |
| `--user-video PATH` | Path to user video (will extract pose) |
| `--output-dir PATH` | Output directory for all results |

**Note:** Must provide either `--expert-pose` OR `--expert-video`, and either `--user-pose` OR `--user-video`.

### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--no-tts` | Disabled | Skip text-to-speech audio generation |
| `--no-viz` | Disabled | Skip AR visualization video |
| `--verbose` | Disabled | Enable debug-level logging |
| `--pose-model PATH` | `movenet_lightning.tflite` | Pose estimation model |
| `--target-fps FPS` | `30.0` | Target FPS for video extraction |
| `--width PIXELS` | `640` | Visualization canvas width |
| `--height PIXELS` | `480` | Visualization canvas height |

---

## Data Flow

```
Input Video/Pose
      ↓
[Pose Extraction]  ← MoveNet or MediaPipe
      ↓
[MediaPipe → COCO17 Adapter]  ← If using MediaPipe
      ↓
[Level-1 Cleaning]  ← Interpolation, normalization, smoothing
      ↓
[Validation Metrics]  ← Structural + Temporal scoring
      ↓
[Feedback Generator]  ← Rule-based feedback
      ↓
[TTS Engine]  ← Optional audio
      ↓
[AR Renderer]  ← Optional visualization
      ↓
Output Files
```

---

## Error Handling

### Critical Errors (Pipeline Stops)

1. **File not found** - Expert/user pose file doesn't exist
2. **Invalid pose shape** - Wrong dimensions (expected: T, 17, 2)
3. **No poses detected** - Video has no person detected
4. **Module import failure** - Missing dependencies
5. **Invalid input format** - Level-1 cleaning requires COCO-17 (17 joints) format

### Input Validation

Level-1 cleaning (`clean_level1_poses()`) strictly validates input format:

- ✓ Must be `numpy.ndarray`
- ✓ Shape must be `(T, J, 2)` where `J = 17` (COCO-17)
- ✓ At least 1 frame required (`T ≥ 1`)
- ✓ Coordinates must be 2D (`(x, y)`)

> [!WARNING]
> MediaPipe (33 joints) poses will be **rejected**. Convert to COCO-17 format using `mp33_to_coco17.py` first.

For detailed validation rules and failure modes, see [level1_pose/LEVEL1_CLEANING_README.md](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/level1_pose/LEVEL1_CLEANING_README.md).


### Non-Critical Errors (Pipeline Continues)

5. **TTS failure** - Continues without audio, saves text only
6. **Visualization failure** - Continues without video

---

## Example Session

```bash
$ python run_pipeline.py --expert-pose raider_pose_level1.npy --user-pose pose_3d.npy --output-dir demo_run

[14:30:15] ======================================================================
[14:30:15]       AR-Based Kabaddi Ghost Trainer - Pipeline Execution
[14:30:15] ======================================================================

[14:30:15] Output directory: demo_run
[14:30:15] Verbose logging: False
[14:30:15] TTS enabled: True
[14:30:15] Visualization enabled: True

[14:30:15] ======================================================================
[14:30:15] [STAGE 1/4] Load Expert/Reference Pose
[14:30:15] ======================================================================
[14:30:15]   → Expert pose (pre-extracted): raider_pose_level1.npy
[14:30:15] ✓ Loaded expert pose: 180 frames
[14:30:15] ✓ Stage complete in 0.05s
[14:30:15]   → Shape: (180, 17, 2)

[14:30:15] ======================================================================
[14:30:15] [STAGE 2/4] Load/Extract User Pose + Level-1 Cleaning
[14:30:15] ======================================================================
[14:30:15]   → User pose (pre-extracted): pose_3d.npy
[14:30:15] ✓ Loaded user pose: 150 frames
[14:30:15] ✓ Stage complete in 0.03s
[14:30:15]   → Shape: (150, 17, 2)

[14:30:15] ======================================================================
[14:30:15] [STAGE 3/4] Pose Validation
[14:30:15] ======================================================================
[14:30:15]   → Expert pose: (180, 17, 2)
[14:30:15]   → User pose: (150, 17, 2)
[14:30:15] Computing validation metrics...
[14:30:16] ✓ Validation complete
[14:30:16]   ✓ Structural score: 78.45/100
[14:30:16]   ✓ Temporal score: 72.30/100
[14:30:16]   ✓ Overall score: 75.38/100
[14:30:16] ✓ Stage complete in 0.85s
[14:30:16]   → Overall: 75.38/100

[14:30:16] ======================================================================
[14:30:16] [STAGE 4/4] Feedback Generation + TTS + Visualization
[14:30:16] ======================================================================
[14:30:16]   → Scores: Overall: 75.4/100
[14:30:16] Generating feedback...
[14:30:16] ✓ Feedback generated
[14:30:16]   ✓ Category: good
[14:30:16]   ✓ Overall message: Good effort. Your performance is acceptable with some...
[14:30:16] Converting feedback to speech...
[14:30:18] ✓ Audio saved to demo_run/feedback.wav
[14:30:18] ----------------------------------------------------------------------
[14:30:18]   → Expert pose frames: 180
[14:30:18]   → User pose frames: 150
[14:30:18] Rendering comparison video...
[14:30:22] ✓ Video saved to demo_run/comparison.mp4
[14:30:22] ✓ Stage complete

[14:30:22] ======================================================================
[14:30:22]              Pipeline Complete - Summary
[14:30:22] ======================================================================

[14:30:22] 📊 Validation Scores:
[14:30:22]   • Structural: 78.45/100
[14:30:22]   • Temporal: 72.30/100
[14:30:22]   • Overall: 75.38/100

[14:30:22] 📁 Generated Files:
[14:30:22]   • Scores: demo_run/scores.json
[14:30:22]   • Feedback (JSON): demo_run/feedback.json
[14:30:22]   • Feedback (Text): demo_run/feedback.txt
[14:30:22]   • Audio: demo_run/feedback.wav
[14:30:22]   • Video: demo_run/comparison.mp4

[14:30:22] 💬 Feedback:
[14:30:22]   Good effort. Your performance is acceptable with some noticeable gaps.

[14:30:22] ✅ All stages completed successfully!
```

---

## Troubleshooting

### Problem: "Module not found" errors

**Solution:** Ensure you're in the correct directory and all dependencies are installed:
```bash
cd "c:/Users/msibr/Documents/MCA/SEM 4/Project/kabaddi_trainer"
pip install numpy scipy opencv-python pyttsx3
```

### Problem: TTS fails on Linux

**Solution:** Install espeak:
```bash
sudo apt-get install espeak
```

### Problem: Video extraction is slow

**Solution:** Use pre-extracted poses or reduce target FPS:
```bash
python run_pipeline.py ... --target-fps 15
```

### Problem: Want to see what's happening internally

**Solution:** Enable verbose logging:
```bash
python run_pipeline.py ... --verbose
```

---

## Integration with Existing Modules

The pipeline uses these existing modules **without modification**:

- `extract_pose.py` - Pose extraction from video
- `level1_pose/mp33_to_coco17.py` - MediaPipe to COCO-17 adapter
- `level1_pose/level1_cleaning.py` - Level-1 pose cleaning
- `pose_validation_metrics.py` - Validation metrics
- `feedback_generator.py` - Feedback generation
- `tts_engine.py` - Text-to-speech
- `ar_pose_renderer.py` - AR visualization

**New modules created:**
- `run_pipeline.py` - Main orchestration script
- `pipeline_config.py` - Configuration management
- `pipeline_logger.py` - Centralized logging

---

## Next Steps

1. **Test the pipeline:**
   ```bash
   python run_pipeline.py --expert-pose raider_pose_level1.npy --user-pose pose_3d.npy --output-dir test_output
   ```

2. **Review outputs:**
   - Open `test_output/comparison.mp4` to see visual comparison
   - Play `test_output/feedback.wav` to hear audio feedback
   - Read `test_output/feedback.txt` for detailed text feedback

3. **Customize:**
   - Adjust TTS rate: `--tts-rate 180`
   - Change canvas size: `--width 1280 --height 720`
   - Use different pose model: `--pose-model your_model.tflite`

---

**Status:** ✅ Ready for use  
**Dependencies:** numpy, scipy, opencv-python, pyttsx3  
**Platform:** Windows (primary), cross-platform compatible
