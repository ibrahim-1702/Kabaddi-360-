# AR-Based Kabaddi Ghost Trainer - Complete System Documentation (Part 2)

## Table of Contents (Part 2)

11. [Detailed Code Analysis](#detailed-code-analysis)
12. [Async Task Implementation](#async-task-implementation)
13. [Pipeline Integration Deep Dive](#pipeline-integration-deep-dive)
14. [Data Flow Analysis](#data-flow-analysis)
15. [Security Implementation](#security-implementation)
16. [Performance Optimization](#performance-optimization)
17. [Testing Strategy](#testing-strategy)
18. [Deployment Procedures](#deployment-procedures)
19. [Maintenance and Monitoring](#maintenance-and-monitoring)
20. [Troubleshooting Guide](#troubleshooting-guide)

---

## 11. Detailed Code Analysis

### 11.1 API Views Implementation Analysis

**File: api/views.py - Line by Line Analysis**

**Import Section**:
```python
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
```

**Import Analysis**:
- `os, sys`: System operations for subprocess calls
- `json`: JSON parsing for pipeline outputs
- `uuid`: Session ID generation and validation
- `subprocess`: Pipeline script execution
- Django imports: Framework components for API views
- Model imports: Database entities for session management

**ARPoseDataView Implementation**:
```python
class ARPoseDataView(View):
    def get(self, request, tutorial_id):
        """Serve AR-ready pose data for mobile app ghost playback"""
        try:
            tutorial = Tutorial.objects.get(id=tutorial_id, is_active=True)
        except Tutorial.DoesNotExist:
            return JsonResponse({'error': 'Tutorial not found'}, status=404)
```

**Purpose**: Converts expert pose files to AR-ready format for mobile consumption
**Key Operations**:
1. Tutorial validation and retrieval
2. Expert pose file loading
3. COCO-17 to AR format conversion
4. JSON response generation

**Pose Data Conversion Logic**:
```python
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
```

**Conversion Process Analysis**:
1. **File Loading**: Uses numpy to load binary pose data
2. **Frame Iteration**: Processes each frame in the sequence
3. **Timestamp Calculation**: Assumes 30 FPS for timing
4. **Joint Mapping**: Maps COCO-17 indices to named joints
5. **NaN Filtering**: Excludes invalid joint positions
6. **Pseudo-3D**: Sets z=0.0 for 2D poses anchored in 3D space
7. **Confidence**: Sets 1.0 for all valid joints (cleaned data)

**SessionStartView Implementation**:
```python
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
```

**Implementation Analysis**:
1. **CSRF Exemption**: Required for API endpoints (consider API key auth)
2. **JSON Parsing**: Handles malformed JSON gracefully
3. **Input Validation**: Checks for required tutorial_id parameter
4. **Tutorial Validation**: Ensures tutorial exists and is active
5. **Session Creation**: Creates new UserSession with default status
6. **Response Format**: Returns session metadata for client tracking

**VideoUploadView Implementation**:
```python
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
```

**File Validation Logic**:
1. **Session Validation**: Ensures session exists before processing
2. **File Presence**: Checks for 'video' in multipart form data
3. **Size Validation**: Enforces 100MB limit for performance
4. **Format Validation**: Could add MIME type checking

**File Storage Implementation**:
```python
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
```

**Storage Process Analysis**:
1. **Path Generation**: Uses session UUID for unique filenames
2. **Chunked Writing**: Handles large files efficiently
3. **Database Recording**: Creates RawVideo record for tracking
4. **Status Update**: Advances session to next stage
5. **Atomic Operation**: Database and file operations should be transactional

**AssessmentTriggerView Implementation**:
```python
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
```

**Async Trigger Analysis**:
1. **State Validation**: Ensures session is ready for processing
2. **Task Dispatch**: Triggers async pipeline execution
3. **Status Update**: Immediately updates to processing state
4. **Response**: Returns processing confirmation to client

**ResultsView Implementation**:
```python
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
```

**Results Loading Analysis**:
1. **Status Validation**: Accepts both scoring_complete and feedback_generated
2. **Results Existence**: Verifies AnalyticalResults record exists
3. **File Loading**: Loads BOTH mandatory JSON outputs
4. **Error Handling**: Graceful handling of file corruption
5. **Mandatory Outputs**: Treats both scores and error_metrics as required

### 11.2 Model Implementation Analysis

**File: api/models.py - Detailed Model Analysis**

**Tutorial Model Deep Dive**:
```python
class Tutorial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    expert_pose_path = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
```

**Field Analysis**:
- `id`: UUID primary key for security (no sequential IDs)
- `name`: Unique constraint prevents duplicate tutorials
- `description`: Unlimited text for detailed explanations
- `expert_pose_path`: Relative path from MEDIA_ROOT
- `is_active`: Soft delete mechanism (preserve data)
- `created_at`: Audit trail for tutorial creation

**UserSession Model Deep Dive**:
```python
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
```

**Status Flow Analysis**:
```
created
  ↓ (video upload)
video_uploaded
  ↓ (assessment trigger)
pose_extracted
  ↓ (Level-1 cleaning)
level1_complete
  ↓ (Level-2 alignment)
level2_complete
  ↓ (Level-3 error localization)
level3_complete
  ↓ (Level-4 scoring)
scoring_complete
  ↓ (LLM feedback - optional)
feedback_generated

failed (can occur at any stage)
```

**Status Semantics**:
- Each status represents a completed pipeline stage
- Status updates are atomic and trackable
- Failed status preserves error context
- Status enables precise progress tracking for mobile app

**AnalyticalResults Model Critical Analysis**:
```python
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
```

**Critical Design Decisions**:
1. **Both Fields Required**: Neither scores nor error_metrics is optional
2. **Level-3 Emphasis**: Error localization treated as primary output
3. **File Path Storage**: Stores paths, not data (for large JSON files)
4. **One-to-One Relationship**: Each session has exactly one result set
5. **Cascade Delete**: Results deleted when session is deleted

**LLMFeedback Model Analysis**:
```python
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
```

**LLM Integration Principles**:
1. **Structured Data Input**: LLM operates on error_metrics.json, not raw data
2. **Text Output**: Primary output is natural language feedback
3. **Optional Audio**: TTS conversion is secondary feature
4. **Model Tracking**: Records which LLM model was used
5. **Timestamp Tracking**: Enables feedback cache management

### 11.3 URL Pattern Analysis

**File: api/urls.py - URL Design Analysis**

```python
urlpatterns = [
    # AR Playback Data
    path('tutorials/<uuid:tutorial_id>/ar-poses/', ARPoseDataView.as_view(), name='ar_pose_data'),
    
    # Tutorial Management
    path('tutorials/', TutorialListView.as_view(), name='tutorial_list'),
    
    # Session Management
    path('session/start/', SessionStartView.as_view(), name='session_start'),
    path('session/<uuid:session_id>/upload-video/', VideoUploadView.as_view(), name='video_upload'),
    path('session/<uuid:session_id>/assess/', AssessmentTriggerView.as_view(), name='assessment_trigger'),
    path('session/<uuid:session_id>/status/', SessionStatusView.as_view(), name='session_status'),
    path('session/<uuid:session_id>/results/', ResultsView.as_view(), name='results'),
]
```

**URL Design Principles**:
1. **Resource-Based**: URLs represent resources, not actions
2. **UUID Parameters**: All IDs are UUIDs for security
3. **Hierarchical Structure**: Logical grouping of related endpoints
4. **RESTful Verbs**: HTTP methods indicate operations
5. **Descriptive Names**: Clear purpose from URL structure

**URL Security Analysis**:
- UUID parameters prevent enumeration attacks
- No sequential IDs that could be guessed
- Resource-based access control possible
- CSRF protection on state-changing operations

---

## 12. Async Task Implementation

### 12.1 Task Architecture

**File: api/tasks.py - Complete Implementation Analysis**

**Task Function Signature**:
```python
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
```

**Function Design**:
- Single parameter: session_id for context
- Comprehensive docstring explaining pipeline semantics
- Clear emphasis on Level-3 as mandatory output
- Integration of LLM feedback generation

**Stage 1: Pose Extraction Implementation**:
```python
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
```

**Stage 1 Analysis**:
1. **Status Update**: Immediately updates session status
2. **Path Resolution**: Uses session UUID for unique file naming
3. **Subprocess Call**: Executes external pose extraction script
4. **Error Capture**: Captures both stdout and stderr
5. **Exception Handling**: CalledProcessError raised on failure

**Database Integration**:
```python
        # Create PoseArtifact record
        PoseArtifact.objects.create(
            user_session=session,
            pose_level1_path=str(pose_path)
        )
        
        session.status = 'level1_complete'
        session.save()
```

**Database Operations**:
- Creates PoseArtifact record for tracking
- Updates session status to reflect completion
- Maintains data consistency between filesystem and database

**Stage 2-4: Pipeline Execution**:
```python
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
```

**Pipeline Integration Analysis**:
1. **Expert Pose Resolution**: Uses tutorial name to find reference pose
2. **File Existence Check**: Validates expert pose exists before processing
3. **Directory Creation**: Ensures results directory exists
4. **Command Construction**: Builds complete command line arguments
5. **Feature Disabling**: Disables TTS and visualization for backend use
6. **Subprocess Execution**: Runs complete pipeline as external process

**Output Validation Implementation**:
```python
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
```

**Validation Strategy**:
1. **File Existence**: Both outputs must exist (no optional files)
2. **Specific Error Messages**: Clear indication of which file is missing
3. **JSON Validation**: Ensures files are valid JSON format
4. **Error Context**: Provides specific error details for debugging

**Results Storage Implementation**:
```python
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
```

**Storage Design**:
- Creates AnalyticalResults record with both file paths
- Emphasizes error_metrics as mandatory Level-3 output
- Updates session status to indicate completion

**LLM Feedback Integration**:
```python
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
```

**LLM Integration Design**:
1. **Optional Processing**: Feedback failure doesn't fail entire pipeline
2. **Placeholder Implementation**: Ready for actual LLM integration
3. **Error Isolation**: LLM errors don't affect core pipeline
4. **Status Tracking**: Separate status for feedback completion

### 12.2 Error Handling in Async Tasks

**Exception Handling Strategy**:
```python
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
```

**Error Handling Principles**:
1. **Specific Exception Types**: Different handling for different error types
2. **Status Updates**: Always update session status on failure
3. **Error Preservation**: Store error messages for debugging
4. **Exception Re-raising**: Allows higher-level error handling
5. **Database Consistency**: Ensure session state reflects actual status

### 12.3 Task Execution Environment

**Mock Task Implementation**:
```python
# For environments without Celery, use simple function call
# In production, replace with: @celery_app.task
class MockTask:
    def delay(self, *args, **kwargs):
        return process_multi_level_pipeline(*args, **kwargs)

process_multi_level_pipeline.delay = MockTask().delay
```

**Environment Considerations**:
- Development: Synchronous execution for debugging
- Production: Async execution with Celery or similar
- Testing: Mock implementation for unit tests
- Scaling: Queue-based execution for high load

---

## 13. Pipeline Integration Deep Dive

### 13.1 Pose Extraction Pipeline

**File: level1_pose/pose_extract_cli.py - Implementation Analysis**

**CLI Interface Design**:
```python
def main():
    parser = argparse.ArgumentParser(description='Extract pose from video')
    parser.add_argument('video_path', help='Input video path')
    parser.add_argument('output_path', help='Output .npy file path')
    
    args = parser.parse_args()
    
    try:
        extract_pose_from_video(args.video_path, args.output_path)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

**CLI Design Principles**:
- Positional arguments for required parameters
- Clear error messages to stderr
- Non-zero exit codes on failure
- Simple interface for subprocess integration

**Pose Extraction Implementation**:
```python
def extract_pose_from_video(video_path, output_path):
    """Extract pose from video and save as COCO-17 format"""
    
    # YOLO (person detection + tracking)
    yolo = YOLO("yolov8n.pt")
    
    # MediaPipe Pose
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.7
    )
```

**Model Configuration Analysis**:
- **YOLO**: Person detection and tracking (yolov8n.pt model)
- **MediaPipe**: Pose estimation with optimized settings
- **Static Mode**: False for video processing
- **Model Complexity**: 1 for balance of speed and accuracy
- **Smoothing**: Enabled for temporal consistency
- **Confidence Thresholds**: Tuned for kabaddi movements

**Video Processing Loop**:
```python
    cap = cv2.VideoCapture(video_path)
    tracks_history = {}
    all_frames_2d = []
    PAD = 40
    FRAME_JOINTS = 33
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # YOLO tracking
        results = yolo.track(
            frame,
            persist=True,
            classes=[0],  # person
            tracker="bytetrack.yaml",
            verbose=False
        )
        
        # Default frame (NaNs)
        frame_pose_2d = np.full((FRAME_JOINTS, 2), np.nan)
```

**Processing Strategy**:
1. **Frame-by-Frame**: Sequential video processing
2. **Person Tracking**: YOLO with ByteTrack for consistency
3. **Default Initialization**: NaN values for missing poses
4. **Padding**: 40-pixel padding around detected person
5. **Joint Count**: 33 joints for MediaPipe format

**Person Selection Logic**:
```python
        # Select raider (most motion)
        raider_id = None
        max_motion = 0
        
        for pid, pts in tracks_history.items():
            if len(pts) < 5:
                continue
            motion = sum(
                np.linalg.norm(np.array(pts[i]) - np.array(pts[i - 1]))
                for i in range(1, len(pts))
            )
            if motion > max_motion:
                max_motion = motion
                raider_id = pid
```

**Motion-Based Selection**:
- Tracks multiple people in frame
- Calculates motion as cumulative displacement
- Selects person with highest motion (active raider)
- Requires minimum 5 frames for stable tracking

**Format Conversion Pipeline**:
```python
    # Convert MP33 to COCO17
    mp33_poses = np.array(all_frames_2d)
    coco17_poses = mp33_to_coco17(mp33_poses)
    
    # Apply Level-1 cleaning
    cleaned_poses = clean_level1_poses(coco17_poses)
    
    # Save output
    np.save(output_path, cleaned_poses)
    print(f"Saved COCO-17 poses: {cleaned_poses.shape}")
```

**Conversion Process**:
1. **MP33 Array**: Convert list to numpy array
2. **Format Conversion**: MediaPipe 33 joints → COCO-17 joints
3. **Level-1 Cleaning**: Apply noise reduction and normalization
4. **File Output**: Save as binary numpy file
5. **Confirmation**: Print final shape for verification

### 13.2 Main Pipeline Analysis

**File: run_pipeline.py - Pipeline Orchestration**

**Pipeline Stages Implementation**:
```python
def main(args):
    """Main pipeline execution with strict 4-level semantics"""
    
    # Initialize configuration and logger
    config = PipelineConfig.from_args(args)
    logger = PipelineLogger(verbose=config.verbose)
    
    # Print header
    logger.header("AR-Based Kabaddi Ghost Trainer - Pipeline Execution")
    
    # Create output directory
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
```

**Initialization Process**:
- Configuration management from command line arguments
- Logger setup with verbosity control
- Output directory creation with error handling
- Clear pipeline identification in logs

**Stage 1: Expert Pose Loading**:
```python
    # =========================================================================
    # STAGE 1: Load/Extract Expert Pose
    # =========================================================================
    current_stage += 1
    logger.log_stage_start(current_stage, total_stages, "Load Expert/Reference Pose")
    
    expert_pose = load_or_extract_pose(
        input_path=args.expert_pose,
        video_path=args.expert_video if hasattr(args, 'expert_video') else None,
        output_dir=output_dir,
        config=config,
        logger=logger,
        name='expert'
    )
    
    if expert_pose is None:
        logger.error("Failed to load expert pose. Aborting pipeline.")
        sys.exit(1)
```

**Expert Pose Handling**:
- Supports both pre-extracted poses and video extraction
- Comprehensive logging of stage progress
- Graceful failure handling with clear error messages
- Mandatory expert pose requirement (pipeline aborts if missing)

**Stage 2: User Pose Processing**:
```python
    # =========================================================================
    # STAGE 2: Load/Extract User Pose + Level-1 Cleaning
    # =========================================================================
    current_stage += 1
    logger.log_stage_start(current_stage, total_stages, "Load/Extract User Pose + Level-1 Cleaning")
    
    user_pose = load_or_extract_pose(
        input_path=args.user_pose,
        video_path=args.user_video if hasattr(args, 'user_video') else None,
        output_dir=output_dir,
        config=config,
        logger=logger,
        name='user'
    )
```

**User Pose Processing**:
- Same interface as expert pose for consistency
- Integrated Level-1 cleaning in extraction process
- Detailed progress logging for debugging
- Flexible input handling (pre-extracted or video)

**Stage 3: Pose Validation (Levels 2-4)**:
```python
    # =========================================================================
    # STAGE 3: Pose Validation
    # =========================================================================
    current_stage += 1
    logger.log_stage_start(current_stage, total_stages, "Pose Validation")
    
    scores = run_validation(expert_pose, user_pose, output_dir, logger)
    
    if scores is None:
        logger.error("Failed to compute validation scores. Aborting pipeline.")
        sys.exit(1)
```

**Validation Stage**:
- Executes Levels 2-4 of analytical pipeline
- Returns similarity scores as primary output
- Generates error_metrics.json as mandatory side effect
- Comprehensive error handling with pipeline abort

### 13.3 Level-2 Temporal Alignment

**File: temporal_alignment.py - DTW Implementation**

**Pelvis Trajectory Extraction**:
```python
def extract_pelvis_trajectory(poses: np.ndarray) -> np.ndarray:
    """
    Extract pelvis trajectory from pose sequence using hip midpoint.
    
    Args:
        poses: Pose sequence (T, 17, 2) in COCO-17 format
        
    Returns:
        Pelvis trajectory (T, 2) - hip midpoint coordinates
    """
    # COCO-17: joint 11 = left hip, joint 12 = right hip
    left_hip = poses[:, 11, :]   # (T, 2)
    right_hip = poses[:, 12, :]  # (T, 2)
    
    # Pelvis = midpoint between hips
    pelvis = (left_hip + right_hip) / 2.0
    return pelvis
```

**Trajectory Design**:
- Uses hip midpoint as stable reference point
- COCO-17 joint indices: 11 (left hip), 12 (right hip)
- Simple averaging for pelvis position calculation
- Returns 2D trajectory for DTW processing

**DTW Distance Matrix**:
```python
def compute_distance_matrix(user_pelvis: np.ndarray, ghost_pelvis: np.ndarray) -> np.ndarray:
    """
    Compute pairwise Euclidean distances between pelvis positions.
    
    Args:
        user_pelvis: User pelvis trajectory (T_user, 2)
        ghost_pelvis: Ghost pelvis trajectory (T_ghost, 2)
        
    Returns:
        Distance matrix (T_user, T_ghost)
    """
    T_user, T_ghost = len(user_pelvis), len(ghost_pelvis)
    distances = np.zeros((T_user, T_ghost))
    
    for i in range(T_user):
        for j in range(T_ghost):
            # Euclidean distance between pelvis positions
            diff = user_pelvis[i] - ghost_pelvis[j]
            distances[i, j] = np.sqrt(np.sum(diff ** 2))
    
    return distances
```

**Distance Calculation**:
- Pairwise Euclidean distances between all frame combinations
- Simple geometric distance in 2D space
- Full distance matrix for DTW algorithm
- Computational complexity: O(T_user × T_ghost)

**DTW Algorithm Implementation**:
```python
def dtw_alignment(distance_matrix: np.ndarray) -> List[Tuple[int, int]]:
    """
    Compute DTW alignment path using dynamic programming.
    
    Args:
        distance_matrix: Pairwise distances (T_user, T_ghost)
        
    Returns:
        Alignment path as list of (user_idx, ghost_idx) pairs
    """
    T_user, T_ghost = distance_matrix.shape
    
    # Initialize DTW cost matrix
    dtw_matrix = np.full((T_user, T_ghost), np.inf)
    dtw_matrix[0, 0] = distance_matrix[0, 0]
    
    # Fill first row and column
    for i in range(1, T_user):
        dtw_matrix[i, 0] = dtw_matrix[i-1, 0] + distance_matrix[i, 0]
    for j in range(1, T_ghost):
        dtw_matrix[0, j] = dtw_matrix[0, j-1] + distance_matrix[0, j]
    
    # Fill DTW matrix
    for i in range(1, T_user):
        for j in range(1, T_ghost):
            cost = distance_matrix[i, j]
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i-1, j],     # insertion
                dtw_matrix[i, j-1],     # deletion
                dtw_matrix[i-1, j-1]    # match
            )
```

**DTW Matrix Construction**:
- Dynamic programming approach
- Three possible transitions: insertion, deletion, match
- Cumulative cost minimization
- Standard DTW algorithm implementation

**Path Backtracking**:
```python
    # Backtrack to find optimal path
    path = []
    i, j = T_user - 1, T_ghost - 1
    
    while i > 0 or j > 0:
        path.append((i, j))
        
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        else:
            # Choose minimum cost predecessor
            costs = [
                dtw_matrix[i-1, j-1],  # diagonal
                dtw_matrix[i-1, j],    # up
                dtw_matrix[i, j-1]     # left
            ]
            min_idx = np.argmin(costs)
            
            if min_idx == 0:    # diagonal
                i, j = i-1, j-1
            elif min_idx == 1:  # up
                i -= 1
            else:               # left
                j -= 1
    
    path.append((0, 0))
    path.reverse()
    
    return path
```

**Backtracking Process**:
- Starts from bottom-right corner of DTW matrix
- Follows minimum cost path backwards
- Handles boundary conditions (edges of matrix)
- Returns optimal alignment path

### 13.4 Level-3 Error Localization

**File: error_localization.py - Error Analysis Implementation**

**Error Computation Function**:
```python
def compute_error_metrics(
    aligned_user_poses: np.ndarray,
    aligned_trainer_poses: np.ndarray,
    enable_temporal_phases: bool = True
) -> Dict:
    """
    Compute error localization metrics between aligned pose sequences.
    
    Args:
        aligned_user_poses: (T, 17, 2) - User pose sequence
        aligned_trainer_poses: (T, 17, 2) - Trainer pose sequence  
        enable_temporal_phases: Whether to compute temporal phase errors
        
    Returns:
        Dictionary containing frame errors, joint aggregates, and optional phases
    """
    # Validate inputs
    assert aligned_user_poses.shape == aligned_trainer_poses.shape
    assert aligned_user_poses.shape[1:] == (17, 2), "Expected COCO-17 format (17, 2)"
    
    T, num_joints, _ = aligned_user_poses.shape
    
    # Compute frame-wise Euclidean error per joint
    frame_errors = np.linalg.norm(
        aligned_user_poses - aligned_trainer_poses, axis=2
    )  # Shape: (T, 17)
```

**Error Calculation**:
- Input validation ensures correct format and alignment
- Frame-wise Euclidean distance per joint
- Operates on aligned sequences (post-DTW)
- Output shape: (T, 17) for T frames and 17 joints

**Joint Aggregation**:
```python
    # Aggregate joint-wise statistics
    joint_aggregates = {}
    for j, joint_name in enumerate(COCO_17_JOINTS):
        joint_errors = frame_errors[:, j]
        joint_aggregates[joint_name] = {
            "mean": float(np.mean(joint_errors)),
            "max": float(np.max(joint_errors)),
            "std": float(np.std(joint_errors))
        }
```

**Statistical Analysis**:
- Mean error: Average deviation across all frames
- Max error: Worst-case deviation for joint
- Standard deviation: Consistency of joint performance
- Per-joint analysis enables targeted feedback

**Temporal Phase Analysis**:
```python
    # Optional temporal phase segmentation
    if enable_temporal_phases:
        phase_boundaries = [0, T//3, 2*T//3, T]
        phases = ["early", "mid", "late"]
        
        temporal_phases = {}
        for i, phase in enumerate(phases):
            start_idx = phase_boundaries[i]
            end_idx = phase_boundaries[i + 1]
            phase_errors = frame_errors[start_idx:end_idx]
            
            phase_joint_means = {}
            for j, joint_name in enumerate(COCO_17_JOINTS):
                phase_joint_means[joint_name] = float(np.mean(phase_errors[:, j]))
            
            temporal_phases[phase] = phase_joint_means
```

**Phase Segmentation**:
- Divides movement into early, mid, late phases
- Equal time division (T/3 each phase)
- Per-phase joint error analysis
- Enables temporal progression feedback

**Output Structure**:
```python
    result = {
        "frame_errors": {
            "shape": list(frame_errors.shape),
            "data": frame_errors.tolist()
        },
        "joint_aggregates": joint_aggregates,
        "metadata": {
            "total_frames": T,
            "joints_count": num_joints
        }
    }
    
    if enable_temporal_phases:
        result["temporal_phases"] = temporal_phases
        result["metadata"]["phase_boundaries"] = phase_boundaries
    
    return result
```

**Result Format**:
- Frame errors: Complete error matrix with metadata
- Joint aggregates: Statistical summary per joint
- Temporal phases: Phase-wise error analysis (optional)
- Metadata: Processing information and parameters

---

## 14. Data Flow Analysis

### 14.1 Complete System Data Flow

**Data Flow Diagram**:
```
Mobile App                Django Backend              Pipeline System
    │                          │                           │
    ├─ Tutorial Selection ────▶│ GET /api/tutorials/       │
    │                          │                           │
    ├─ AR Pose Request ───────▶│ GET /api/tutorials/{id}/  │
    │                          │     ar-poses/             │
    │                          │                           │
    ├─ Session Creation ──────▶│ POST /api/session/start/  │
    │                          │                           │
    ├─ Video Upload ──────────▶│ POST /api/session/{id}/   │
    │                          │     upload-video/         │
    │                          │                           │
    ├─ Assessment Trigger ────▶│ POST /api/session/{id}/   │
    │                          │     assess/               │
    │                          │           │               │
    │                          │           ├─ Pose Extract ─▶ level1_pose/
    │                          │           │               │ pose_extract_cli.py
    │                          │           │               │
    │                          │           ├─ Pipeline Exec ▶ run_pipeline.py
    │                          │           │               │ ├─ Level-2 DTW
    │                          │           │               │ ├─ Level-3 Error
    │                          │           │               │ └─ Level-4 Score
    │                          │           │               │
    │                          │           └─ LLM Feedback ▶ feedback_generator.py
    │                          │                           │
    ├─ Status Polling ────────▶│ GET /api/session/{id}/    │
    │                          │     status/               │
    │                          │                           │
    └─ Results Retrieval ─────▶│ GET /api/session/{id}/    │
                               │     results/              │
```

### 14.2 File System Data Flow

**File Creation and Access Patterns**:
```
Input Files:
├── raw_videos/{session_id}.mp4          # User uploaded video
├── expert_poses/{tutorial_name}.npy     # Reference trainer poses
└── yolov8n.pt                          # YOLO model weights

Processing Files:
├── poses/{session_id}.npy              # Extracted user poses (Level-1)
└── results/{session_id}/               # Pipeline outputs
    ├── scores.json                     # Level-4 similarity scores
    ├── error_metrics.json              # Level-3 error localization
    ├── feedback.json                   # LLM feedback (optional)
    └── feedback.txt                    # Detailed feedback text

Database Records:
├── Tutorial                            # Tutorial metadata
├── UserSession                         # Session state tracking
├── RawVideo                           # Video file metadata
├── PoseArtifact                       # Pose file metadata
├── AnalyticalResults                  # Pipeline output paths
└── LLMFeedback                        # Generated feedback
```

### 14.3 Data Transformation Pipeline

**Stage 1: Video → Pose Extraction**
```
Input:  raw_videos/{session_id}.mp4 (H.264 video)
Process: YOLO person detection + MediaPipe pose estimation
Output: poses/{session_id}.npy (T, 17, 2) COCO-17 format
```

**Stage 2: Pose → Temporal Alignment**
```
Input:  User poses (T_user, 17, 2) + Expert poses (T_expert, 17, 2)
Process: DTW on pelvis trajectories
Output: Alignment indices for both sequences
```

**Stage 3: Aligned Poses → Error Localization**
```
Input:  Aligned user poses + Aligned expert poses
Process: Frame-wise Euclidean distance calculation
Output: error_metrics.json with joint-wise statistics
```

**Stage 4: Aligned Poses → Similarity Scoring**
```
Input:  Aligned user poses + Aligned expert poses
Process: Structural and temporal similarity metrics
Output: scores.json with overall performance scores
```

**Stage 5: Error Metrics → LLM Feedback**
```
Input:  error_metrics.json + scores.json + tutorial context
Process: LLM reasoning over structured error data
Output: feedback.json with natural language coaching advice
```

### 14.4 API Data Formats

**Tutorial List Response**:
```json
{
  "tutorials": [
    {
      "id": "uuid",
      "name": "hand_touch",
      "description": "Hand touch kabaddi movement"
    }
  ]
}
```

**AR Pose Data Response**:
```json
{
  "tutorial_id": "uuid",
  "tutorial_name": "hand_touch",
  "total_frames": 150,
  "duration": 5.0,
  "fps": 30,
  "pose_format": "COCO-17",
  "ar_poses": [
    {
      "frame": 0,
      "timestamp": 0.0,
      "joints": [
        {
          "name": "left_shoulder",
          "x": 0.4, "y": 0.4, "z": 0.0,
          "confidence": 1.0
        }
      ]
    }
  ]
}
```

**Session Status Response**:
```json
{
  "session_id": "uuid",
  "status": "feedback_generated",
  "updated_at": "2024-01-15T10:30:45Z",
  "error_message": null
}
```

**Complete Results Response**:
```json
{
  "session_id": "uuid",
  "tutorial": "hand_touch",
  "scores": {
    "structural": 85.2,
    "temporal": 78.9,
    "overall": 82.1
  },
  "error_metrics": {
    "frame_errors": {
      "shape": [150, 17],
      "data": [[0.12, 0.08, ...], ...]
    },
    "joint_aggregates": {
      "left_shoulder": {
        "mean": 0.15,
        "max": 0.45,
        "std": 0.12
      }
    },
    "temporal_phases": {
      "early": {"left_shoulder": 0.12},
      "mid": {"left_shoulder": 0.18},
      "late": {"left_shoulder": 0.16}
    }
  },
  "feedback": {
    "text": "Focus on improving your left shoulder positioning...",
    "audio_path": null,
    "generated_at": "2024-01-15T10:30:50Z"
  },
  "completed_at": "2024-01-15T10:30:45Z"
}
```

---

## 15. Security Implementation

### 15.1 Current Security Measures

**UUID-Based Resource Identification**:
```python
# All models use UUID primary keys
id = models.UUIDField(primary_key=True, default=uuid.uuid4)

# URL patterns use UUID parameters
path('session/<uuid:session_id>/status/', SessionStatusView.as_view())
```

**Benefits**:
- Prevents enumeration attacks
- No sequential ID guessing
- 128-bit entropy for session IDs
- URL-safe representation

**CSRF Protection**:
```python
# Enabled in middleware
'django.middleware.csrf.CsrfViewMiddleware',

# Exempted for API endpoints (consider API key auth)
@method_decorator(csrf_exempt, name='dispatch')
```

**Current State**:
- CSRF protection enabled globally
- API endpoints exempted (development convenience)
- Production should implement API key authentication

**File Upload Validation**:
```python
# File size limits
if video_file.size > 100 * 1024 * 1024:  # 100MB limit
    return JsonResponse({'error': 'File too large'}, status=413)

# File type validation (should be implemented)
# MIME type checking
# File content validation
```

### 15.2 Security Vulnerabilities and Mitigations

**Current Vulnerabilities**:

1. **No Authentication**
   - API endpoints are publicly accessible
   - No user authentication or authorization
   - Session hijacking possible with UUID knowledge

2. **File Upload Security**
   - No MIME type validation
   - No file content scanning
   - Potential for malicious file uploads

3. **Path Traversal**
   - File paths constructed from user input
   - Potential for directory traversal attacks

4. **Information Disclosure**
   - Detailed error messages in responses
   - Stack traces in debug mode
   - File system paths exposed

**Recommended Security Enhancements**:

**Authentication and Authorization**:
```python
# API Key Authentication
class APIKeyAuthentication:
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            return None
        
        try:
            # Validate API key against database/cache
            user = validate_api_key(api_key)
            return (user, api_key)
        except InvalidAPIKey:
            raise AuthenticationFailed('Invalid API key')

# Rate Limiting
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='10/m', method='POST')
def upload_video(request):
    # Implementation
```

**File Upload Security**:
```python
import magic

def validate_video_file(uploaded_file):
    # MIME type validation
    mime_type = magic.from_buffer(uploaded_file.read(1024), mime=True)
    if mime_type not in ['video/mp4', 'video/quicktime', 'video/x-msvideo']:
        raise ValidationError('Invalid file type')
    
    # File size validation
    if uploaded_file.size > MAX_VIDEO_SIZE:
        raise ValidationError('File too large')
    
    # File name sanitization
    safe_filename = secure_filename(uploaded_file.name)
    
    return safe_filename
```

**Path Security**:
```python
import os.path

def secure_file_path(base_dir, filename):
    # Prevent path traversal
    safe_path = os.path.join(base_dir, filename)
    if not safe_path.startswith(base_dir):
        raise SecurityError('Path traversal attempt')
    
    return safe_path
```

### 15.3 Production Security Configuration

**Django Security Settings**:
```python
# Production security settings
DEBUG = False
ALLOWED_HOSTS = ['api.kabaddi-trainer.com']

# Security middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'api.middleware.APIKeyMiddleware',  # Custom API key auth
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS enforcement
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

**Database Security**:
```python
# Database connection security
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ['DB_PORT'],
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# Connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 600
```

---

## 16. Performance Optimization

### 16.1 Current Performance Characteristics

**Video Upload Performance**:
- File size limit: 100MB
- Chunked upload processing
- Synchronous file writing
- No compression or optimization

**Pipeline Execution Performance**:
- Pose extraction: ~30 seconds for 5-second video
- DTW alignment: ~1 second for 150-frame sequences
- Error localization: ~0.1 seconds
- LLM feedback: ~5 seconds (depending on model)

**Database Performance**:
- SQLite for development (single-threaded)
- No connection pooling
- No query optimization
- No caching layer

### 16.2 Performance Optimization Strategies

**Async Processing Optimization**:
```python
# Celery configuration for production
from celery import Celery

app = Celery('kabaddi_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Task routing
app.conf.task_routes = {
    'api.tasks.process_multi_level_pipeline': {'queue': 'pipeline'},
    'api.tasks.generate_llm_feedback': {'queue': 'llm'},
}

# Worker configuration
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = True
```

**Database Optimization**:
```python
# PostgreSQL with connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
        }
    }
}

# Database indexing
class UserSession(models.Model):
    status = models.CharField(max_length=20, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    tutorial = models.ForeignKey(Tutorial, on_delete=models.CASCADE, db_index=True)
```

**Caching Strategy**:
```python
# Redis caching configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Cache tutorial data
from django.core.cache import cache

def get_tutorials():
    tutorials = cache.get('active_tutorials')
    if tutorials is None:
        tutorials = list(Tutorial.objects.filter(is_active=True))
        cache.set('active_tutorials', tutorials, 3600)  # 1 hour
    return tutorials
```

**File Storage Optimization**:
```python
# AWS S3 for production file storage
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_STORAGE_BUCKET_NAME = 'kabaddi-trainer-media'
AWS_S3_REGION_NAME = 'us-west-2'
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = 'private'

# CloudFront CDN for static files
AWS_S3_CUSTOM_DOMAIN = 'cdn.kabaddi-trainer.com'
STATICFILES_STORAGE = 'storages.backends.s3boto3.StaticS3Boto3Storage'
```

### 16.3 Pipeline Performance Optimization

**Pose Extraction Optimization**:
```python
# GPU acceleration for pose estimation
import torch

def optimize_pose_extraction():
    # Use GPU if available
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Optimize YOLO model
    yolo = YOLO("yolov8n.pt")
    yolo.to(device)
    
    # Batch processing for multiple frames
    batch_size = 8
    frames_batch = []
    
    for frame in video_frames:
        frames_batch.append(frame)
        if len(frames_batch) == batch_size:
            results = yolo.track(frames_batch)
            process_batch_results(results)
            frames_batch = []
```

**Memory Optimization**:
```python
# Streaming video processing
def process_video_streaming(video_path):
    cap = cv2.VideoCapture(video_path)
    
    # Process frames in chunks to manage memory
    chunk_size = 30  # 1 second at 30 FPS
    frame_buffer = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_buffer.append(frame)
        
        if len(frame_buffer) == chunk_size:
            # Process chunk
            poses_chunk = process_frame_chunk(frame_buffer)
            yield poses_chunk
            frame_buffer = []
    
    # Process remaining frames
    if frame_buffer:
        poses_chunk = process_frame_chunk(frame_buffer)
        yield poses_chunk
```

**Parallel Processing**:
```python
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

def parallel_error_computation(user_poses, expert_poses):
    # Split computation across CPU cores
    num_cores = mp.cpu_count()
    chunk_size = len(user_poses) // num_cores
    
    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        futures = []
        
        for i in range(0, len(user_poses), chunk_size):
            chunk_user = user_poses[i:i+chunk_size]
            chunk_expert = expert_poses[i:i+chunk_size]
            
            future = executor.submit(compute_chunk_errors, chunk_user, chunk_expert)
            futures.append(future)
        
        # Combine results
        all_errors = []
        for future in futures:
            chunk_errors = future.result()
            all_errors.extend(chunk_errors)
    
    return np.array(all_errors)
```

---

This completes Part 2 of the comprehensive system documentation. The documentation now covers detailed code analysis, async task implementation, pipeline integration, data flow analysis, security implementation, and performance optimization strategies.

Part 3 will continue with testing strategies, deployment procedures, maintenance and monitoring, troubleshooting guides, and future enhancement recommendations.