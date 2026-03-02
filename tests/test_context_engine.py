"""
Test Suite for Context Engine

Comprehensive unit tests for all aggregation functions and edge cases.
"""

import pytest
import json
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_feedback.context_engine import (
    classify_score,
    classify_joints,
    analyze_phase,
    detect_temporal_trend,
    generate_context,
    load_raw_scores
)
from llm_feedback.config import (
    JOINT_TIER_HIGH,
    JOINT_TIER_MEDIUM,
    PHASE_EXCELLENT,
    PHASE_GOOD,
    PHASE_FAIR
)


# ============================================================================
# TEST: SCORE CLASSIFICATION
# ============================================================================

def test_score_classification_excellent():
    """Test excellent score classification."""
    assert classify_score(95.0) == "Excellent"
    assert classify_score(90.0) == "Excellent"
    assert classify_score(100.0) == "Excellent"


def test_score_classification_good():
    """Test good score classification."""
    assert classify_score(82.0) == "Good"
    assert classify_score(75.0) == "Good"
    assert classify_score(89.9) == "Good"


def test_score_classification_fair():
    """Test fair score classification."""
    assert classify_score(67.0) == "Fair"
    assert classify_score(60.0) == "Fair"
    assert classify_score(74.9) == "Fair"


def test_score_classification_needs_improvement():
    """Test needs improvement score classification."""
    assert classify_score(45.0) == "Needs Improvement"
    assert classify_score(0.0) == "Needs Improvement"
    assert classify_score(59.9) == "Needs Improvement"


# ============================================================================
# TEST: JOINT CLASSIFICATION
# ============================================================================

def test_joint_classification_tiers():
    """Test joint tier classification logic."""
    joint_stats = {
        "nose": {"mean": 0.24, "max": 0.44, "std": 0.09},
        "right_wrist": {"mean": 0.92, "max": 1.87, "std": 0.64},
        "left_shoulder": {"mean": 0.48, "max": 1.18, "std": 0.44}
    }
    
    result = classify_joints(joint_stats)
    
    # Major: right_wrist (0.92 > 0.7)
    assert len(result['major']) == 1
    assert result['major'][0]['joint'] == 'right_wrist'
    assert result['major'][0]['severity'] == 'major'
    
    # Moderate: left_shoulder (0.48 in 0.3-0.7)
    assert len(result['moderate']) == 1
    assert result['moderate'][0]['joint'] == 'left_shoulder'
    assert result['moderate'][0]['severity'] == 'moderate'
    
    # Minor: nose (0.24 < 0.3)
    assert len(result['minor']) == 1
    assert result['minor'][0]['joint'] == 'nose'
    assert result['minor'][0]['severity'] == 'minor'


def test_joint_classification_sorting():
    """Test that joints are sorted by error within each tier."""
    joint_stats = {
        "joint_a": {"mean": 0.8, "max": 1.5, "std": 0.3},
        "joint_b": {"mean": 1.2, "max": 2.0, "std": 0.4},
        "joint_c": {"mean": 0.9, "max": 1.6, "std": 0.35}
    }
    
    result = classify_joints(joint_stats)
    
    # All should be major (> 0.7)
    assert len(result['major']) == 3
    
    # Should be sorted: joint_b (1.2), joint_c (0.9), joint_a (0.8)
    assert result['major'][0]['joint'] == 'joint_b'
    assert result['major'][1]['joint'] == 'joint_c'
    assert result['major'][2]['joint'] == 'joint_a'


def test_joint_classification_null_handling():
    """Test that null joints are skipped."""
    joint_stats = {
        "nose": {"mean": 0.24, "max": 0.44, "std": 0.09},
        "left_eye": {"mean": None, "max": None, "std": None},
        "right_wrist": {"mean": 0.92, "max": 1.87, "std": 0.64}
    }
    
    result = classify_joints(joint_stats)
    
    # left_eye should be skipped
    all_joints = result['major'] + result['moderate'] + result['minor']
    joint_names = [j['joint'] for j in all_joints]
    
    assert 'left_eye' not in joint_names
    assert len(all_joints) == 2


