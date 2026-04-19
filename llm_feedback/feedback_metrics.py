"""
LLM Feedback System - Automated Feedback Metrics

Computes quality metrics for LLM-generated feedback by comparing
the response text against the source context data.

Metrics:
1. Groundedness: Does the response reference actual data from context?
2. Hallucination: Does it invent joints/facts not in the data?
3. Specificity: Specific joint names vs generic vague advice?
4. Relevance: Does the tone match the actual score level?
5. Technique Awareness: Does it reference the specific technique name?
"""

import re
from typing import Dict, List


# All COCO-17 joint names the system uses
ALL_JOINT_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
]

# Generic vague terms that indicate low specificity
GENERIC_TERMS = [
    'your body', 'your form', 'your movement', 'your technique',
    'overall movement', 'body positioning', 'general form',
    'some areas', 'certain areas', 'various joints', 'multiple areas'
]

# Score-tone mapping for relevance check
SCORE_TONE_MAP = {
    'Excellent': ['excellent', 'great', 'outstanding', 'perfect', 'fantastic', 'superb', 'impressive'],
    'Good': ['good', 'solid', 'decent', 'well', 'nice', 'positive'],
    'Fair': ['fair', 'average', 'moderate', 'room for improvement', 'needs work', 'attention'],
    'Needs Improvement': ['poor', 'weak', 'significant', 'struggling', 'needs improvement', 'deficient', 'lacking']
}


def compute_groundedness(feedback_text: str, context: Dict) -> Dict:
    """
    Measure how well the feedback is grounded in actual context data.
    
    Checks if mentioned joints actually exist in the context deviations.
    
    Returns:
        score (1-5), details
    """
    feedback_lower = feedback_text.lower()
    
    # Get joints that are actually flagged in context (major + moderate)
    context_joints = set()
    for severity in ['major', 'moderate']:
        for joint in context.get('joint_deviations', {}).get(severity, []):
            context_joints.add(joint['joint'].replace('_', ' ').lower())
    
    # Get phase qualities from context
    context_phases = {}
    for phase in ['early', 'mid', 'late']:
        phase_data = context.get('phase_analysis', {}).get(phase, {})
        context_phases[phase] = phase_data.get('quality', 'Unknown')
    
    # Check how many context joints are mentioned in feedback
    mentioned_context_joints = 0
    for joint in context_joints:
        if joint in feedback_lower:
            mentioned_context_joints += 1
    
    # Check if assessment matches
    overall_assessment = context.get('summary', {}).get('overall_assessment', '')
    assessment_mentioned = overall_assessment.lower() in feedback_lower
    
    # Check if temporal trend is mentioned
    temporal_pattern = context.get('temporal_trend', {}).get('pattern', '')
    trend_mentioned = temporal_pattern.lower() in feedback_lower
    
    # Score calculation
    total_context_items = len(context_joints) + 2  # joints + assessment + trend
    mentioned_items = mentioned_context_joints + (1 if assessment_mentioned else 0) + (1 if trend_mentioned else 0)
    
    if total_context_items == 0:
        ratio = 1.0
    else:
        ratio = mentioned_items / total_context_items
    
    score = max(1, min(5, round(ratio * 5)))
    
    return {
        'score': score,
        'context_joints_total': len(context_joints),
        'context_joints_mentioned': mentioned_context_joints,
        'assessment_mentioned': assessment_mentioned,
        'trend_mentioned': trend_mentioned
    }


def compute_hallucination(feedback_text: str, context: Dict) -> Dict:
    """
    Detect if the feedback mentions joints or facts not present in context.
    
    Lower score = less hallucination = better.
    
    Returns:
        score (1-5 where 1=no hallucination, 5=heavy hallucination), details
    """
    feedback_lower = feedback_text.lower()
    
    # Get all joints mentioned in context (any severity)
    context_joints = set()
    for severity in ['major', 'moderate', 'minor']:
        for joint in context.get('joint_deviations', {}).get(severity, []):
            context_joints.add(joint['joint'].replace('_', ' ').lower())
    
    # Find all joint names mentioned in feedback
    mentioned_joints = set()
    for joint in ALL_JOINT_NAMES:
        readable = joint.replace('_', ' ').lower()
        if readable in feedback_lower:
            mentioned_joints.add(readable)
    
    # Hallucinated joints = mentioned but NOT in context
    hallucinated_joints = mentioned_joints - context_joints
    
    # Check for fabricated numeric claims (scores, percentages, angles)
    numeric_claims = len(re.findall(r'\b\d+[\.\d]*\s*(%|degrees?|percent)', feedback_lower))
    
    # Score: fewer hallucinations = lower score (better)
    hallucination_count = len(hallucinated_joints) + numeric_claims
    
    if hallucination_count == 0:
        score = 1
    elif hallucination_count <= 1:
        score = 2
    elif hallucination_count <= 3:
        score = 3
    elif hallucination_count <= 5:
        score = 4
    else:
        score = 5
    
    return {
        'score': score,
        'hallucinated_joints': list(hallucinated_joints),
        'numeric_claims': numeric_claims,
        'total_hallucinations': hallucination_count
    }


