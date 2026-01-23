# Feedback & TTS Module - Quick Reference

## Files Created

### Core Modules
1. **feedback_generator.py** - Rule-based feedback generation
2. **tts_engine.py** - Offline text-to-speech engine
3. **demo_feedback.py** - Integration demonstration

### Documentation
4. **FEEDBACK_README.md** - Comprehensive documentation

---

## Quick Start

### Installation
```bash
pip install pyttsx3
```

### Basic Usage
```python
from feedback_generator import FeedbackGenerator
from tts_engine import TTSEngine

# Initialize
gen = FeedbackGenerator()
tts = TTSEngine()

# Input scores from pose metrics
scores = {'structural': 85.0, 'temporal': 82.0, 'overall': 83.5}

# Generate feedback
feedback = gen.generate_user_feedback(scores)

# Speak it
tts.speak_feedback(feedback, mode='summary')
```

### Run Demo
```bash
python demo_feedback.py
```

---

## Feedback Rules

| Score | Category | User Feedback |
|-------|----------|---------------|
| 90-100 | Excellent | Outstanding performance! |
| 80-89 | Very Good | Great job! Minor improvements needed. |
| 70-79 | Good | Good effort. Some gaps to address. |
| 60-69 | Fair | Fair attempt. Focus on matching better. |
| 50-59 | Needs Improvement | Keep practicing. |
| 0-49 | Poor | More practice needed. |

---

## Integration with Pose Metrics

```python
from pose_validation_metrics import PoseValidationMetrics
from feedback_generator import FeedbackGenerator
from tts_engine import TTSEngine

# Pipeline
metrics = PoseValidationMetrics()
gen = FeedbackGenerator()
tts = TTSEngine()

# Compute → Generate → Speak
scores = metrics.user_evaluation_score(user_pose, ghost_pose)
feedback = gen.generate_user_feedback(scores)
tts.speak_feedback(feedback, save_file='feedback.wav')
```

---

## Key Features

✅ Deterministic (same scores → same feedback)  
✅ Offline TTS (no internet required)  
✅ Modular (easy to integrate)  
✅ Demo-friendly (audio file export)  
✅ Explainable (rule-based logic)

---

**Status:** Ready for Integration  
**Dependencies:** pyttsx3, numpy, scipy
