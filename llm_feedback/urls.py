"""
LLM Feedback - URL Configuration

Maps URL patterns to views for feedback generation and health checks.
"""

from django.urls import path
from llm_feedback import views

app_name = 'llm_feedback'

urlpatterns = [
    # Generate feedback from context (prompt-engineered)
    path('generate/', views.generate_feedback_view, name='generate'),
    
    # Generate RAW feedback without context (for comparison demo)
    path('raw_generate/', views.raw_feedback_view, name='raw_generate'),
    
    # Compare both and compute metrics
    path('compare/', views.compare_feedback_view, name='compare'),
    
    # Health check for LLM availability
    path('health/', views.llm_health_check, name='health'),
]
