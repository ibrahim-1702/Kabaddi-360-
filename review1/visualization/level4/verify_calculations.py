#!/usr/bin/env python3
"""
Sanity Check Script for Level-4 Similarity Calculations

Manually verifies that all similarity scores are computed correctly
by walking through the formulas step-by-step with real data.
"""

import json
import numpy as np

print("=" * 70)
print("LEVEL-4 SIMILARITY SCORE SANITY CHECK")
print("=" * 70)

# Load user 1 data as example
with open('../level3/joint_errors_user1.json', 'r') as f:
    data = json.load(f)

print("\n[1] STRUCTURAL SIMILARITY VERIFICATION")
print("-" * 70)

# Extract joint statistics
joint_stats = data['joint_statistics']
print(f"\nJoint statistics (mean errors):")

mean_errors = []
for joint_name, stats in joint_stats.items():
    mean_err = stats['mean']
    print(f"  {joint_name:15s}: {mean_err}")
    mean_errors.append(mean_err)

# Manual calculation
print(f"\n✓ All mean errors: {mean_errors}")
print(f"✓ Using np.nanmean to ignore NaN values...")

mean_joint_error = np.nanmean(mean_errors)
print(f"✓ Mean joint error = {mean_joint_error:.6f}")

MAX_ERROR_THRESHOLD = 1.5
print(f"✓ MAX_ERROR_THRESHOLD = {MAX_ERROR_THRESHOLD}")

structural_raw = (1 - mean_joint_error / MAX_ERROR_THRESHOLD) * 100
print(f"✓ Raw calculation: (1 - {mean_joint_error:.6f} / {MAX_ERROR_THRESHOLD}) * 100")
print(f"                  = {structural_raw:.6f}%")

structural_clamped = max(0, min(100, structural_raw))
print(f"✓ After clamping to [0, 100]: {structural_clamped:.1f}%")

print("\n" + "-" * 70)
print("\n[2] TEMPORAL SIMILARITY VERIFICATION")
print("-" * 70)

num_frames = data['metadata']['num_frames']
print(f"\n✓ Aligned frames (from metadata): {num_frames}")

BASELINE_FRAMES = 115
print(f"✓ BASELINE_FRAMES = {BASELINE_FRAMES}")

frame_deviation = abs(num_frames - BASELINE_FRAMES)
print(f"✓ Frame deviation: |{num_frames} - {BASELINE_FRAMES}| = {frame_deviation}")

max_acceptable_deviation = BASELINE_FRAMES * 0.5
print(f"✓ Max acceptable deviation: {BASELINE_FRAMES} * 0.5 = {max_acceptable_deviation}")

if frame_deviation >= max_acceptable_deviation:
    temporal_quality = 0.0
else:
    temporal_quality = 1.0 - (frame_deviation / max_acceptable_deviation)

print(f"✓ Temporal quality: 1.0 - ({frame_deviation} / {max_acceptable_deviation}) = {temporal_quality:.6f}")

temporal_similarity = 70 + (temporal_quality * 30)
print(f"✓ Temporal similarity: 70 + ({temporal_quality:.6f} * 30) = {temporal_similarity:.1f}%")

print("\n" + "-" * 70)
print("\n[3] OVERALL SCORE VERIFICATION")
print("-" * 70)

WEIGHT_STRUCTURAL = 0.6
WEIGHT_TEMPORAL = 0.4

print(f"\n✓ Weights: Structural={WEIGHT_STRUCTURAL}, Temporal={WEIGHT_TEMPORAL}")
print(f"✓ Structural similarity: {structural_clamped:.1f}%")
print(f"✓ Temporal similarity: {temporal_similarity:.1f}%")

overall_score = WEIGHT_STRUCTURAL * structural_clamped + WEIGHT_TEMPORAL * temporal_similarity
print(f"✓ Overall score: {WEIGHT_STRUCTURAL} * {structural_clamped:.1f} + {WEIGHT_TEMPORAL} * {temporal_similarity:.1f}")
print(f"                = {WEIGHT_STRUCTURAL * structural_clamped:.1f} + {WEIGHT_TEMPORAL * temporal_similarity:.1f}")
print(f"                = {overall_score:.1f}%")

print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)

print(f"\n✓ Structural Similarity: {structural_clamped:.1f}%")
print(f"✓ Temporal Similarity:   {temporal_similarity:.1f}%")
print(f"✓ Overall Score:         {overall_score:.1f}%")

print("\nNow compare with actual output from compute_similarity_scores.py")
print("for user 1 to verify they match!\n")
