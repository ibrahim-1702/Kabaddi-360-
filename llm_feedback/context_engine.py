"""
LLM Feedback System - Context Engine

This module transforms raw pipeline output into canonical, LLM-ready context JSON.

Design Principles:
- Deterministic aggregation only (no probabilistic methods)
- Threshold-based classification (clear, explainable rules)
- Collapse frame noise into phase-level insights
- Distinguish dominant vs secondary deviations
- Review-safe output (all decisions traceable)

Input: Complete results.json from evaluation pipeline
Output: Compact, canonical context JSON ready for LLM reasoning
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path

# Import configuration
from .config import (
    JOINT_TIER_HIGH,
    JOINT_TIER_MEDIUM,
    PHASE_EXCELLENT,
    PHASE_GOOD,
    PHASE_FAIR,
    STABILITY_THRESHOLD,
    SCORE_EXCELLENT,
    SCORE_GOOD,
    SCORE_FAIR,
    TOP_N_JOINTS_PER_PHASE,
    get_all_thresholds
)


# ============================================================================
# CORE AGGREGATION FUNCTIONS
# ============================================================================

def classify_score(score: float) -> str:
    """
    Map similarity score to qualitative assessment band.
    
    Args:
        score: Similarity score (0-100)
        
    Returns:
        Assessment: "Excellent" | "Good" | "Fair" | "Needs Improvement"
    """
    if score >= SCORE_EXCELLENT:
        return "Excellent"
    elif score >= SCORE_GOOD:
        return "Good"
    elif score >= SCORE_FAIR:
        return "Fair"
    else:
        return "Needs Improvement"


def classify_joints(joint_stats: Dict[str, Dict[str, Optional[float]]]) -> Dict[str, List[Dict]]:
    """
    Classify joints into tiered categories based on mean error.
    
    Tiers:
    - Major: mean_error > JOINT_TIER_HIGH (e.g., > 0.7)
    - Moderate: JOINT_TIER_MEDIUM < mean_error <= JOINT_TIER_HIGH (e.g., 0.3-0.7)
    - Minor: mean_error <= JOINT_TIER_MEDIUM (e.g., <= 0.3)
    
    Args:
        joint_stats: Joint statistics from pipeline (contains mean, max, std per joint)
        
    Returns:
        Dictionary with 'major', 'moderate', 'minor' keys, each containing list of joint objects
    """
    major = []
    moderate = []
    minor = []
    
    for joint_name, stats in joint_stats.items():
        mean_error = stats.get('mean')
        max_error = stats.get('max')
        
        # Skip null joints (not detected or invalid)
        if mean_error is None or max_error is None:
            continue
        
        joint_obj = {
            'joint': joint_name,
            'mean_error': round(mean_error, 2),
            'max_error': round(max_error, 2),
            'severity': None
        }
        
        # Classify based on mean error
        if mean_error > JOINT_TIER_HIGH:
            joint_obj['severity'] = 'major'
            major.append(joint_obj)
        elif mean_error > JOINT_TIER_MEDIUM:
            joint_obj['severity'] = 'moderate'
            moderate.append(joint_obj)
        else:
            joint_obj['severity'] = 'minor'
            minor.append(joint_obj)
    
    # Sort each tier by mean error (descending) for prioritization
    major.sort(key=lambda x: x['mean_error'], reverse=True)
    moderate.sort(key=lambda x: x['mean_error'], reverse=True)
    minor.sort(key=lambda x: x['mean_error'], reverse=True)
    
    return {
        'major': major,
        'moderate': moderate,
        'minor': minor
    }


def analyze_phase(phase_data: Dict[str, Optional[float]], top_n: int = TOP_N_JOINTS_PER_PHASE) -> Dict:
    """
    Analyze a single phase and identify quality + dominant joints.
    
    Args:
        phase_data: Phase statistics (joint_name -> error)
        top_n: Number of top error joints to report
        
    Returns:
        Dictionary containing:
        - quality: "Excellent" | "Good" |"Fair" | "Poor"
        - mean_error: Average error across all valid joints
        - dominant_joints: List of top N joints with highest errors
    """
    import math
    
    # Filter out None values and NaN (missing/invalid joints)
    valid_joints = {
        k: v for k, v in phase_data.items() 
        if v is not None and not (isinstance(v, float) and math.isnan(v))
    }
    
    if not valid_joints:
        # No valid joints - assume perfect (this happens when all joints are 0.0)
        return {
            'quality': 'Excellent',
            'mean_error': 0.0,
            'dominant_joints': []
        }
    
    # Calculate mean phase error
    mean_error = sum(valid_joints.values()) / len(valid_joints)
    
    # Classify phase quality based on mean error
    if mean_error <= PHASE_EXCELLENT:
        quality = "Excellent"
    elif mean_error <= PHASE_GOOD:
        quality = "Good"
    elif mean_error <= PHASE_FAIR:
        quality = "Fair"
    else:
        quality = "Poor"
    
    # Identify dominant joints (top N by error)
    sorted_joints = sorted(
        valid_joints.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    dominant_joints = [
        {'joint': joint, 'error': round(error, 2)}
        for joint, error in sorted_joints[:top_n]
    ]
    
    return {
        'quality': quality,
        'mean_error': round(mean_error, 2),
        'dominant_joints': dominant_joints
    }


def detect_temporal_trend(phase_analysis: Dict[str, Dict]) -> Dict:
    """
    Detect temporal error progression pattern across phases.
    
    Patterns:
    - "improving": Late error < Early error (beyond stability threshold)
    - "degrading": Late error > Early error (beyond stability threshold)
    - "stable": Difference within stability threshold
    
    Args:
        phase_analysis: Analysis results for all phases
        
    Returns:
        Dictionary containing:
        - pattern: "improving" | "degrading" | "stable"
        - early_mean_error: Error in early phase
        - mid_mean_error: Error in mid phase
        - late_mean_error: Error in late phase
    """
    import math
    
    early_error = phase_analysis['early']['mean_error']
    mid_error = phase_analysis['mid']['mean_error']
    late_error = phase_analysis['late']['mean_error']
    
    # Handle NaN cases - treat as perfect (0.0)
    if isinstance(early_error, float) and math.isnan(early_error):
        early_error = 0.0
    if isinstance(mid_error, float) and math.isnan(mid_error):
        mid_error = 0.0
    if isinstance(late_error, float) and math.isnan(late_error):
        late_error = 0.0
    
    # Determine temporal pattern
    error_delta = late_error - early_error
    
    # If all errors are zero or near-zero, it's stable/perfect
    if abs(error_delta) < STABILITY_THRESHOLD:
        pattern = "stable"
    elif late_error < early_error:
        pattern = "improving"
    else:
        pattern = "degrading"
    
    return {
        'pattern': pattern,
        'early_mean_error': early_error,
        'mid_mean_error': mid_error,
        'late_mean_error': late_error
    }


# ============================================================================
# MAIN CONTEXT GENERATION
# ============================================================================

def generate_context(raw_scores: Dict) -> Dict:
    """
    Transform raw pipeline output into canonical context JSON.
    
    This is the main entry point for the Context Engine. It performs pure
    aggregation on existing pipeline output without introducing new analysis.
    
    Args:
        raw_scores: Complete results.json from evaluation pipeline
        
    Returns:
        Canonical context JSON ready for LLM processing
        
    Raises:
        KeyError: If required keys are missing from input
        ValueError: If input data is malformed
    """
    # Validate input structure
    required_keys = ['scores', 'error_statistics', 'session_id', 'pose_id']
    for key in required_keys:
        if key not in raw_scores:
            raise KeyError(f"Missing required key in raw_scores: '{key}'")
    
    # Extract input data
    scores = raw_scores['scores']
    error_stats = raw_scores['error_statistics']
    joint_stats = error_stats['joint_statistics']
    phase_stats = error_stats['phase_statistics']
    metadata = error_stats['metadata']
    
    # 1. SCORE CONTEXTUALIZATION
    summary = {
        'overall_score': scores['overall'],
        'overall_assessment': classify_score(scores['overall']),
        'structural_score': scores['structural'],
        'structural_assessment': classify_score(scores['structural']),
        'temporal_score': scores['temporal'],
        'temporal_assessment': classify_score(scores['temporal'])
    }
    
    # 2. JOINT DEVIATION CLASSIFICATION
    joint_deviations = classify_joints(joint_stats)
    
    # 3. PHASE ANALYSIS
    phase_analysis = {}
    for phase in ['early', 'mid', 'late']:
        phase_analysis[phase] = analyze_phase(
            phase_stats[phase],
            top_n=TOP_N_JOINTS_PER_PHASE
        )
    
    # 4. TEMPORAL TREND DETECTION
    temporal_trend = detect_temporal_trend(phase_analysis)
    
    # 5. ASSEMBLE CANONICAL CONTEXT
    context = {
        'metadata': {
            'session_id': raw_scores['session_id'],
            'pose_id': raw_scores['pose_id'],
            'num_frames': metadata['num_frames'],
            'reference_duration': metadata['reference_duration'],
            'pipeline_version': raw_scores.get('metadata', {}).get('pipeline_version', 'unknown')
        },
        'summary': summary,
        'joint_deviations': joint_deviations,
        'phase_analysis': phase_analysis,
        'temporal_trend': temporal_trend,
        'thresholds_used': get_all_thresholds()
    }
    
    return context


# ============================================================================
# FILE I/O UTILITIES
# ============================================================================

def load_raw_scores(file_path: str) -> Dict:
    """
    Load raw pipeline output from JSON file.
    
    Args:
        file_path: Path to results.json
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {file_path}")
    
    with open(path, 'r') as f:
        return json.load(f)


