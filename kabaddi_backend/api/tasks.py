import os
import sys
import json
import subprocess
from pathlib import Path
from django.conf import settings
from .models import UserSession, PoseArtifact, AnalyticalResults, LLMFeedback
import imageio_ffmpeg
FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()

# Add project root to sys.path so we can import from frontend and llm_feedback
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.backend.pipeline_runner import run_level2_dtw, run_level3_errors, run_level4_scoring
from llm_feedback.context_engine import generate_context
from llm_feedback.prompt_builder import build_prompts
from llm_feedback.llm_client import generate_feedback


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
        
        video_path = Path(session.rawvideo.file_path)
        
        # ── Slow the user video to 50% to match expert preprocessing ──────────
        slowed_video_path = settings.MEDIA_ROOT / 'raw_videos' / f'{session_id}_slow.mp4'
        ffmpeg_cmd = [
            FFMPEG_BIN, '-y',
            '-i', str(video_path),
            '-filter:v', 'setpts=2.0*PTS',
            '-an',  # drop audio - we only need pose
            str(slowed_video_path)
        ]
        subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
        video_path = slowed_video_path
        # ──────────────────────────────────────────────────────────────────────
        
        pose_path = settings.MEDIA_ROOT / 'poses' / f'{session_id}.npy'
        
        # Execute pose extraction with Level-1 cleaning
        python_exec = settings.PYTHON_EXEC.split() if isinstance(settings.PYTHON_EXEC, str) else [settings.PYTHON_EXEC]
        extract_cmd = [
            *python_exec,
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

        import numpy as np

        # Get expert pose path
        expert_pose_path = settings.MEDIA_ROOT / 'expert_poses' / f'{session.tutorial.name}.npy'

        if not expert_pose_path.exists():
            raise FileNotFoundError(f"Expert pose not found: {expert_pose_path}")

        # Create results directory
        results_dir = settings.MEDIA_ROOT / 'results' / session_id
        os.makedirs(results_dir, exist_ok=True)

        # Load poses
        expert_poses = np.load(str(expert_pose_path))
        user_poses = np.load(str(pose_path))

        # Level-2: DTW alignment
        aligned_expert, aligned_user, T_aligned = run_level2_dtw(expert_poses, user_poses)
        np.save(str(results_dir / 'expert_aligned.npy'), aligned_expert)
        np.save(str(results_dir / 'user_aligned.npy'), aligned_user)

        # Level-3: Error computation
        error_metrics = run_level3_errors(aligned_expert, aligned_user, reference_duration=expert_poses.shape[0])
        error_metrics_path = results_dir / 'error_metrics.json'
        with open(error_metrics_path, 'w') as f:
            json.dump(error_metrics, f, indent=2)

        # Level-4: Scoring
        scores = run_level4_scoring(error_metrics)
        scores_path = results_dir / 'scores.json'
        with open(scores_path, 'w') as f:
            json.dump(scores, f, indent=2)
        
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
        # STAGE 3: LLM FEEDBACK GENERATION
        # =====================================================================
        try:
            # Build results dict that context_engine expects
            results_for_context = {
                'session_id': session_id,
                'pose_id': session.tutorial.name,
                'scores': scores,
                'error_statistics': error_metrics,
                'metadata': {'pipeline_version': 'mobile_v1'}
            }

            context = generate_context(results_for_context)
            prompts = build_prompts(context, technique_name=session.tutorial.name)
            llm_result = generate_feedback(prompts['system'], prompts['instruction'])

            feedback_text = llm_result.get('feedback_text', '') if llm_result['generation_status'] == 'success' else ''

            # TTS: save audio if feedback was generated
            audio_path = None
            if feedback_text:
                try:
                    from tts_engine import TTSEngine
                    tts_dir = settings.MEDIA_ROOT / 'tts_audio'
                    os.makedirs(tts_dir, exist_ok=True)
                    audio_path = str(tts_dir / f'{session_id}.wav')
                    print(f"[TTS] Saving audio to: {audio_path}")
                    tts = TTSEngine()
                    success = tts.save_to_file(feedback_text, audio_path)
                    print(f"[TTS] save_to_file returned: {success}")
                    print(f"[TTS] File exists after save: {os.path.exists(audio_path)}")
                    if not success or not os.path.exists(audio_path):
                        print(f"[TTS] ERROR: Audio file not created at {audio_path}")
                        audio_path = None
                except Exception as tts_err:
                    print(f"[TTS] Exception during TTS: {tts_err}")
                    audio_path = None

            LLMFeedback.objects.create(
                user_session=session,
                feedback_text=feedback_text,
                audio_feedback_path=audio_path
            )

            session.status = 'feedback_generated'
            session.save()

        except Exception as e:
            # Feedback is optional - don't fail the pipeline
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