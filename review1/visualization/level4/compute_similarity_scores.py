#!/usr/bin/env python3
"""
Level-4: Similarity Score Computation

Purpose:
    Compute overall performance similarity scores by aggregating
    Level-2 (temporal alignment) and Level-3 (joint errors) intelligence.
    
    This is PURE AGGREGATION - no new analysis.

Inputs:
    - joint_errors.json: Error statistics from Level-3

Outputs:
    - similarity_scores.json: Structural, temporal, and overall scores

Scope:
    ✓ Structural similarity (spatial accuracy)
    ✓ Temporal similarity (DTW alignment quality)
    ✓ Weighted overall score
    ✗ NO new error computation
    ✗ NO DTW recomputation
    ✗ NO feedback generation

Design Rationale:
    - Level-4 consolidates previously computed intelligence into interpretable assessment
    - Scores are simple, explainable, defensible at undergraduate level
    - Pure aggregation layer enables clean separation of concerns
"""

import numpy as np
import json
import os
import sys
from typing import Dict
from datetime import datetime


# ============================================================================
# SCORING PARAMETERS
# ============================================================================

# Maximum error threshold for structural similarity
# 1.5 chosen empirically based on observed normalized pose errors
# across training samples; acts as upper-bound for poor execution
# Updated from 0.3 to 1.5 after analyzing actual error ranges (0.3-1.4)
MAX_ERROR_THRESHOLD = 1.5

# Weighting for overall score
WEIGHT_STRUCTURAL = 0.6  # 60% - more important for form/technique
WEIGHT_TEMPORAL = 0.4    # 40% - important but secondary