def save_context(context: Dict, output_path: str) -> None:
    """
    Save canonical context to JSON file.
    
    Args:
        context: Canonical context dictionary
        output_path: Path to save context.json
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(context, f, indent=2)


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """
    Command-line interface for Context Engine.
    
    Usage:
        python -m llm_feedback.context_engine <results.json> [output.json]
    """
    import sys
    
    print("=" * 70)
    print("CONTEXT ENGINE - LLM Feedback System")
    print("=" * 70)
    print("\nTransforming raw pipeline output into canonical context JSON.\n")
    
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python -m llm_feedback.context_engine <results.json> [output.json]")
        print("\nExample:")
        print("  python -m llm_feedback.context_engine data/results/session_id/results.json")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "context.json"
    
    try:
        # Load raw scores
        print(f"[1/3] Loading raw scores from: {input_path}")
        raw_scores = load_raw_scores(input_path)
        print(f"  ✓ Session: {raw_scores.get('session_id', 'unknown')}")
        print(f"  ✓ Frames: {raw_scores['error_statistics']['metadata']['num_frames']}")
        
        # Generate context
        print(f"\n[2/3] Generating canonical context...")
        context = generate_context(raw_scores)
        print(f"  ✓ Overall: {context['summary']['overall_score']}% ({context['summary']['overall_assessment']})")
        print(f"  ✓ Major deviations: {len(context['joint_deviations']['major'])}")
        print(f"  ✓ Temporal trend: {context['temporal_trend']['pattern']}")
        
        # Save context
        print(f"\n[3/3] Saving context to: {output_path}")
        save_context(context, output_path)
        print(f"  ✓ Context saved successfully")
        
        print("\n" + "=" * 70)
        print("CONTEXT GENERATION COMPLETE")
        print("=" * 70)
        print(f"\n✓ Output: {output_path}")
        print(f"✓ Compact, LLM-ready context generated")
        print(f"✓ All aggregations deterministic and traceable")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
