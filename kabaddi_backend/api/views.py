import os
import json
import uuid
import subprocess
import sys
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views import View
from django.utils.decorators import method_decorator
from .models import Tutorial, UserSession, RawVideo, PoseArtifact, AnalyticalResults


class ARPoseDataView(View):
    def get(self, request, tutorial_id):
        """Serve AR-ready pose data for mobile app ghost playback"""
        try:
            tutorial = Tutorial.objects.get(id=tutorial_id, is_active=True)
        except Tutorial.DoesNotExist:
            return JsonResponse({'error': 'Tutorial not found'}, status=404)
        
        try:
            # Load expert pose data
            expert_pose_path = settings.MEDIA_ROOT / tutorial.expert_pose_path
            
            if not expert_pose_path.exists():
                return JsonResponse({'error': 'Expert pose data not found'}, status=404)
            
            import numpy as np
            poses = np.load(expert_pose_path)  # Shape: (T, 17, 2)
            
            # Convert to AR-ready format
            ar_poses = []
            for frame_idx, pose in enumerate(poses):
                frame_data = {
                    'frame': frame_idx,
                    'timestamp': frame_idx / 30.0,  # Assume 30 FPS
                    'joints': []
                }
                
                # COCO-17 joint names for AR rendering
                joint_names = [
                    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
                    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
                    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
                    'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
                ]
                
                for joint_idx, (x, y) in enumerate(pose):
                    if not np.isnan(x) and not np.isnan(y):
                        frame_data['joints'].append({
                            'name': joint_names[joint_idx],
                            'x': float(x),
                            'y': float(y),
                            'z': 0.0,  # Pseudo-3D: anchored in 3D space
                            'confidence': 1.0
                        })
                
                ar_poses.append(frame_data)
            
            return JsonResponse({
                'tutorial_id': str(tutorial.id),
                'tutorial_name': tutorial.name,
                'total_frames': len(ar_poses),
                'duration': len(ar_poses) / 30.0,
                'fps': 30,
                'pose_format': 'COCO-17',
                'ar_poses': ar_poses
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Failed to load AR pose data: {str(e)}'}, status=500)


class TutorialListView(View):
    def get(self, request):
        tutorials = Tutorial.objects.filter(is_active=True)
        data = [{
            'id': str(tutorial.id),
            'name': tutorial.name,
            'description': tutorial.description
        } for tutorial in tutorials]
        return JsonResponse({'tutorials': data})


@method_decorator(csrf_exempt, name='dispatch')
class SessionStartView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            tutorial_id = data.get('tutorial_id')
            
            if not tutorial_id:
                return JsonResponse({'error': 'tutorial_id required'}, status=400)
            
            try:
                tutorial = Tutorial.objects.get(id=tutorial_id, is_active=True)
            except Tutorial.DoesNotExist:
                return JsonResponse({'error': 'Invalid tutorial_id'}, status=400)
            
            session = UserSession.objects.create(tutorial=tutorial)
            
            return JsonResponse({
                'session_id': str(session.id),
                'tutorial': tutorial.name,
                'status': session.status
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class VideoUploadView(View):
    def post(self, request, session_id):
        try:
            session = UserSession.objects.get(id=session_id)
        except UserSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
        
        if 'video' not in request.FILES:
            return JsonResponse({'error': 'No video file provided'}, status=400)
        
        video_file = request.FILES['video']
        
        # Validate file
        if video_file.size > 100 * 1024 * 1024:  # 100MB limit
            return JsonResponse({'error': 'File too large'}, status=400)
        
        try:
            # Save video
            video_path = settings.MEDIA_ROOT / 'raw_videos' / f'{session_id}.mp4'
            
            with open(video_path, 'wb') as f:
                for chunk in video_file.chunks():
                    f.write(chunk)
            
            # Create RawVideo record
            RawVideo.objects.create(
                user_session=session,
                file_path=str(video_path),
                file_size=video_file.size
            )
            
            # Update session status
            session.status = 'video_uploaded'
            session.save()
            
            return JsonResponse({
                'session_id': str(session.id),
                'status': session.status,
                'file_size': video_file.size
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Upload failed: {str(e)}'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class AssessmentTriggerView(View):
    def post(self, request, session_id):
        try:
            session = UserSession.objects.get(id=session_id)
        except UserSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
        
        if session.status != 'video_uploaded':
            return JsonResponse({'error': f'Invalid status: {session.status}'}, status=400)
        
        # Trigger async pipeline execution
        try:
            from .tasks import process_multi_level_pipeline
            process_multi_level_pipeline.delay(str(session.id))
            
            session.status = 'pose_extracted'
            session.save()
            
            return JsonResponse({
                'session_id': str(session.id),
                'status': 'processing',
                'message': 'Multi-level analytical pipeline started'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Pipeline trigger failed: {str(e)}'}, status=500)


class SessionStatusView(View):
    def get(self, request, session_id):
        try:
            session = UserSession.objects.get(id=session_id)
            
            return JsonResponse({
                'session_id': str(session.id),
                'status': session.status,
                'updated_at': session.updated_at.isoformat(),
                'error_message': session.error_message
            })
            
        except UserSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)


class ResultsView(View):
    def get(self, request, session_id):
        try:
            session = UserSession.objects.get(id=session_id)
            
            if session.status != 'scoring_complete' and session.status != 'feedback_generated':
                return JsonResponse({
                    'error': 'Results not ready',
                    'status': session.status
                }, status=404)
            
            try:
                results = AnalyticalResults.objects.get(user_session=session)
            except AnalyticalResults.DoesNotExist:
                return JsonResponse({'error': 'Results not found'}, status=404)
            
            # Load BOTH mandatory outputs
            try:
                with open(results.scores_json_path, 'r') as f:
                    scores = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return JsonResponse({'error': 'Scores file corrupted'}, status=500)
            
            try:
                with open(results.error_metrics_json_path, 'r') as f:
                    error_metrics = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return JsonResponse({'error': 'Error metrics file corrupted'}, status=500)
            
            response_data = {
                'session_id': str(session.id),
                'tutorial': session.tutorial.name,
                'scores': scores,
                'error_metrics': error_metrics,  # MANDATORY Level-3 output
                'completed_at': results.completed_at.isoformat()
            }
            
            # Add LLM feedback if available
            try:
                from .models import LLMFeedback
                feedback = LLMFeedback.objects.get(user_session=session)
                response_data['feedback'] = {
                    'text': feedback.feedback_text,
                    'audio_path': feedback.audio_feedback_path,
                    'generated_at': feedback.generated_at.isoformat()
                }
            except LLMFeedback.DoesNotExist:
                pass
            
            return JsonResponse(response_data)
            
        except UserSession.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)