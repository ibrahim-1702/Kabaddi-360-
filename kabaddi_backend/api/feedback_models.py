from django.db import models
from .models import UserSession

class LLMFeedback(models.Model):
    """
    Stores AI-generated coaching feedback based on error_metrics.json analysis.
    
    CRITICAL: LLM does NOT analyze video or poses directly.
    LLM reasons over structured numeric error data from Level-3 Error Localization.
    """
    id = models.UUIDField(primary_key=True, default=models.uuid.uuid4)
    user_session = models.OneToOneField(UserSession, on_delete=models.CASCADE)
    
    # Text feedback from LLM
    feedback_text = models.TextField()
    
    # Optional: TTS audio file path
    audio_feedback_path = models.CharField(max_length=255, null=True, blank=True)
    
    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    llm_model_used = models.CharField(max_length=100, default='gpt-4')
    
    def __str__(self):
        return f"Feedback for {self.user_session.tutorial.name}"