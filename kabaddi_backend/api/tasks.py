import os
import sys
import json
import subprocess
from pathlib import Path
from django.conf import settings
from .models import UserSession, PoseArtifact, AnalyticalResults, LLMFeedback


def process_multi_level_pipeline(session_id: str):
    """
    Execute the complete 4-level analytical pipeline + LLM feedback:
    
    Level-1: Pose Cleaning & Normalization
    Level-2: Temporal Alignment (DTW)
    Level-3: Error Localization (MANDATORY first-class output)
    Level-4: Similarity Scoring
    Step 8-9: LLM Feedback Generation
    
    CRITICAL: This function treats Level-3 as NON-OPTIONAL.
    Both scores.json AND error_metrics.json are REQUIRED outputs.
    """
    try:
        session = UserSession.objects.get(id=session_id)
        
        # =====================================================================
        # STAGE 1: Pose Extraction + Level-1 Cleaning
        # =====================================================================
        session.status = 'pose_extracted'
        session.save()
        
        video_path = session.rawvideo.file_path
        pose_path = settings.MEDIA_ROOT / 'poses' / f'{session_id}.npy'
        
        # Execute pose extraction with Level-1 cleaning
        extract_cmd = [
            sys.executable, 
            str(settings.EXTRACT_POSE_SCRIPT),
            str(video_path), 
            str(pose_path)
        ]
        
        result = subprocess.run(extract_cmd, capture_output=True, text=True, check=True)
        
        # Create PoseArtifact record
        PoseArtifact.objects.create(
            user_session=session,
            pose_level1_path=str(pose_path)
        )
        
        session.status = 'level1_complete'
        session.save()
        
        # =====================================================================
        # STAGE 2-4: Multi-Level Pipeline Execution
        # =====================================================================
        
        # Get expert pose path
        expert_pose_path = settings.MEDIA_ROOT / 'expert_poses' / f'{session.tutorial.name}.npy'
        
        if not expert_pose_path.exists():
            raise FileNotFoundError(f"Expert pose not found: {expert_pose_path}")
        
        # Create results directory
        results_dir = settings.MEDIA_ROOT / 'results' / session_id
        os.makedirs(results_dir, exist_ok=True)
        
        # Execute complete pipeline (Levels 2-4)
        pipeline_cmd = [
            sys.executable, 
            str(settings.RUN_PIPELINE_SCRIPT),
            '--expert-pose', str(expert_pose_path),
            '--user-pose', str(pose_path),
            '--output-dir', str(results_dir),
            '--no-tts',  # Disable TTS for backend
            '--no-viz'   # Disable visualization for backend
        ]
        
        result = subprocess.run(pipeline_cmd, capture_output=True, text=True, check=True)
        
        # =====================================================================
        # VALIDATE MANDATORY OUTPUTS
        # =====================================================================
        
        scores_path = results_dir / 'scores.json'
        error_metrics_path = results_dir / 'error_metrics.json'
        
        # CRITICAL: Both files must exist
        if not scores_path.exists():
            raise FileNotFoundError("Pipeline failed to generate scores.json")
        
        if not error_metrics_path.exists():
            raise FileNotFoundError("Pipeline failed to generate error_metrics.json (Level-3 Error Localization)")
        
        # Validate JSON format
        try:
            with open(scores_path, 'r') as f:
                scores = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid scores.json format: {e}")
        
        try:
            with open(error_metrics_path, 'r') as f:
                error_metrics = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid error_metrics.json format: {e}")
        
        # =====================================================================
        # STORE ANALYTICAL RESULTS
        # =====================================================================
        
        AnalyticalResults.objects.create(
            user_session=session,
            scores_json_path=str(scores_path),
            error_metrics_json_path=str(error_metrics_path)  # MANDATORY Level-3 output
        )
        
        session.status = 'scoring_complete'
        session.save()
        
        # =====================================================================
        # STAGE 3: LLM FEEDBACK GENERATION (STEP 8-9)
        # =====================================================================
        
        # Generate LLM feedback based on error_metrics.json
        try:
            # Simple feedback generation (replace with actual LLM integration)
            feedback_text = f"Based on your {session.tutorial.name} attempt, here are areas for improvement..."
            
            # Store LLM feedback
            LLMFeedback.objects.create(
                user_session=session,
                feedback_text=feedback_text,
                audio_feedback_path=None
            )
            
            session.status = 'feedback_generated'
            session.save()
            
        except Exception as e:
            # Feedback generation is optional - don't fail the entire pipeline
            session.error_message = f"Feedback generation failed: {str(e)}"
            session.save()
        
    except subprocess.CalledProcessError as e:
        session.status = 'failed'
        session.error_message = f"Pipeline execution failed: {e.stderr}"
        session.save()
        raise
        
    except Exception as e:
        session.status = 'failed'
        session.error_message = str(e)
        session.save()
        raise


# For environments without Celery, use simple function call
# In production, replace with: @celery_app.task
class MockTask:
    def delay(self, *args, **kwargs):
        return process_multi_level_pipeline(*args, **kwargs)

process_multi_level_pipeline.delay = MockTask().delay