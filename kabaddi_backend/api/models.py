from django.db import models
import uuid

class Tutorial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=50, unique=True)  # hand_touch, toe_touch, bonus
    description = models.TextField()
    expert_pose_path = models.CharField(max_length=255)  # expert_poses/hand_touch.npy
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserSession(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('video_uploaded', 'Video Uploaded'),
        ('pose_extracted', 'Pose Extracted'),
        ('level1_complete', 'Level-1 Complete'),
        ('level2_complete', 'Level-2 Complete'),
        ('level3_complete', 'Level-3 Complete'),
        ('scoring_complete', 'Scoring Complete'),
        ('feedback_generated', 'Feedback Generated'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tutorial = models.ForeignKey(Tutorial, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.tutorial.name} - {self.status}"

class RawVideo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_session = models.OneToOneField(UserSession, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    checksum = models.CharField(max_length=64, null=True, blank=True)

class PoseArtifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_session = models.OneToOneField(UserSession, on_delete=models.CASCADE)
    pose_level1_path = models.CharField(max_length=255)  # Level-1 cleaned poses
    generated_at = models.DateTimeField(auto_now_add=True)

class AnalyticalResults(models.Model):
    """
    CRITICAL: This model treats Level-3 Error Localization as MANDATORY first-class output.
    Both scores.json AND error_metrics.json are required pipeline outputs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_session = models.OneToOneField(UserSession, on_delete=models.CASCADE)
    
    # MANDATORY: Similarity Scoring (Level-4)
    scores_json_path = models.CharField(max_length=255)
    
    # MANDATORY: Error Localization (Level-3) - NOT OPTIONAL
    error_metrics_json_path = models.CharField(max_length=255)
    
    # Optional: Alignment indices from Level-2
    alignment_indices_path = models.CharField(max_length=255, null=True, blank=True)
    
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Results for {self.user_session.tutorial.name}"

class LLMFeedback(models.Model):
    """
    Stores AI-generated coaching feedback based on error_metrics.json analysis.
    
    CRITICAL: LLM does NOT analyze video or poses directly.
    LLM reasons over structured numeric error data from Level-3 Error Localization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
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