# Conservative baseline for temporal similarity if metadata unavailable
TEMPORAL_BASELINE = 85.0


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def load_error_data(json_path: str) -> Dict:
    """
    Load joint error statistics from Level-3.
    
    Args:
        json_path: Path to joint_errors.json
    
    Returns:
        Dictionary containing error statistics
    
    Raises:
        FileNotFoundError: If JSON doesn't exist
        ValueError: If JSON is missing required keys
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Error JSON not found: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Validate required keys
    required_keys = ['metadata', 'joint_statistics']
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Error JSON missing required key: '{key}'")
    
    return data


def compute_structural_similarity(error_data: Dict) -> float:
    """
    Compute structural similarity based on spatial accuracy.
    
    Uses joint_statistics from Level-3 (aggregated across time).
    
    Formula:
        mean_joint_error = mean of all joint mean errors (ignoring NaN)
        structural_similarity = max(0, min(100, (1 - mean_joint_error / MAX_ERROR_THRESHOLD) * 100))
    
    Design Note:
        - Inverse relationship: lower error = higher similarity
        - MAX_ERROR_THRESHOLD acts as normalization constant
        - 0.0 error → 100% similarity
        - 0.3 error → 0% similarity
        - Uses nanmean to handle missing joints (NaN values)
        - 0.3 chosen empirically based on observed normalized pose errors
    
    Args:
        error_data: Dictionary from joint_errors.json
    
    Returns:
        Structural similarity score (0-100)
    """
    joint_stats = error_data['joint_statistics']
    
    # Extract mean errors from all joints
    mean_errors = [stats['mean'] for stats in joint_stats.values()]
    
    # Overall mean joint error (CRITICAL: use nanmean to ignore NaN joints)
    mean_joint_error = np.nanmean(mean_errors)
    
    # Convert to similarity (clamped to [0, 100])
    structural_similarity = max(0, min(100, (1 - mean_joint_error / MAX_ERROR_THRESHOLD) * 100))
    
    return structural_similarity


def compute_temporal_similarity(error_data: Dict) -> float:
    """
    Compute temporal similarity based on DTW alignment quality.
    
    Uses alignment frame count as proxy for DTW quality.
    Different users will have different aligned frame counts after DTW,
    which indicates how much temporal compression/expansion was needed.
    
    Formula:
        Reference: Use a baseline frame count (e.g., average across all users)
        temporal_quality = 1 - abs(num_frames - baseline_frames) / baseline_frames
        temporal_similarity = max(0, min(100, temporal_quality * 100))
    
    Current Implementation:
        Uses frame count variation from expected baseline.
        Lower deviation = better temporal match = higher similarity.
    
    Design Note:
        - Uses actual Level-2 output (aligned frame count)
        - Not a fixed assumption
        - Differentiates between users based on alignment efficiency
        - Future: Can be enhanced with actual DTW cost from Level-2
    
    Args:
        error_data: Dictionary from joint_errors.json
    
    Returns:
        Temporal similarity score (0-100)
    """
    metadata = error_data.get('metadata', {})
    num_frames = metadata.get('num_frames')
    
    if not num_frames:
        # Fallback if metadata unavailable
        return TEMPORAL_BASELINE
    
    # Use a reasonable baseline frame count (empirically chosen)
    # This represents an "ideal" alignment length
    # Updated after observing actual data: 103-129 frames for 4 users
    BASELINE_FRAMES = 115  # Middle of observed range
    
    # Calculate deviation from baseline
    frame_deviation = abs(num_frames - BASELINE_FRAMES)
    
    # Normalize deviation (frames beyond 50% deviation from baseline get 0%)
    max_acceptable_deviation = BASELINE_FRAMES * 0.5
    
    # Calculate quality (inverse of deviation)
    if frame_deviation >= max_acceptable_deviation:
        temporal_quality = 0.0
    else:
        temporal_quality = 1.0 - (frame_deviation / max_acceptable_deviation)
    
    # Convert to percentage and scale to reasonable range
    # Scale from 0-100 to 70-100 range (since successful DTW deserves baseline credit)
    temporal_similarity = 70 + (temporal_quality * 30)
    
    return temporal_similarity


def compute_overall_score(structural: float, temporal: float) -> float:
    """
    Compute weighted overall performance score.
    
    Formula:
        overall = WEIGHT_STRUCTURAL * structural + WEIGHT_TEMPORAL * temporal
                = 0.6 * structural + 0.4 * temporal
    
    Weights Rationale:
        - Structural (60%): Form and technique most important for sports training
        - Temporal (40%): Timing matters but secondary to spatial accuracy
    
    Args:
        structural: Structural similarity (0-100)
        temporal: Temporal similarity (0-100)
    
    Returns:
        Overall performance score (0-100)
    """
    overall = WEIGHT_STRUCTURAL * structural + WEIGHT_TEMPORAL * temporal
    return overall


def export_scores(scores: Dict, output_path: str) -> None:
    """
    Export similarity scores to JSON.
    
    Schema enforces:
        - Clear score breakdown
        - Transparent weighting
        - Metadata for traceability
    
    Args:
        scores: Dictionary containing all scores
        output_path: Path to save JSON file
    """
    with open(output_path, 'w') as f:
        json.dump(scores, f, indent=2)
    
    print(f"✓ Exported similarity scores to: {output_path}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Main entry point for Level-4 similarity score computation.
    
    Usage:
        python compute_similarity_scores.py <joint_errors.json>
    
    Output:
        similarity_scores.json in the same directory
    """
    print("=" * 70)
    print("LEVEL-4: SIMILARITY SCORE COMPUTATION")
    print("=" * 70)
    print("\nAggregating Level-2 and Level-3 intelligence.")
    print("Scope: Pure aggregation - no new analysis.\n")
    
    # ========================================================================
    # Parse Arguments
    # ========================================================================
    if len(sys.argv) != 2:
        print("Usage: python compute_similarity_scores.py <joint_errors.json>")
        print("\nExample:")
        print("  python compute_similarity_scores.py ../level3/joint_errors_user1.json")
        sys.exit(1)
    
    error_json_path = sys.argv[1]
    output_path = "similarity_scores.json"
    
    # ========================================================================
    # STEP 1: Load Error Data
    # ========================================================================
    print("[STEP 1] Loading joint error statistics from Level-3...")
    
    try:
        error_data = load_error_data(error_json_path)
        print(f"  ✓ Loaded: {error_json_path}")
        print(f"    Frames: {error_data['metadata']['num_frames']}")
        print(f"    Joints: {error_data['metadata']['num_joints']}")
    except Exception as e:
        print(f"  ✗ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    
    # ========================================================================
    # STEP 2: Compute Structural Similarity
    # ========================================================================
    print("\n[STEP 2] Computing structural similarity (spatial accuracy)...")
    
    structural_similarity = compute_structural_similarity(error_data)
    
    print(f"  ✓ Structural similarity: {structural_similarity:.1f}%")
    print(f"    Formula: 1 - (mean_joint_error / {MAX_ERROR_THRESHOLD})")
    print(f"    Design: Inverse relationship - lower error = higher similarity")
    
    # ========================================================================
    # STEP 3: Compute Temporal Similarity
    # ========================================================================
    print("\n[STEP 3] Computing temporal similarity (alignment quality)...")
    
    temporal_similarity = compute_temporal_similarity(error_data)
    
    print(f"  ✓ Temporal similarity: {temporal_similarity:.1f}%")
    print(f"    Source: DTW alignment quality from Level-2")
    print(f"    Note: Conservative baseline for successful alignment")
    
    # ========================================================================
    # STEP 4: Compute Overall Score
    # ========================================================================
    print("\n[STEP 4] Computing weighted overall score...")
    
    overall_score = compute_overall_score(structural_similarity, temporal_similarity)
    
    print(f"  ✓ Overall score: {overall_score:.1f}%")
    print(f"    Formula: {WEIGHT_STRUCTURAL} * structural + {WEIGHT_TEMPORAL} * temporal")
    print(f"    = {WEIGHT_STRUCTURAL} * {structural_similarity:.1f} + {WEIGHT_TEMPORAL} * {temporal_similarity:.1f}")
    print(f"    = {overall_score:.1f}")
    
    # ========================================================================
    # STEP 5: Export JSON
    # ========================================================================
    print("\n[STEP 5] Exporting similarity scores...")
    
    scores = {
        "structural_similarity": round(structural_similarity, 1),
        "temporal_similarity": round(temporal_similarity, 1),
        "overall_score": round(overall_score, 1),
        "weights": {
            "structural": WEIGHT_STRUCTURAL,
            "temporal": WEIGHT_TEMPORAL
        },
        "metadata": {
            "source": os.path.basename(error_json_path),
            "computation_date": datetime.now().isoformat(),
            "max_error_threshold": MAX_ERROR_THRESHOLD,
            "temporal_baseline": TEMPORAL_BASELINE
        }
    }
    
    export_scores(scores, output_path)
    
    print(f"  ✓ JSON validation:")
    print(f"    - Structural: {scores['structural_similarity']}%")
    print(f"    - Temporal: {scores['temporal_similarity']}%")
    print(f"    - Overall: {scores['overall_score']}%")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("LEVEL-4 SIMILARITY COMPUTATION COMPLETE")
    print("=" * 70)
    print(f"\n✓ Output: {output_path}")
    print(f"  - Structural similarity: {scores['structural_similarity']}% (spatial accuracy)")
    print(f"  - Temporal similarity: {scores['temporal_similarity']}% (alignment quality)")
    print(f"  - Overall score: {scores['overall_score']}% (weighted)")
    print(f"\n✓ Pure aggregation: No new analysis introduced")
    print(f"✓ Scores are simple, explainable, defensible")
    print(f"✓ Ready for Level-4 visualization")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