def compute_specificity(feedback_text: str, context: Dict) -> Dict:
    """
    Measure how specific the feedback is (specific joints vs generic advice).
    
    Returns:
        score (1-5), details
    """
    feedback_lower = feedback_text.lower()
    
    # Count specific joint name mentions
    specific_mentions = 0
    mentioned_joints = []
    for joint in ALL_JOINT_NAMES:
        readable = joint.replace('_', ' ').lower()
        if readable in feedback_lower:
            specific_mentions += 1
            mentioned_joints.append(readable)
    
    # Count generic term usage
    generic_mentions = 0
    found_generic = []
    for term in GENERIC_TERMS:
        if term in feedback_lower:
            generic_mentions += 1
            found_generic.append(term)
    
    # Count phase-specific mentions
    phase_mentions = 0
    for phase in ['early', 'mid', 'late']:
        if phase in feedback_lower:
            phase_mentions += 1
    
    # Score: more specific = higher score
    specificity_score = specific_mentions + phase_mentions - generic_mentions
    
    if specificity_score >= 5:
        score = 5
    elif specificity_score >= 3:
        score = 4
    elif specificity_score >= 1:
        score = 3
    elif specificity_score >= 0:
        score = 2
    else:
        score = 1
    
    return {
        'score': score,
        'specific_joints_mentioned': mentioned_joints,
        'specific_count': specific_mentions,
        'generic_terms_found': found_generic,
        'generic_count': generic_mentions,
        'phase_mentions': phase_mentions
    }


def compute_relevance(feedback_text: str, context: Dict) -> Dict:
    """
    Check if the feedback tone matches the actual performance score.
    
    Returns:
        score (1-5), details
    """
    feedback_lower = feedback_text.lower()
    
    overall_assessment = context.get('summary', {}).get('overall_assessment', 'Unknown')
    overall_score = context.get('summary', {}).get('overall_score', 0)
    
    # Get expected tone words for this assessment level
    expected_tones = SCORE_TONE_MAP.get(overall_assessment, [])
    
    # Count matching tone words
    matching_tones = [t for t in expected_tones if t in feedback_lower]
    
    # Check for mismatched tones (e.g., "excellent" in a "Needs Improvement" context)
    mismatched_tones = []
    for assessment, tones in SCORE_TONE_MAP.items():
        if assessment == overall_assessment:
            continue
        # Check for severe mismatches only
        if overall_assessment == 'Needs Improvement' and assessment == 'Excellent':
            for t in tones:
                if t in feedback_lower:
                    mismatched_tones.append(f"{t} (expected {overall_assessment})")
        elif overall_assessment == 'Excellent' and assessment == 'Needs Improvement':
            for t in tones:
                if t in feedback_lower:
                    mismatched_tones.append(f"{t} (expected {overall_assessment})")
    
    # Score calculation
    if len(matching_tones) >= 2 and len(mismatched_tones) == 0:
        score = 5
    elif len(matching_tones) >= 1 and len(mismatched_tones) == 0:
        score = 4
    elif len(matching_tones) >= 1 and len(mismatched_tones) <= 1:
        score = 3
    elif len(mismatched_tones) <= 2:
        score = 2
    else:
        score = 1
    
    return {
        'score': score,
        'overall_assessment': overall_assessment,
        'overall_score': overall_score,
        'matching_tones': matching_tones,
        'mismatched_tones': mismatched_tones
    }


def compute_technique_awareness(feedback_text: str, technique_name: str) -> Dict:
    """
    Check if the feedback references the specific technique name.
    
    Returns:
        score (1-5), details
    """
    feedback_lower = feedback_text.lower()
    technique_lower = technique_name.lower().strip()
    
    # Direct mention
    technique_mentioned = technique_lower in feedback_lower
    
    # Partial mention (individual words of technique name)
    technique_words = technique_lower.split()
    words_mentioned = [w for w in technique_words if w in feedback_lower and len(w) > 2]
    
    # Check for kabaddi-specific terms
    kabaddi_terms = ['raid', 'raider', 'kabaddi', 'touch', 'bonus', 'cant']
    kabaddi_mentions = [t for t in kabaddi_terms if t in feedback_lower]
    
    if technique_mentioned and len(kabaddi_mentions) >= 1:
        score = 5
    elif technique_mentioned:
        score = 4
    elif len(words_mentioned) >= 1 and len(kabaddi_mentions) >= 1:
        score = 3
    elif len(kabaddi_mentions) >= 1:
        score = 2
    else:
        score = 1
    
    return {
        'score': score,
        'technique_name': technique_name,
        'technique_mentioned': technique_mentioned,
        'technique_words_found': words_mentioned,
        'kabaddi_terms_found': kabaddi_mentions
    }


def compute_all_metrics(feedback_text: str, context: Dict, technique_name: str = "Unknown") -> Dict:
    """
    Compute all 5 metrics for a single feedback response.
    
    Returns:
        Dictionary with all metric scores and overall percentage.
    """
    groundedness = compute_groundedness(feedback_text, context)
    hallucination = compute_hallucination(feedback_text, context)
    specificity = compute_specificity(feedback_text, context)
    relevance = compute_relevance(feedback_text, context)
    technique = compute_technique_awareness(feedback_text, technique_name)
    
    # Overall score: sum of all metrics (hallucination is inverted: 5 - score)
    raw_total = (
        groundedness['score'] +
        (6 - hallucination['score']) +  # Invert: 1 hallucination = 5 points
        specificity['score'] +
        relevance['score'] +
        technique['score']
    )
    
    overall_percentage = round((raw_total / 25) * 100, 1)
    
    return {
        'groundedness': groundedness,
        'hallucination': hallucination,
        'specificity': specificity,
        'relevance': relevance,
        'technique_awareness': technique,
        'overall_score': raw_total,
        'overall_max': 25,
        'overall_percentage': overall_percentage
    }
