"""
LLM Feedback System - Configuration

This module defines all thresholds and constants used by the Context Engine.
All values are empirically derived from observed error distributions.
"""

# ============================================================================
# JOINT DEVIATION CLASSIFICATION THRESHOLDS
# ============================================================================

# Major issues: significant deviations requiring primary attention
JOINT_TIER_HIGH = 0.7

# Moderate issues: noticeable deviations but not critical
JOINT_TIER_MEDIUM = 0.3

# Note: Minor issues are implicitly defined as <= JOINT_TIER_MEDIUM


# ============================================================================
# PHASE QUALITY ASSESSMENT BANDS
# ============================================================================

# Excellent execution: minimal errors
PHASE_EXCELLENT = 0.3

# Good execution: acceptable errors
PHASE_GOOD = 0.5

# Fair execution: noticeable errors but not critical
PHASE_FAIR = 0.8

# Poor execution: implicitly defined as > PHASE_FAIR


# ============================================================================
# TEMPORAL TREND DETECTION
# ============================================================================

# Threshold for considering error progression as "stable"
# If abs(late_error - early_error) < STABILITY_THRESHOLD, trend is "stable"
STABILITY_THRESHOLD = 0.1


# ============================================================================
# SCORE ASSESSMENT BANDS
# ============================================================================

# Excellent performance
SCORE_EXCELLENT = 90

# Good performance
SCORE_GOOD = 75

# Fair performance (needs some improvement)
SCORE_FAIR = 60

# Needs improvement: implicitly defined as < SCORE_FAIR


# ============================================================================
# AGGREGATION PARAMETERS
# ============================================================================

# Number of top joints to report per phase
TOP_N_JOINTS_PER_PHASE = 3


# ============================================================================
# THRESHOLD EXPORT
# ============================================================================

def get_all_thresholds() -> dict:
    """
    Export all thresholds for transparency and traceability.
    
    Returns:
        Dictionary of all configuration thresholds
    """
    return {
        'joint_tier_high': JOINT_TIER_HIGH,
        'joint_tier_medium': JOINT_TIER_MEDIUM,
        'phase_excellent': PHASE_EXCELLENT,
        'phase_good': PHASE_GOOD,
        'phase_fair': PHASE_FAIR,
        'stability_threshold': STABILITY_THRESHOLD,
        'score_excellent': SCORE_EXCELLENT,
        'score_good': SCORE_GOOD,
        'score_fair': SCORE_FAIR,
        'top_n_joints_per_phase': TOP_N_JOINTS_PER_PHASE
    }


# ============================================================================
# LLM INFERENCE SETTINGS
# ============================================================================

# Ollama API configuration
LLM_ENDPOINT = "http://localhost:11434/api/generate"
LLM_MODEL = "llama3"

# LLM generation parameters
LLM_TEMPERATURE = 0.3  # Low temperature for consistent feedback
LLM_MAX_TOKENS = 1024
LLM_TIMEOUT = 180  # seconds (increased for larger models like llama3)
LLM_STREAM = False  # Don't stream, wait for complete response


def get_llm_config():
    """
    Get LLM configuration as a dictionary
    
    Returns:
        Dictionary of LLM configuration
    """
    return {
        'endpoint': LLM_ENDPOINT,
        'model': LLM_MODEL,
        'timeout': LLM_TIMEOUT,
        'temperature': LLM_TEMPERATURE,
        'max_tokens': LLM_MAX_TOKENS,
        'stream': LLM_STREAM
    }