# ============================================================================
# TEST: PHASE ANALYSIS
# ============================================================================

def test_phase_analysis_poor_quality():
    """Test phase quality classification for poor execution."""
    phase_data = {"nose": 0.22, "left_shoulder": 1.08, "right_wrist": 1.72}
    result = analyze_phase(phase_data, top_n=2)
    
    # Mean error ~1.0, should be "Poor" (> 0.8)
    assert result['quality'] == "Poor"
    assert result['mean_error'] > PHASE_FAIR


def test_phase_analysis_excellent_quality():
    """Test phase quality classification for excellent execution."""
    phase_data = {"nose": 0.15, "left_shoulder": 0.20, "right_wrist": 0.25}
    result = analyze_phase(phase_data, top_n=2)
    
    # Mean error ~0.2, should be "Excellent" (<= 0.3)
    assert result['quality'] == "Excellent"
    assert result['mean_error'] <= PHASE_EXCELLENT


def test_phase_analysis_dominant_joints():
    """Test identification of dominant joints."""
    phase_data = {
        "nose": 0.22,
        "left_shoulder": 1.08,
        "right_wrist": 1.72,
        "left_knee": 0.68,
        "right_ankle": 1.09
    }
    result = analyze_phase(phase_data, top_n=3)
    
    # Top 3: right_wrist (1.72), right_ankle (1.09), left_shoulder (1.08)
    assert len(result['dominant_joints']) == 3
    assert result['dominant_joints'][0]['joint'] == 'right_wrist'
    assert result['dominant_joints'][1]['joint'] == 'right_ankle'
    assert result['dominant_joints'][2]['joint'] == 'left_shoulder'


def test_phase_analysis_null_handling():
    """Test phase analysis with null joints."""
    phase_data = {
        "nose": 0.22,
        "left_eye": None,
        "right_eye": None,
        "left_shoulder": 0.48
    }
    result = analyze_phase(phase_data, top_n=2)
    
    # Should only use valid joints
    assert len(result['dominant_joints']) == 2
    
    # Null joints should not appear
    joint_names = [j['joint'] for j in result['dominant_joints']]
    assert 'left_eye' not in joint_names
    assert 'right_eye' not in joint_names


# ============================================================================
# TEST: TEMPORAL TREND DETECTION
# ============================================================================

def test_temporal_trend_improving():
    """Test detection of improving temporal pattern."""
    phase_analysis = {
        'early': {'mean_error': 1.2},
        'mid': {'mean_error': 0.5},
        'late': {'mean_error': 0.3}
    }
    result = detect_temporal_trend(phase_analysis)
    
    assert result['pattern'] == "improving"
    assert result['early_mean_error'] == 1.2
    assert result['late_mean_error'] == 0.3


def test_temporal_trend_degrading():
    """Test detection of degrading temporal pattern."""
    phase_analysis = {
        'early': {'mean_error': 0.3},
        'mid': {'mean_error': 0.6},
        'late': {'mean_error': 1.0}
    }
    result = detect_temporal_trend(phase_analysis)
    
    assert result['pattern'] == "degrading"


def test_temporal_trend_stable():
    """Test detection of stable temporal pattern."""
    phase_analysis = {
        'early': {'mean_error': 0.5},
        'mid': {'mean_error': 0.52},
        'late': {'mean_error': 0.54}
    }
    result = detect_temporal_trend(phase_analysis)
    
    # Difference 0.04 < 0.1 (STABILITY_THRESHOLD), should be stable
    assert result['pattern'] == "stable"


# ============================================================================
# TEST: END-TO-END CONTEXT GENERATION
# ============================================================================

