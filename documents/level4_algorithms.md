# Level 4: Similarity Score Computation - Algorithm Analysis

## Overview
Level 4 is a pure aggregation layer that consolidates Level-2 (temporal) and Level-3 (spatial) intelligence into interpretable performance scores. No new analysis is performed - only weighted combination of previous results.

---

## Algorithm 4.1: Similarity Score Computation
**File**: [`compute_similarity_scores.py`](file:///c:/Users/msibr/Documents/MCA/SEM%204/Project/kabaddi_trainer/review1/visualization/level4/compute_similarity_scores.py)

### Purpose
Convert raw error data into normalized 0-100% performance scores for structural (spatial), temporal (timing), and overall (combined) similarity.

### Input
- Error statistics: `../level3/joint_errors_user{N}.json`

### Output
- Similarity scores: `similarity_scores.json`

---

## Core Algorithms

### 4.1.1: Structural Similarity Computation
**Algorithm**: Inverse Error Mapping with Threshold Normalization

**Purpose**: Convert spatial errors to similarity percentage

**Mathematical Formula**:
```
Given joint statistics from Level-3:
  joint_stats = {joint_name: {mean, max, std} for each of 17 joints}

Step 1: Extract mean errors
  mean_errors = [stats['mean'] for stats in joint_stats.values()]

Step 2: Compute overall mean joint error (CRITICAL: handle NaN)
  mean_joint_error = nanmean(mean_errors)

Step 3: Normalize using threshold
  structural_similarity = (1 - mean_joint_error / MAX_ERROR_THRESHOLD) × 100

Step 4: Clamp to [0, 100]
  structural_similarity = max(0, min(100, structural_similarity))
```

**Threshold Parameter**:
```
MAX_ERROR_THRESHOLD = 1.5
```

**Rationale for 1.5**:
- Empirically determined from observed error ranges
- Training data showed errors typically in [0.3, 1.4] range
- 1.5 acts as upper bound for "poor but valid" execution
- Chosen after analyzing actual user data (not arbitrary)

**Interpretation**:
```
If mean_joint_error = 0.0   → structural_similarity = 100%
If mean_joint_error = 0.75  → structural_similarity = 50%
If mean_joint_error = 1.5   → structural_similarity = 0%
If mean_joint_error > 1.5   → structural_similarity = 0% (clamped)
```

**Implementation**:
```python
def compute_structural_similarity(error_data: Dict) -> float:
    joint_stats = error_data['joint_statistics']
    
    # Extract mean errors from all joints
    mean_errors = [stats['mean'] for stats in joint_stats.values()]
    
    # Overall mean joint error (use nanmean to ignore NaN joints)
    mean_joint_error = np.nanmean(mean_errors)
    
    # Convert to similarity (inverse relationship)
    structural_similarity = (1 - mean_joint_error / MAX_ERROR_THRESHOLD) * 100
    
    # Clamp to [0, 100]
    structural_similarity = max(0, min(100, structural_similarity))
    
    return structural_similarity
```

**Example Calculation**:
```
User has joint errors:
  left_knee: mean = 0.42
  right_knee: mean = 0.38
  left_shoulder: mean = 0.55
  ... (all 17 joints)

Overall mean = 0.48

structural_similarity = (1 - 0.48/1.5) × 100
                      = (1 - 0.32) × 100
                      = 0.68 × 100
                      = 68%
```

**Design Philosophy**:
- **Inverse relationship**: Lower error = higher similarity
- **Normalized scale**: 0-100% is intuitive
- **Threshold-based**: Provides context (error relative to worst acceptable)
- **NaN-safe**: Uses nanmean to handle missing joints

---

### 4.1.2: Temporal Similarity Computation
**Algorithm**: Frame Count Deviation from Baseline

**Purpose**: Quantify DTW alignment quality using aligned sequence length

**Mathematical Formula**:
```
Given:
  num_frames = T_aligned (from Level-2 DTW output)
  BASELINE_FRAMES = 115 (empirically chosen middle of observed range)
  MAX_ACCEPTABLE_DEVIATION = BASELINE_FRAMES × 0.5 = 57.5 frames

Step 1: Calculate deviation from baseline
  frame_deviation = |num_frames - BASELINE_FRAMES|

Step 2: Normalize deviation
  if frame_deviation >= MAX_ACCEPTABLE_DEVIATION:
      temporal_quality = 0.0
  else:
      temporal_quality = 1.0 - (frame_deviation / MAX_ACCEPTABLE_DEVIATION)

Step 3: Scale to [70, 100] range
  temporal_similarity = 70 + (temporal_quality × 30)
```

**Why [70, 100] Range?**
- Successful DTW alignment deserves baseline credit (70%)
- Only exceptional alignment gets 100%
- Penalizes extreme compression/expansion

**Baseline Selection**:
```
Observed user data:
  User 1: 103 frames
  User 2: 115 frames
  User 3: 129 frames
  User 4: 108 frames

Middle of range: BASELINE_FRAMES = 115
```

**Implementation**:
```python
def compute_temporal_similarity(error_data: Dict) -> float:
    BASELINE_FRAMES = 115
    TEMPORAL_BASELINE = 85.0  # Fallback if metadata unavailable
    
    metadata = error_data.get('metadata', {})
    num_frames = metadata.get('num_frames')
    
    if not num_frames:
        # Fallback if metadata unavailable
        return TEMPORAL_BASELINE
    
    # Calculate deviation from baseline
    frame_deviation = abs(num_frames - BASELINE_FRAMES)
    
    # Maximum acceptable deviation (50% from baseline)
    max_acceptable_deviation = BASELINE_FRAMES * 0.5  # 57.5 frames
    
    # Calculate quality (inverse of deviation)
    if frame_deviation >= max_acceptable_deviation:
        temporal_quality = 0.0
    else:
        temporal_quality = 1.0 - (frame_deviation / max_acceptable_deviation)
    
    # Scale from 0-1 to 70-100 range
    temporal_similarity = 70 + (temporal_quality * 30)
    
    return temporal_similarity
```

**Example Calculations**:

**Example 1: Perfect match**
```
num_frames = 115 (exactly baseline)
frame_deviation = |115 - 115| = 0
temporal_quality = 1.0 - (0 / 57.5) = 1.0
temporal_similarity = 70 + (1.0 × 30) = 100%
```

**Example 2: Slight deviation**
```
num_frames = 103
frame_deviation = |103 - 115| = 12
temporal_quality = 1.0 - (12 / 57.5) = 1.0 - 0.209 = 0.791
temporal_similarity = 70 + (0.791 × 30) = 70 + 23.7 = 93.7%
```

**Example 3: Large deviation**
```
num_frames = 75
frame_deviation = |75 - 115| = 40
temporal_quality = 1.0 - (40 / 57.5) = 1.0 - 0.696 = 0.304
temporal_similarity = 70 + (0.304 × 30) = 70 + 9.1 = 79.1%
```

**Example 4: Extreme deviation**
```
num_frames = 50
frame_deviation = |50 - 115| = 65
65 >= 57.5 → temporal_quality = 0.0
temporal_similarity = 70 + (0.0 × 30) = 70%
```

**Rationale**:
- Uses actual DTW output (aligned frame count)
- Not a fixed assumption - differs per user
- Lower deviation = better temporal match
- Baseline credit acknowledges successful alignment

---

### 4.1.3: Overall Score Computation
**Algorithm**: Weighted Linear Combination

**Purpose**: Combine structural and temporal scores into single performance metric

**Mathematical Formula**:
```
WEIGHT_STRUCTURAL = 0.6  (60%)
WEIGHT_TEMPORAL = 0.4    (40%)

overall_score = WEIGHT_STRUCTURAL × structural_similarity
              + WEIGHT_TEMPORAL × temporal_similarity
```

**Weight Rationale**:

| Aspect | Weight | Justification |
|--------|--------|---------------|
| **Structural** | 60% | Form and technique are primary in sports training |
| | | Spatial accuracy determines injury risk |
| | | Core coaching focus |
| **Temporal** | 40% | Timing matters but is secondary |
| | | Speed can improve with practice |
| | | DTW already handled basic synchronization |

**Implementation**:
```python
def compute_overall_score(structural: float, temporal: float) -> float:
    WEIGHT_STRUCTURAL = 0.6
    WEIGHT_TEMPORAL = 0.4
    
    overall = WEIGHT_STRUCTURAL * structural + WEIGHT_TEMPORAL * temporal
    return overall
```

**Example Calculation**:
```
User performance:
  structural_similarity = 68%
  temporal_similarity = 93.7%

overall_score = 0.6 × 68 + 0.4 × 93.7
              = 40.8 + 37.48
              = 78.28%
              ≈ 78.3%
```

**Properties**:
- **Range**: [0, 100] (both inputs in [0,100])
- **Weighted average**: True average (weights sum to 1.0)
- **Interpretable**: Percentage format is intuitive

---

## Complete Scoring Pipeline

### Data Flow
```
Level-3 JSON Input:
  ├─ joint_statistics (mean errors)
  └─ metadata (num_frames)
       │
       ├──→ Structural Similarity
       │     ├─ Extract mean errors
       │     ├─ Compute average
       │     ├─ Normalize by threshold
       │     └─ → structural_similarity (0-100%)
       │
       ├──→ Temporal Similarity
       │     ├─ Extract frame count
       │     ├─ Compute deviation from baseline
       │     ├─ Normalize deviation
       │     └─ → temporal_similarity (70-100%)
       │
       └──→ Overall Score
             ├─ Weighted combination
             └─ → overall_score (0-100%)
```

### JSON Output Schema
```json
{
  "structural_similarity": 68.0,
  "temporal_similarity": 93.7,
  "overall_score": 78.3,
  
  "weights": {
    "structural": 0.6,
    "temporal": 0.4
  },
  
  "metadata": {
    "source": "joint_errors_user1.json",
    "computation_date": "2026-01-20T13:45:00",
    "max_error_threshold": 1.5,
    "temporal_baseline": 85.0
  }
}
```

---

## Algorithm Properties

### Advantages
1. **Pure Aggregation**: No new analysis, only combines existing data
2. **Explainable**: Each score has clear formula and interpretation
3. **Transparent**: Weights and thresholds documented
4. **Undergraduate-Appropriate**: Simple math, defensible choices

### Design Decisions

#### Why These Formulas?
1. **Structural**: Inverse error mapping
   - Intuitive: less error = higher score
   - Threshold provides context (relative to worst case)
   - Simple linear transformation

2. **Temporal**: Frame count deviation
   - Proxy for DTW alignment quality
   - Different users have different aligned lengths
   - Baseline credit for successful alignment

3. **Overall**: Weighted average
   - Standard aggregation method
   - Weights based on domain knowledge (sports training)
   - Easy to adjust if requirements change

#### Alternative Approaches (Not Used)
1. **Non-linear mappings** (exponential, sigmoid)
   - Rejected: Too complex for undergraduate project
   - Current linear approach is sufficient and explainable

2. **Equal weights** (50-50)
   - Rejected: Doesn't reflect domain importance
   - Form > timing in sports training

3. **DTW cost as temporal score**
   - Considered but not  implemented
   - Would require saving DTW cost from Level-2
   - Frame count is simpler proxy

---

## Parameters Summary

| Parameter | Value | Purpose | Rationale |
|-----------|-------|---------|-----------|
| `MAX_ERROR_THRESHOLD` | 1.5 | Structural normalization | Empirical from data (0.3-1.4 range) |
| `WEIGHT_STRUCTURAL` | 0.6 | Structural importance | Form primary in sports |
| `WEIGHT_TEMPORAL` | 0.4 | Temporal importance | Timing secondary |
| `BASELINE_FRAMES` | 115 | Temporal baseline | Middle of observed range (103-129) |
| `TEMPORAL_BASELINE` | 85.0 | Fallback score | Conservative if metadata missing |
| Temporal Range | [70, 100] | Score scaling | Credit for successful alignment |

---

## Score Interpretation Guide

### Structural Similarity
- **90-100%**: Excellent form, very close to expert
- **75-89%**: Good form, minor deviations
- **60-74%**: Fair form, noticeable errors
- **Below 60%**: Poor form, significant corrections needed

### Temporal Similarity
- **95-100%**: Excellent timing, minimal compression/expansion
- **85-94%**: Good timing, slight speed variations
- **75-84%**: Fair timing, moderate speed differences
- **70-74%**: Poor timing, significant compression/expansion

### Overall Score
- **85-100%**: Excellent performance
- **70-84%**: Good performance
- **55-69%**: Fair performance
- **Below 55%**: Needs improvement

---

## Mathematical Correctness

### Score Bounds Proof
```
Proof that all scores ∈ [0, 100]:

Structural:
  mean_joint_error ≥ 0 (Euclidean distance)
  raw_score = (1 - mean_joint_error / 1.5) × 100
  if mean_joint_error = 0: raw_score = 100
  if mean_joint_error ≥ 1.5: raw_score ≤ 0
  with clamping: structural ∈ [0, 100] ✓

Temporal:
  temporalquality ∈ [0, 1] (by construction)
  temporal = 70 + (quality × 30)
  if quality = 0: temporal = 70
  if quality = 1: temporal = 100
  temporal ∈ [70, 100] ⊂ [0, 100] ✓

Overall:
  structural ∈ [0, 100], temporal ∈ [0, 100]
  overall = 0.6 × structural + 0.4 × temporal
  min: 0.6 × 0 + 0.4 × 0 = 0
  max: 0.6 × 100 + 0.4 × 100 = 100
  overall ∈ [0, 100] ✓
```

### Monotonicity Properties
```
Lower error → Higher score:
  ∂(structural_similarity) / ∂(mean_joint_error) = -100/1.5 < 0 ✓

Closer to baseline → Higher temporal score:
  ∂(temporal_similarity) / ∂(frame_deviation) = -30/57.5 < 0 ✓
```

---

## Conclusion

Level-4 provides a clean aggregation layer that:
- ✓ Consolidates Level-2 and Level-3 intelligence
- ✓ Uses simple, explainable formulas
- ✓ Produces intuitive 0-100% scores
- ✓ Has transparent, documented parameters
- ✓ Requires no new computation
- ✓ Is appropriate for undergraduate-level project

**Key Insight**: Separation of concerns
- Level-3: Raw error computation
- Level-4: Error → Score transformation
- Clean abstraction boundary

