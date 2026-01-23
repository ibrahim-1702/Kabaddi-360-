"""
Feedback Generator for AR-Based Kabaddi Ghost Trainer

This module provides deterministic, rule-based feedback generation from
pose validation scores. Feedback is derived ONLY from metric values,
without hallucinating coaching advice.

Input: Score dictionary from PoseValidationMetrics
Output: Structured textual feedback

Constraints:
- No modification of metric values
- No direct pose/video analysis
- Deterministic and repeatable
- Explainable feedback logic
"""

from typing import Dict, Tuple


class FeedbackGenerator:
    """
    Rule-based feedback generator for pose validation scores.
    
    Maps numerical scores to structured textual feedback using
    predefined templates and score ranges.
    """
    
    # Score category thresholds
    CATEGORIES = {
        'excellent': (90, 100),
        'very_good': (80, 90),
        'good': (70, 80),
        'fair': (60, 70),
        'needs_improvement': (50, 60),
        'poor': (0, 50)
    }
    
    # Ghost validation feedback templates
    GHOST_FEEDBACK = {
        'excellent': {
            'overall': "AR ghost rendering is excellent. Near-perfect alignment with expert pose.",
            'structural': "Ghost pose structure is accurate.",
            'temporal': "Ghost motion timing is synchronized."
        },
        'very_good': {
            'overall': "AR ghost rendering is very good with minor deviations.",
            'structural': "Ghost pose structure has minor inaccuracies.",
            'temporal': "Ghost motion timing has minor sync issues."
        },
        'good': {
            'overall': "AR ghost rendering is acceptable but has noticeable gaps.",
            'structural': "Ghost pose structure shows noticeable deviations.",
            'temporal': "Ghost motion timing shows noticeable delays."
        },
        'fair': {
            'overall': "AR ghost rendering needs calibration. Significant deviations detected.",
            'structural': "Ghost pose structure has significant errors.",
            'temporal': "Ghost motion timing has significant sync issues."
        },
        'needs_improvement': {
            'overall': "AR ghost rendering has major issues. Pipeline needs verification.",
            'structural': "Ghost pose structure is poorly aligned.",
            'temporal': "Ghost motion timing is poorly synchronized."
        },
        'poor': {
            'overall': "AR ghost rendering has critical issues. Check AR tracking and pose estimation.",
            'structural': "Ghost pose structure is critically misaligned.",
            'temporal': "Ghost motion timing is critically out of sync."
        }
    }
    
    # User evaluation feedback templates
    USER_FEEDBACK = {
        'excellent': {
            'overall': "Outstanding performance! You matched the expert technique exceptionally well.",
            'structural': "Your pose structure is accurate.",
            'temporal': "Your timing is well synchronized."
        },
        'very_good': {
            'overall': "Great job! Your performance is very good with minor areas for improvement.",
            'structural': "Your pose structure is mostly accurate.",
            'temporal': "Your timing is mostly synchronized."
        },
        'good': {
            'overall': "Good effort. Your performance is acceptable with some noticeable gaps.",
            'structural': "Your pose structure needs minor adjustments.",
            'temporal': "Your timing needs minor adjustments."
        },
        'fair': {
            'overall': "Fair attempt. Focus on matching the ghost more closely.",
            'structural': "Your pose structure has noticeable differences.",
            'temporal': "Your timing has noticeable delays."
        },
        'needs_improvement': {
            'overall': "Keep practicing. Your performance needs significant improvement.",
            'structural': "Your pose structure needs significant work.",
            'temporal': "Your timing needs significant work."
        },
        'poor': {
            'overall': "More practice needed. Focus on the basics and try matching individual poses first.",
            'structural': "Your pose structure differs greatly from the target.",
            'temporal': "Your timing is not aligned with the motion."
        }
    }
    
    def __init__(self):
        """Initialize feedback generator."""
        pass
    
    @staticmethod
    def _categorize_score(score: float) -> str:
        """
        Map a numerical score to its category.
        
        Args:
            score: Score value [0, 100]
        
        Returns:
            Category string (e.g., 'excellent', 'good', 'poor')
        """
        for category, (min_score, max_score) in FeedbackGenerator.CATEGORIES.items():
            if min_score <= score < max_score:
                return category
        
        # Handle edge case: score == 100
        if score == 100:
            return 'excellent'
        
        # Fallback (should never reach here with valid input)
        return 'poor'
    
    def generate_ghost_feedback(self, scores: Dict[str, float]) -> Dict[str, str]:
        """
        Generate feedback for ghost validation.
        
        Args:
            scores: Dictionary with keys:
                - 'structural': float [0, 100]
                - 'temporal': float [0, 100]
                - 'overall': float [0, 100]
        
        Returns:
            Dictionary with feedback text:
                - 'overall': Overall feedback message
                - 'structural': Structural component feedback
                - 'temporal': Temporal component feedback
                - 'category': Score category (for reference)
        """
        overall_score = scores['overall']
        structural_score = scores['structural']
        temporal_score = scores['temporal']
        
        # Categorize scores
        overall_category = self._categorize_score(overall_score)
        structural_category = self._categorize_score(structural_score)
        temporal_category = self._categorize_score(temporal_score)
        
        # Generate feedback
        feedback = {
            'overall': self.GHOST_FEEDBACK[overall_category]['overall'],
            'structural': self.GHOST_FEEDBACK[structural_category]['structural'],
            'temporal': self.GHOST_FEEDBACK[temporal_category]['temporal'],
            'category': overall_category,
            'scores': scores  # Include original scores for reference
        }
        
        return feedback
    
    def generate_user_feedback(self, scores: Dict[str, float]) -> Dict[str, str]:
        """
        Generate feedback for user evaluation.
        
        Args:
            scores: Dictionary with keys:
                - 'structural': float [0, 100]
                - 'temporal': float [0, 100]
                - 'overall': float [0, 100]
        
        Returns:
            Dictionary with feedback text:
                - 'overall': Overall feedback message
                - 'structural': Structural component feedback
                - 'temporal': Temporal component feedback
                - 'category': Score category (for reference)
        """
        overall_score = scores['overall']
        structural_score = scores['structural']
        temporal_score = scores['temporal']
        
        # Categorize scores
        overall_category = self._categorize_score(overall_score)
        structural_category = self._categorize_score(structural_score)
        temporal_category = self._categorize_score(temporal_score)
        
        # Generate feedback
        feedback = {
            'overall': self.USER_FEEDBACK[overall_category]['overall'],
            'structural': self.USER_FEEDBACK[structural_category]['structural'],
            'temporal': self.USER_FEEDBACK[temporal_category]['temporal'],
            'category': overall_category,
            'scores': scores  # Include original scores for reference
        }
        
        return feedback
    
    def generate_detailed_feedback(
        self, 
        scores: Dict[str, float], 
        mode: str = 'user'
    ) -> str:
        """
        Generate detailed multi-line feedback string.
        
        Args:
            scores: Score dictionary
            mode: 'user' or 'ghost'
        
        Returns:
            Multi-line formatted feedback string
        """
        if mode == 'ghost':
            feedback = self.generate_ghost_feedback(scores)
        else:
            feedback = self.generate_user_feedback(scores)
        
        detailed_text = f"""
Performance Summary
===================
Overall Score: {feedback['scores']['overall']:.1f}/100 ({feedback['category'].replace('_', ' ').title()})

{feedback['overall']}

Component Breakdown:
- Structural Accuracy: {feedback['scores']['structural']:.1f}/100
  {feedback['structural']}

- Temporal Accuracy: {feedback['scores']['temporal']:.1f}/100
  {feedback['temporal']}
"""
        return detailed_text.strip()
    
    def get_score_category_rules(self) -> str:
        """
        Return a formatted table of score categorization rules.
        
        Returns:
            String containing the rules table
        """
        table = """
Score Categorization Rules
==========================

Score Range | Category           | Description
------------|-------------------|----------------------------------
90-100      | Excellent          | Near-perfect alignment
80-89       | Very Good          | Minor issues
70-79       | Good               | Acceptable performance
60-69       | Fair               | Noticeable gaps
50-59       | Needs Improvement  | Significant issues
0-49        | Poor               | Major problems
"""
        return table.strip()