def test_generate_context_structure():
    """Test full context generation with minimal data."""
    raw_scores = {
        'session_id': 'test-session-123',
        'pose_id': 'test-pose-456',
        'scores': {
            'structural': 58.5,
            'temporal': 80.8,
            'overall': 67.4
        },
        'error_statistics': {
            'metadata': {
                'num_frames': 103,
                'reference_duration': 78,
                'num_joints': 17,
                'alignment': 'DTW_pelvis_based'
            },
            'joint_statistics': {
                'nose': {'mean': 0.24, 'max': 0.44, 'std': 0.09},
                'right_wrist': {'mean': 0.92, 'max': 1.87, 'std': 0.64}
            },
            'phase_statistics': {
                'early': {'nose': 0.22, 'right_wrist': 1.72},
                'mid': {'nose': 0.25, 'right_wrist': 0.27},
                'late': {'nose': 0.25, 'right_wrist': 0.77}
            }
        },
        'metadata': {
            'pipeline_version': 'test_v1'
        }
    }
    
    context = generate_context(raw_scores)
    
    # Validate structure
    assert 'metadata' in context
    assert 'summary' in context
    assert 'joint_deviations' in context
    assert 'phase_analysis' in context
    assert 'temporal_trend' in context
    assert 'thresholds_used' in context


def test_generate_context_values():
    """Test that context values match input data."""
    raw_scores = {
        'session_id': 'test-session-123',
        'pose_id': 'test-pose-456',
        'scores': {
            'structural': 58.5,
            'temporal': 80.8,
            'overall': 67.4
        },
        'error_statistics': {
            'metadata': {
                'num_frames': 103,
                'reference_duration': 78,
                'num_joints': 17,
                'alignment': 'DTW_pelvis_based'
            },
            'joint_statistics': {
                'nose': {'mean': 0.24, 'max': 0.44, 'std': 0.09},
                'right_wrist': {'mean': 0.92, 'max': 1.87, 'std': 0.64}
            },
            'phase_statistics': {
                'early': {'nose': 0.22, 'right_wrist': 1.72},
                'mid': {'nose': 0.25, 'right_wrist': 0.27},
                'late': {'nose': 0.25, 'right_wrist': 0.77}
            }
        }
    }
    
    context = generate_context(raw_scores)
    
    # Validate values
    assert context['metadata']['session_id'] == 'test-session-123'
    assert context['summary']['overall_score'] == 67.4
    assert context['summary']['overall_assessment'] == 'Fair'
    assert len(context['joint_deviations']['major']) == 1
    assert context['joint_deviations']['major'][0]['joint'] == 'right_wrist'


def test_generate_context_missing_key():
    """Test error handling for missing required key."""
    raw_scores = {
        'session_id': 'test-session-123',
        # Missing 'scores' key
        'error_statistics': {
            'metadata': {},
            'joint_statistics': {},
            'phase_statistics': {'early': {}, 'mid': {}, 'late': {}}
        }
    }
    
    with pytest.raises(KeyError):
        generate_context(raw_scores)


# ============================================================================
# TEST: FILE I/O
# ============================================================================

def test_load_raw_scores_missing_file():
    """Test error handling for missing file."""
    with pytest.raises(FileNotFoundError):
        load_raw_scores('nonexistent_file.json')


# ============================================================================
# INTEGRATION TEST WITH REAL DATA
# ============================================================================

def test_integration_with_real_data():
    """Test end-to-end with actual pipeline output (if available)."""
    # This test requires an actual results.json file
    # Skip if file doesn't exist
    test_file = Path(__file__).parent.parent / 'data' / 'results' / '039ae972-178d-4520-86ff-b7c9b02d5d6b' / 'results.json'
    
    if not test_file.exists():
        pytest.skip("Real test data not available")
    
    raw_scores = load_raw_scores(str(test_file))
    context = generate_context(raw_scores)
    
    # Validate critical properties
    assert context['summary']['overall_score'] == 67.4
    assert context['summary']['overall_assessment'] == 'Fair'
    assert len(context['joint_deviations']['major']) > 0
    assert context['temporal_trend']['pattern'] in ['improving', 'degrading', 'stable']
    
    # Verify compactness (context should be much smaller than raw)
    # Raw results.json is ~2500 lines, context should be < 200
    context_json = json.dumps(context, indent=2)
    assert len(context_json.split('\n')) < 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
