"""
LLM Feedback System - Prompt Builder

This module builds LLM prompts from canonical context JSON.

Responsibilities:
- Load system prompt from file
- Build instruction prompt by injecting context fields
- Enforce field consumption rules (major/moderate/minor)
- No LLM calls (pure prompt construction)

Design:
- Framework-agnostic (no Django dependencies)
- Fully deterministic (same context → same prompt)
- Clean separation from LLM inference
"""

from pathlib import Path
from typing import Dict, List


# Path to prompt template files
PROMPTS_DIR = Path(__file__).parent / 'prompts'
SYSTEM_PROMPT_FILE = PROMPTS_DIR / 'system_prompt.txt'
INSTRUCTION_TEMPLATE_FILE = PROMPTS_DIR / 'instruction_template.txt'


# ============================================================================
# SYSTEM PROMPT LOADER
# ============================================================================

def load_system_prompt() -> str:
    """
    Load system prompt from file.
    
    Returns:
        System prompt text
        
    Raises:
        FileNotFoundError: If system prompt file doesn't exist
    """
    if not SYSTEM_PROMPT_FILE.exists():
        raise FileNotFoundError(f"System prompt not found: {SYSTEM_PROMPT_FILE}")
    
    with open(SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read().strip()


# ============================================================================
# INSTRUCTION PROMPT BUILDER
# ============================================================================

def build_instruction_prompt(context: Dict, technique_name: str = "Unknown Technique") -> str:
    """
    Build instruction prompt from canonical context JSON.
    
    Field Consumption Rules:
    - Use all major deviations
    - Use at most top 3 moderate deviations
    - Never include minor deviations
    
    Args:
        context: Canonical context JSON from Context Engine
        technique_name: Name of the kabaddi technique being evaluated
        
    Returns:
        Filled instruction prompt ready for LLM
        
    Raises:
        KeyError: If required context fields are missing
        FileNotFoundError: If template file doesn't exist
    """
    # Load template
    if not INSTRUCTION_TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"Instruction template not found: {INSTRUCTION_TEMPLATE_FILE}")
    
    with open(INSTRUCTION_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Extract summary assessments
    summary = context['summary']
    overall_assessment = summary['overall_assessment']
    structural_assessment = summary['structural_assessment']
    temporal_assessment = summary['temporal_assessment']
    
    # Extract and format major deviations
    major_devs = context['joint_deviations']['major']
    major_list = _format_joint_list(major_devs)
    
    # Conditionally include moderate deviations (max 3)
    moderate_devs = context['joint_deviations']['moderate']
    moderate_section = _format_moderate_section(moderate_devs, max_count=3)
    
    # Extract phase analysis
    phases = context['phase_analysis']
    
    early_quality = phases['early']['quality']
    early_dominant = _format_dominant_joints(phases['early']['dominant_joints'])
    
    mid_quality = phases['mid']['quality']
    mid_dominant = _format_dominant_joints(phases['mid']['dominant_joints'])
    
    late_quality = phases['late']['quality']
    late_dominant = _format_dominant_joints(phases['late']['dominant_joints'])
    
    # Extract temporal trend
    temporal_pattern = context['temporal_trend']['pattern']
    
    # Fill template
    filled_prompt = template.format(
        technique_name=technique_name,
        overall_assessment=overall_assessment,
        structural_assessment=structural_assessment,
        temporal_assessment=temporal_assessment,
        major_deviations_list=major_list,
        moderate_deviations_section=moderate_section,
        early_quality=early_quality,
        early_dominant_joints=early_dominant,
        mid_quality=mid_quality,
        mid_dominant_joints=mid_dominant,
        late_quality=late_quality,
        late_dominant_joints=late_dominant,
        temporal_pattern=temporal_pattern
    )
    
    return filled_prompt


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_joint_list(joints: List[Dict]) -> str:
    """
    Format list of joints for prompt.
    
    Args:
        joints: List of joint objects with 'joint' field
        
    Returns:
        Formatted string with one joint per line
    """
    if not joints:
        return "None"
    
    formatted = []
    for joint in joints:
        joint_name = joint['joint'].replace('_', ' ').title()
        formatted.append(f"- {joint_name}")
    
    return '\n'.join(formatted)


def _format_moderate_section(moderate_devs: List[Dict], max_count: int = 3) -> str:
    """
    Format moderate deviations section (optional, max 3).
    
    Rules:
    - If 0 moderate deviations: return empty string
    - If 1-3 moderate deviations: include them
    - If > 3 moderate deviations: include only top 3
    
    Args:
        moderate_devs: List of moderate deviation objects
        max_count: Maximum number of moderate deviations to include
        
    Returns:
        Formatted section or empty string
    """
    if not moderate_devs:
        return ""
    
    # Take only top N
    selected_devs = moderate_devs[:max_count]
    
    joint_names = [
        dev['joint'].replace('_', ' ').title()
        for dev in selected_devs
    ]
    
    joint_list = ', '.join(joint_names)
    
    return f"\n## Secondary Areas (optional mention)\n{joint_list}"


def _format_dominant_joints(dominant_joints: List[Dict]) -> str:
    """
    Format dominant joints for a phase.
    
    Args:
        dominant_joints: List of dominant joint objects with 'joint' field
        
    Returns:
        Comma-separated joint names
    """
    if not dominant_joints:
        return "None"
    
    joint_names = [
        dj['joint'].replace('_', ' ').title()
        for dj in dominant_joints
    ]
    
    return ', '.join(joint_names)


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def build_prompts(context: Dict, technique_name: str = "Unknown Technique") -> Dict[str, str]:
    """
    Build both system and instruction prompts from context.
    
    Convenience function for getting both prompts at once.
    
    Args:
        context: Canonical context JSON from Context Engine
        technique_name: Name of the kabaddi technique being evaluated
        
    Returns:
        Dictionary with 'system' and 'instruction' keys
    """
    return {
        'system': load_system_prompt(),
        'instruction': build_instruction_prompt(context, technique_name=technique_name)
    }


# ============================================================================
# VALIDATION
# ============================================================================

def validate_context(context: Dict) -> bool:
    """
    Validate that context has all required fields for prompt building.
    
    Args:
        context: Context dictionary to validate
        
    Returns:
        True if valid
        
    Raises:
        KeyError: If required field is missing
    """
    required_fields = [
        ('summary', 'overall_assessment'),
        ('summary', 'structural_assessment'),
        ('summary', 'temporal_assessment'),
        ('joint_deviations', 'major'),
        ('joint_deviations', 'moderate'),
        ('phase_analysis', 'early'),
        ('phase_analysis', 'mid'),
        ('phase_analysis', 'late'),
        ('temporal_trend', 'pattern')
    ]
    
    for *path, field in required_fields:
        obj = context
        for key in path:
            if key not in obj:
                raise KeyError(f"Missing required field: {'.'.join(path + [field])}")
            obj = obj[key]
        
        if field not in obj:
            raise KeyError(f"Missing required field: {'.'.join(path + [field])}")
    
    return True


if __name__ == "__main__":
    print("Prompt Builder Module")
    print("=" * 70)
    print("\nThis module builds LLM prompts from canonical context JSON.")
    print("\nUsage:")
    print("  from llm_feedback.prompt_builder import build_prompts")
    print("  prompts = build_prompts(context)")
    print("  system_prompt = prompts['system']")
    print("  instruction_prompt = prompts['instruction']")
