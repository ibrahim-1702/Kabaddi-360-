"""
LLM Feedback System

A production-grade LLM inference layer for generating coaching feedback
from canonical context JSON.

Components:
- Context Engine (context_engine.py): Aggregates raw scores into canonical context
- Prompt Builder (prompt_builder.py): Builds LLM prompts from context
- LLM Client (llm_client.py): Calls local LLM via Ollama API
- Views (views.py): Django REST API endpoints

Architecture:
    Pipeline Output → Context Engine → Canonical Context
                                            ↓
    System Prompt + Instruction Prompt ← Prompt Builder
                                            ↓
    LLM API Call → LLM Client → Feedback Text
"""

# Context Engine (TASK 1)
from llm_feedback.context_engine import generate_context, load_raw_scores, save_context

# Prompt Builder (TASK 3)
from llm_feedback.prompt_builder import build_prompts, load_system_prompt, build_instruction_prompt

# LLM Client (TASK 3)
from llm_feedback.llm_client import LLMClient, generate_feedback

# Configuration
from llm_feedback.config import get_all_thresholds, get_llm_config

__version__ = "1.0.0"

__all__ = [
    # Context Engine
    'generate_context',
    'load_raw_scores',
    'save_context',
    
    # Prompt Builder
    'build_prompts',
    'load_system_prompt',
    'build_instruction_prompt',
    
    # LLM Client
    'LLMClient',
    'generate_feedback',
    
    # Configuration
    'get_all_thresholds',
    'get_llm_config',
]