# ==================== USAGE EXAMPLE ====================

if __name__ == "__main__":
    """
    Example usage demonstrating feedback generation for different score ranges.
    """
    
    # Initialize feedback generator
    generator = FeedbackGenerator()
    
    print("=" * 70)
    print("FEEDBACK GENERATOR - DEMONSTRATION")
    print("=" * 70)
    print()
    
    # Print categorization rules
    print(generator.get_score_category_rules())
    print()
    print("=" * 70)
    print()
    
    # Test cases covering all score ranges
    test_cases = [
        {
            'name': 'Excellent Performance',
            'scores': {'structural': 95.0, 'temporal': 92.0, 'overall': 93.5}
        },
        {
            'name': 'Very Good Performance',
            'scores': {'structural': 85.0, 'temporal': 83.0, 'overall': 84.0}
        },
        {
            'name': 'Good Performance',
            'scores': {'structural': 75.0, 'temporal': 72.0, 'overall': 73.5}
        },
        {
            'name': 'Fair Performance',
            'scores': {'structural': 65.0, 'temporal': 62.0, 'overall': 63.5}
        },
        {
            'name': 'Needs Improvement',
            'scores': {'structural': 55.0, 'temporal': 52.0, 'overall': 53.5}
        },
        {
            'name': 'Poor Performance',
            'scores': {'structural': 35.0, 'temporal': 32.0, 'overall': 33.5}
        }
    ]
    
    # Generate and display feedback for each test case
    for i, test in enumerate(test_cases, 1):
        print(f"TEST CASE {i}: {test['name']}")
        print("-" * 70)
        
        # User feedback
        print("\n[USER EVALUATION MODE]")
        detailed = generator.generate_detailed_feedback(test['scores'], mode='user')
        print(detailed)
        
        print("\n" + "=" * 70 + "\n")
    
    # Demonstrate determinism
    print("DETERMINISM VERIFICATION")
    print("-" * 70)
    test_score = {'structural': 75.0, 'temporal': 72.0, 'overall': 73.5}
    
    feedback1 = generator.generate_user_feedback(test_score)
    feedback2 = generator.generate_user_feedback(test_score)
    
    print(f"Test Score: {test_score}")
    print(f"\nFirst Call:  {feedback1['overall']}")
    print(f"Second Call: {feedback2['overall']}")
    print(f"\nAre they identical? {feedback1 == feedback2}")
    print()
    print("=" * 70)
