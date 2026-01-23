# AR-Based Kabaddi Ghost Trainer - Complete System Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [User Flow Analysis](#user-flow-analysis)
4. [Backend Components](#backend-components)
5. [Pipeline Architecture](#pipeline-architecture)
6. [Database Schema](#database-schema)
7. [API Documentation](#api-documentation)
8. [File Structure Analysis](#file-structure-analysis)
9. [Configuration Management](#configuration-management)
10. [Error Handling](#error-handling)

---

## 1. System Overview

### 1.1 Project Purpose

The AR-Based Kabaddi Ghost Trainer is a comprehensive system designed to enable Kabaddi players to:
- Learn movements by watching a ghost trainer in Augmented Reality (AR)
- Practice movements themselves through video recording
- Receive objective, explainable, AI-generated feedback based on pose analysis

### 1.2 Core Principles

**Non-Real-Time Processing**: All evaluation happens AFTER recording, not during live performance.

**Pose-Centric Analysis**: The system operates on 2D pose data (COCO-17 format) rather than raw video analysis.

**Pseudo-3D AR**: AR rendering uses 2D pose sequences anchored in 3D space, not true 3D reconstruction.

**Deterministic Pipeline**: The evaluation pipeline is treated as a "deterministic analytical truth engine" with strict semantic levels.

### 1.3 Technology Stack

**Backend Framework**: Django (Python)
**Database**: SQLite (development) / PostgreSQL (production)
**Pose Estimation**: MediaPipe + YOLO
**Temporal Alignment**: Dynamic Time Warping (DTW)
**AR Framework**: Unity + AR Foundation (mobile)
**LLM Integration**: GPT-4 for feedback generation
**File Storage**: Local filesystem with structured directories

---

## 2. Architecture Design

### 2.1 5-Layer System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Mobile App    │───▶│  Django Backend  │───▶│ Pose Pipeline   │
│                 │    │                  │    │ (EXISTING)      │
│ - AR Playback   │    │ - Session Mgmt   │    │ - Level 1-4     │
│ - Video Record  │    │ - File Storage   │    │ - Error Metrics │
│ - Status Poll   │    │ - Async Tasks    │    │ - Scoring       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   File System    │    │ LLM Feedback    │
                       │ - raw_videos/    │    │ - RAG-based     │
                       │ - poses/         │    │ - Text + TTS    │
                       │ - results/       │    │ - Coaching      │
                       └──────────────────┘    └─────────────────┘
```

### 2.2 Layer Responsibilities

**Layer 1 - Mobile App (Frontend)**
- AR ghost trainer playback using Unity + AR Foundation
- Video recording of user attempts
- UI controls for tutorial selection and assessment triggers
- Status polling and result display
- NO pose estimation or ML processing

**Layer 2 - Django Backend (Orchestration)**
- Session management and state tracking
- File storage and retrieval
- Async task coordination
- API endpoint provision
- NO pose mathematics or evaluation logic

**Layer 3 - Pose & Evaluation Pipeline (Analytical Engine)**
- Level-1: Pose Cleaning & Normalization
- Level-2: Temporal Alignment (DTW)
- Level-3: Error Localization (MANDATORY)
- Level-4: Similarity Scoring
- Deterministic, reproducible results

**Layer 4 - LLM Feedback Engine (Optional)**
- RAG-based coaching knowledge retrieval
- Structured data interpretation (not raw video/pose analysis)
- Natural language feedback generation
- Text-to-Speech conversion

**Layer 5 - AR Playback (Mobile-side)**
- Pseudo-3D skeleton rendering
- Real-world anchoring
- Deterministic movement playback

### 2.3 Critical Architectural Boundaries

**Backend NEVER performs:**
- Pose estimation mathematics
- Similarity computation algorithms
- Pipeline level logic modification
- Real-time processing during recording

**Pipeline NEVER modified for:**
- Backend integration convenience
- API response optimization
- Database storage requirements
- Mobile app compatibility

---

## 3. User Flow Analysis

### 3.1 Complete 9-Step User Journey

**STEP 1 - App Launch & Tutorial Selection**
```
User Action: Opens mobile app
App Behavior: Fetches available tutorials from backend
Backend Role: Returns tutorial metadata via GET /api/tutorials/
Data Flow: Tutorial list with descriptions and expert pose references
```

**STEP 2 - AR Ghost Trainer Playback**
```
User Action: Taps "Play Tutorial"
App Behavior: Loads trainer pose sequence, renders as pseudo-3D AR ghost
Backend Role: Serves AR-ready pose data via GET /api/tutorials/{id}/ar-poses/
Data Flow: COCO-17 pose sequences formatted for AR rendering
Important: No pose estimation, scoring, or backend interaction during playback
```

**STEP 3 - User Practice ("Try")**
```
User Action: Taps "Try"
App Behavior: Records video of user performing movement
Backend Role: None (no interaction)
Data Flow: Video stored locally on device
Important: No pose estimation on device, no feedback shown yet
```

**STEP 4 - Video Upload ("Assess")**
```
User Action: Taps "Assess"
App Behavior: Uploads recorded video with tutorial context
Backend Role: Creates UserSession, stores raw video as immutable artifact
Data Flow: POST /api/session/start/ → POST /api/session/{id}/upload-video/
Important: No pose math during upload, video treated as source artifact
```

**STEP 5 - Offline Pose Extraction**
```
Trigger: Backend async process
Process: Converts raw video → Level-1 cleaned pose sequence
Backend Role: Calls existing pose extraction tool via subprocess
Data Flow: video.mp4 → pose_level1.npy (COCO-17 format)
Important: OFFLINE/ASYNC, backend does not compute pose itself
```

**STEP 6 - Pose Evaluation Pipeline Execution**
```
Trigger: Pose extraction completion
Process: Executes 4-level analytical pipeline in strict order
Pipeline Levels:
  1. Level-1: Pose Cleaning & Normalization (already done)
  2. Level-2: Temporal Alignment using DTW on pelvis trajectories
  3. Level-3: Error Localization (frame-wise + joint-wise diagnostics)
  4. Level-4: Similarity Scoring (overall performance metrics)
Backend Role: Treats pipeline as black-box analytical engine
Data Flow: user_pose.npy + expert_pose.npy → scores.json + error_metrics.json
Important: Backend stores outputs without interpretation
```

**STEP 7 - Result Availability**
```
Trigger: Pipeline completion
Backend Behavior: Updates session status to "evaluated"
App Behavior: Polls session status, fetches results when ready
Data Flow: GET /api/session/{id}/status/ → GET /api/session/{id}/results/
Important: Both scores.json AND error_metrics.json are returned
```

**STEP 8 - LLM-Based Feedback Generation**
```
Trigger: Analytical results availability
Input Data: error_metrics.json (primary), scores.json (secondary), tutorial context
LLM Role: Reasons over structured numeric error data, retrieves coaching knowledge
Backend Role: Orchestrates LLM call, stores generated feedback
Data Flow: error_metrics.json → LLM → feedback_text + optional_audio
Important: LLM does NOT analyze video or poses directly
```

**STEP 9 - Voice Feedback Delivery**
```
Trigger: Feedback generation completion
App Behavior: Plays feedback audio, displays summary text
Backend Role: Serves feedback text and optional TTS audio
Data Flow: GET /api/session/{id}/results/ includes feedback data
Important: Feedback based on pose-level error analysis, not video analysis
```

### 3.2 Critical Flow Rules

1. **AR playback accuracy is NOT evaluated** - Only user imitation accuracy matters
2. **Error Localization measures USER performance** - Not AR rendering quality
3. **Backend NEVER performs pose math** - Only orchestrates existing tools
4. **Pipeline semantics must NOT be collapsed** - 4 levels remain distinct
5. **Evaluation happens AFTER recording** - Never during live performance

---

## 4. Backend Components

### 4.1 Django Project Structure

```
kabaddi_backend/
├── kabaddi_backend/          # Project configuration
│   ├── __init__.py
│   ├── settings.py           # Django settings and pipeline paths
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py              # WSGI application entry point
├── api/                     # Main application
│   ├── migrations/          # Database migrations
│   ├── management/          # Custom management commands
│   │   └── commands/
│   │       └── create_tutorials.py
│   ├── __init__.py
│   ├── models.py            # Database models
│   ├── views.py             # API views
│   ├── urls.py              # API URL patterns
│   └── tasks.py             # Async task definitions
├── media/                   # File storage
│   ├── raw_videos/          # Uploaded user videos
│   ├── poses/               # Extracted pose files
│   ├── expert_poses/        # Reference trainer poses
│   └── results/             # Pipeline output files
├── db.sqlite3              # SQLite database
└── manage.py               # Django management script
```

### 4.2 Settings Configuration Analysis

**File: kabaddi_backend/settings.py**

```python
# Core Django Configuration
SECRET_KEY = 'django-insecure-kabaddi-trainer-dev-key'  # Development only
DEBUG = True                                            # Disable in production
ALLOWED_HOSTS = ['*']                                  # Restrict in production

# Application Registration
INSTALLED_APPS = [
    'django.contrib.contenttypes',  # Content type framework
    'django.contrib.auth',          # Authentication system
    'api',                          # Main application
]

# Middleware Stack (Minimal)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',    # Security headers
    'django.middleware.common.CommonMiddleware',        # Common processing
    'django.middleware.csrf.CsrfViewMiddleware',       # CSRF protection
]

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Media File Handling
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Pipeline Integration Paths
PIPELINE_BASE_DIR = (BASE_DIR.parent.parent / 'level1_pose').resolve()
EXTRACT_POSE_SCRIPT = PIPELINE_BASE_DIR / 'pose_extract_cli.py'
RUN_PIPELINE_SCRIPT = BASE_DIR.parent.parent / 'run_pipeline.py'
```

**Critical Path Resolution:**
- `BASE_DIR`: Points to kabaddi_backend/ directory
- `PIPELINE_BASE_DIR`: Resolves to project_root/level1_pose/
- `EXTRACT_POSE_SCRIPT`: Points to CLI-compatible pose extraction
- `RUN_PIPELINE_SCRIPT`: Points to main pipeline orchestrator

**Media Directory Structure:**
```python
# Automatic directory creation
os.makedirs(MEDIA_ROOT / 'raw_videos', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'poses', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'expert_poses', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'results', exist_ok=True)
```

### 4.3 URL Configuration Analysis

**File: kabaddi_backend/urls.py**
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('api/', include('api.urls')),  # All API endpoints under /api/
]
```

**File: api/urls.py**
```python
urlpatterns = [
    # Tutorial Management
    path('tutorials/', TutorialListView.as_view(), name='tutorial_list'),
    path('tutorials/<uuid:tutorial_id>/ar-poses/', ARPoseDataView.as_view(), name='ar_pose_data'),
    
    # Session Management
    path('session/start/', SessionStartView.as_view(), name='session_start'),
    path('session/<uuid:session_id>/upload-video/', VideoUploadView.as_view(), name='video_upload'),
    path('session/<uuid:session_id>/assess/', AssessmentTriggerView.as_view(), name='assessment_trigger'),
    path('session/<uuid:session_id>/status/', SessionStatusView.as_view(), name='session_status'),
    path('session/<uuid:session_id>/results/', ResultsView.as_view(), name='results'),
]
```

**URL Pattern Analysis:**
- All endpoints use UUID parameters for security
- RESTful design with resource-based paths
- Clear separation between tutorial and session operations
- AR-specific endpoint for mobile app integration

---

## 5. Pipeline Architecture

### 5.1 4-Level Analytical Engine

The pose evaluation pipeline consists of four distinct, mandatory analytical levels that must execute in strict order:

**Level-1: Pose Cleaning & Normalization**
```
Purpose: Stabilizes pose data, removes noise, scale, and translation artifacts
Input: Raw pose data (potentially noisy, scaled, translated)
Process: 
  - Noise reduction algorithms
  - Scale normalization
  - Translation centering
  - Confidence filtering
Output: Cleaned poses (T, 17, 2) in canonical coordinate system
Location: level1_pose/level1_cleaning.py
Critical: NOT pose extraction - this is post-extraction cleaning
```

**Level-2: Temporal Alignment**
```
Purpose: Aligns user and trainer sequences in time using DTW
Input: User pose sequence + Trainer pose sequence
Process:
  - Extract pelvis trajectories (hip midpoint)
  - Compute pairwise Euclidean distances
  - Apply Dynamic Time Warping algorithm
  - Generate optimal alignment path
Output: Aligned frame indices for both sequences
Location: temporal_alignment.py
Critical: Handles speed variation, NOT similarity computation
```

**Level-3: Error Localization (MANDATORY FIRST-CLASS OUTPUT)**
```
Purpose: Computes frame-wise and joint-wise geometric errors
Input: Aligned user poses + Aligned trainer poses
Process:
  - Frame-wise Euclidean error per joint
  - Joint-wise aggregated statistics (mean, max, std)
  - Temporal phase segmentation (early, mid, late)
  - Error ranking and prioritization
Output: error_metrics.json with detailed diagnostic data
Location: error_localization.py
Critical: THIS IS NOT OPTIONAL - Primary analytical output
```

**Level-4: Similarity Scoring**
```
Purpose: Computes high-level performance scores
Input: Aligned pose sequences
Process:
  - Structural similarity metrics
  - Temporal consistency analysis
  - Overall performance aggregation
Output: scores.json with summary metrics
Location: pose_validation_metrics.py
Critical: This is SUMMARY, not main output - Level-3 is primary
```

### 5.2 Pipeline Execution Flow

**File: run_pipeline.py**

```python
def main(args):
    """Main pipeline execution with strict 4-level semantics"""
    
    # Stage 1: Load/Extract Expert Pose
    expert_pose = load_or_extract_pose(
        input_path=args.expert_pose,
        video_path=args.expert_video,
        config=config,
        logger=logger,
        name='expert'
    )
    
    # Stage 2: Load/Extract User Pose + Level-1 Cleaning
    user_pose = load_or_extract_pose(
        input_path=args.user_pose,
        video_path=args.user_video,
        config=config,
        logger=logger,
        name='user'
    )
    
    # Stage 3: Execute Levels 2-4
    scores = run_validation(expert_pose, user_pose, output_dir, logger)
    
    # Stage 4: Generate Feedback (Optional)
    feedback = run_feedback_pipeline(scores, output_dir, config, logger)
```

**Critical Pipeline Semantics:**
1. Pipeline ALWAYS runs all levels in order
2. Level-3 Error Localization is NEVER skipped
3. Both scores.json AND error_metrics.json are REQUIRED outputs
4. Pipeline treats pose sequences as immutable analytical inputs
5. Backend NEVER modifies pipeline logic for integration convenience

### 5.3 Pose Extraction Integration

**File: level1_pose/pose_extract_cli.py**

```python
def extract_pose_from_video(video_path, output_path):
    """Extract pose from video and save as COCO-17 format"""
    
    # YOLO person detection + tracking
    yolo = YOLO("yolov8n.pt")
    
    # MediaPipe pose estimation
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.7
    )
    
    # Process video frame by frame
    cap = cv2.VideoCapture(video_path)
    all_frames_2d = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # YOLO tracking for person detection
        results = yolo.track(frame, persist=True, classes=[0])
        
        # Select most active person (raider)
        raider_id = select_most_active_person(results, tracks_history)
        
        # Extract pose from raider bounding box
        if raider_id:
            pose_data = extract_pose_from_bbox(frame, raider_box, pose)
            all_frames_2d.append(pose_data)
    
    # Convert MP33 to COCO17 format
    mp33_poses = np.array(all_frames_2d)
    coco17_poses = mp33_to_coco17(mp33_poses)
    
    # Apply Level-1 cleaning
    cleaned_poses = clean_level1_poses(coco17_poses)
    
    # Save final output
    np.save(output_path, cleaned_poses)
```

**Integration Points:**
- CLI-compatible interface for backend subprocess calls
- Automatic format conversion (MP33 → COCO17)
- Integrated Level-1 cleaning pipeline
- Deterministic output format for evaluation pipeline

---

## 6. Database Schema

### 6.1 Entity Relationship Design

```
Tutorial (1) ──────── (N) UserSession (1) ──────── (1) RawVideo
    │                        │                           
    │                        ├── (1) PoseArtifact       
    │                        ├── (1) AnalyticalResults  
    │                        └── (1) LLMFeedback        
    │
    └── expert_pose_path (file reference)
```

### 6.2 Model Definitions

**File: api/models.py**

**Tutorial Model**
```python
class Tutorial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=50, unique=True)  # hand_touch, toe_touch, bonus
    description = models.TextField()
    expert_pose_path = models.CharField(max_length=255)  # expert_poses/hand_touch.npy
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

**Purpose**: Stores tutorial metadata and references to expert pose files
**Key Fields**:
- `name`: Unique identifier for tutorial type
- `expert_pose_path`: File path to reference trainer pose sequence
- `is_active`: Enables/disables tutorials without deletion

**UserSession Model**
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
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tutorial = models.ForeignKey(Tutorial, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(null=True, blank=True)
```

**Purpose**: Tracks user assessment sessions and pipeline progress
**Key Fields**:
- `status`: Detailed pipeline progress tracking
- `tutorial`: Links to specific movement being assessed
- `error_message`: Stores failure details for debugging

**Status Flow**:
```
created → video_uploaded → pose_extracted → level1_complete → 
level2_complete → level3_complete → scoring_complete → feedback_generated
                                    ↓
                                 failed (any stage)
```

**RawVideo Model**
```python
class RawVideo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_session = models.OneToOneField(UserSession, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    checksum = models.CharField(max_length=64, null=True, blank=True)
```

**Purpose**: Stores metadata for uploaded user videos (immutable source artifacts)
**Key Fields**:
- `file_path`: Absolute path to stored video file
- `file_size`: For validation and storage management
- `checksum`: Optional integrity verification

**PoseArtifact Model**
```python
class PoseArtifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_session = models.OneToOneField(UserSession, on_delete=models.CASCADE)
    pose_level1_path = models.CharField(max_length=255)  # Level-1 cleaned poses
    generated_at = models.DateTimeField(auto_now_add=True)
```

**Purpose**: Tracks generated pose files from video extraction
**Key Fields**:
- `pose_level1_path`: Path to Level-1 cleaned pose sequence
- `generated_at`: Timestamp for cache management

**AnalyticalResults Model**
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

**Purpose**: Stores paths to ALL pipeline outputs (both mandatory)
**Critical Design**:
- `error_metrics_json_path`: MANDATORY - Level-3 is first-class output
- `scores_json_path`: MANDATORY - Level-4 summary metrics
- Both fields are required, neither is optional

**LLMFeedback Model**
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

**Purpose**: Stores LLM-generated coaching feedback
**Key Design**:
- LLM operates on structured error data, NOT raw video/poses
- Feedback based on Level-3 error localization results
- Optional TTS audio generation for voice feedback

### 6.3 Database Relationships

**One-to-Many Relationships**:
- Tutorial → UserSession (one tutorial, many user attempts)

**One-to-One Relationships**:
- UserSession → RawVideo (one session, one video)
- UserSession → PoseArtifact (one session, one pose file)
- UserSession → AnalyticalResults (one session, one result set)
- UserSession → LLMFeedback (one session, one feedback)

**Cascade Behavior**:
- Deleting Tutorial cascades to all UserSessions
- Deleting UserSession cascades to all related artifacts
- File cleanup handled separately (not database-enforced)

---

## 7. API Documentation

### 7.1 Tutorial Management Endpoints

**GET /api/tutorials/**

*Purpose*: Retrieve list of available tutorials for mobile app

*Request*:
```http
GET /api/tutorials/ HTTP/1.1
Host: backend.kabaddi-trainer.com
Accept: application/json
```

*Response*:
```json
{
  "tutorials": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "hand_touch",
      "description": "Hand touch kabaddi movement"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001", 
      "name": "toe_touch",
      "description": "Toe touch kabaddi movement"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "name": "bonus", 
      "description": "Bonus kabaddi movement"
    }
  ]
}
```

*Implementation*:
```python
class TutorialListView(View):
    def get(self, request):
        tutorials = Tutorial.objects.filter(is_active=True)
        data = [{
            'id': str(tutorial.id),
            'name': tutorial.name,
            'description': tutorial.description
        } for tutorial in tutorials]
        return JsonResponse({'tutorials': data})
```

**GET /api/tutorials/{tutorial_id}/ar-poses/**

*Purpose*: Serve AR-ready pose data for mobile app ghost playback

*Request*:
```http
GET /api/tutorials/550e8400-e29b-41d4-a716-446655440000/ar-poses/ HTTP/1.1
Host: backend.kabaddi-trainer.com
Accept: application/json
```

*Response*:
```json
{
  "tutorial_id": "550e8400-e29b-41d4-a716-446655440000",
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
          "name": "nose",
          "x": 0.5,
          "y": 0.3,
          "z": 0.0,
          "confidence": 1.0
        },
        {
          "name": "left_shoulder",
          "x": 0.4,
          "y": 0.4,
          "z": 0.0,
          "confidence": 1.0
        }
      ]
    }
  ]
}
```

*AR Data Format Specification*:
- `x, y`: Normalized coordinates (0.0-1.0)
- `z`: Always 0.0 for pseudo-3D (anchored in 3D space)
- `confidence`: Joint detection confidence (0.0-1.0)
- `timestamp`: Frame time in seconds (frame_index / fps)

### 7.2 Session Management Endpoints

**POST /api/session/start/**

*Purpose*: Create new user assessment session

*Request*:
```http
POST /api/session/start/ HTTP/1.1
Host: backend.kabaddi-trainer.com
Content-Type: application/json

{
  "tutorial_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

*Response*:
```json
{
  "session_id": "660e8400-e29b-41d4-a716-446655440000",
  "tutorial": "hand_touch",
  "status": "created"
}
```

*Error Responses*:
```json
// Missing tutorial_id
{
  "error": "tutorial_id required"
}

// Invalid tutorial_id
{
  "error": "Invalid tutorial_id"
}
```

**POST /api/session/{session_id}/upload-video/**

*Purpose*: Upload user performance video

*Request*:
```http
POST /api/session/660e8400-e29b-41d4-a716-446655440000/upload-video/ HTTP/1.1
Host: backend.kabaddi-trainer.com
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="video"; filename="user_attempt.mp4"
Content-Type: video/mp4

[binary video data]
--boundary--
```

*Response*:
```json
{
  "session_id": "660e8400-e29b-41d4-a716-446655440000",
  "status": "video_uploaded",
  "file_size": 15728640
}
```

*Validation Rules*:
- Maximum file size: 100MB
- Supported formats: .mp4, .mov, .avi
- File stored as: `media/raw_videos/{session_id}.mp4`

**POST /api/session/{session_id}/assess/**

*Purpose*: Trigger async pipeline execution

*Request*:
```http
POST /api/session/660e8400-e29b-41d4-a716-446655440000/assess/ HTTP/1.1
Host: backend.kabaddi-trainer.com
```

*Response*:
```json
{
  "session_id": "660e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Multi-level analytical pipeline started"
}
```

*Preconditions*:
- Session must exist
- Session status must be "video_uploaded"
- Expert pose file must exist for tutorial

**GET /api/session/{session_id}/status/**

*Purpose*: Poll session status for mobile app

*Request*:
```http
GET /api/session/660e8400-e29b-41d4-a716-446655440000/status/ HTTP/1.1
Host: backend.kabaddi-trainer.com
Accept: application/json
```

*Response*:
```json
{
  "session_id": "660e8400-e29b-41d4-a716-446655440000",
  "status": "feedback_generated",
  "updated_at": "2024-01-15T10:30:45.123456Z",
  "error_message": null
}
```

*Status Values*:
- `created`: Session initialized
- `video_uploaded`: Video stored successfully
- `pose_extracted`: Pose extraction completed
- `level1_complete`: Level-1 cleaning completed
- `level2_complete`: Level-2 alignment completed
- `level3_complete`: Level-3 error localization completed
- `scoring_complete`: Level-4 scoring completed
- `feedback_generated`: LLM feedback generated
- `failed`: Pipeline failed (check error_message)

**GET /api/session/{session_id}/results/**

*Purpose*: Retrieve complete assessment results

*Request*:
```http
GET /api/session/660e8400-e29b-41d4-a716-446655440000/results/ HTTP/1.1
Host: backend.kabaddi-trainer.com
Accept: application/json
```

*Response*:
```json
{
  "session_id": "660e8400-e29b-41d4-a716-446655440000",
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
      },
      "right_elbow": {
        "mean": 0.23,
        "max": 0.67,
        "std": 0.18
      }
    },
    "temporal_phases": {
      "early": {
        "left_shoulder": 0.12,
        "right_elbow": 0.19
      },
      "mid": {
        "left_shoulder": 0.18,
        "right_elbow": 0.25
      },
      "late": {
        "left_shoulder": 0.16,
        "right_elbow": 0.25
      }
    }
  },
  "feedback": {
    "text": "Based on your hand_touch attempt, focus on improving your left shoulder positioning during the mid-phase of the movement...",
    "audio_path": null,
    "generated_at": "2024-01-15T10:30:50.123456Z"
  },
  "completed_at": "2024-01-15T10:30:45.123456Z"
}
```

*Critical Response Structure*:
- `scores`: Level-4 similarity scoring (summary metrics)
- `error_metrics`: Level-3 error localization (PRIMARY diagnostic data)
- `feedback`: LLM-generated coaching advice (optional)
- Both scores AND error_metrics are MANDATORY outputs

### 7.3 Error Handling

**Standard Error Response Format**:
```json
{
  "error": "Human-readable error message",
  "details": "Additional technical details (optional)",
  "timestamp": "2024-01-15T10:30:45.123456Z"
}
```

**HTTP Status Codes**:
- `200 OK`: Successful request
- `400 Bad Request`: Invalid input data
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side failure

**Common Error Scenarios**:
```json
// Session not found
{
  "error": "Session not found"
}

// Invalid session status
{
  "error": "Invalid status: video_uploaded"
}

// Pipeline execution failure
{
  "error": "Pipeline execution failed",
  "details": "Expert pose not found: expert_poses/invalid.npy"
}

// File corruption
{
  "error": "Scores file corrupted"
}
```

---

## 8. File Structure Analysis

### 8.1 Project Root Structure

```
kabaddi_trainer/                    # Project root directory
├── .agent/                         # Agent configuration
├── .amazonq/                       # Amazon Q rules
├── .qodo/                          # Qodo configuration
├── Assets/                         # Unity assets (AR components)
├── kabaddi_backend/               # Django backend (THIS DOCUMENTATION FOCUS)
├── legacy/                        # Deprecated components
├── level1_pose/                   # Level-1 pose processing
├── pipeline_fidelity_test/        # Pipeline testing
├── pipeline_out/                  # Pipeline output samples
├── samples/                       # Sample data files
├── tests/                         # Test suites
├── Complete_System_Vision.docx    # System requirements
├── run_pipeline.py               # Main pipeline orchestrator
├── temporal_alignment.py         # Level-2 DTW implementation
├── error_localization.py         # Level-3 error analysis
├── feedback_generator.py         # LLM feedback system
├── pipeline_config.py            # Pipeline configuration
├── pipeline_logger.py            # Logging utilities
└── [other pipeline components]
```

### 8.2 Backend Directory Deep Dive

**kabaddi_backend/ Structure**:
```
kabaddi_backend/
├── kabaddi_backend/              # Django project configuration
│   ├── __init__.py              # Python package marker
│   ├── settings.py              # Django settings (CRITICAL)
│   ├── urls.py                  # Root URL configuration
│   └── wsgi.py                  # WSGI application entry
├── api/                         # Main Django application
│   ├── migrations/              # Database schema migrations
│   │   ├── __init__.py
│   │   ├── 0001_initial.py      # Initial model creation
│   │   └── 0002_alter_usersession_status_llmfeedback.py
│   ├── management/              # Custom Django commands
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       └── create_tutorials.py  # Tutorial data seeding
│   ├── __init__.py
│   ├── models.py                # Database models (CRITICAL)
│   ├── views.py                 # API view implementations (CRITICAL)
│   ├── urls.py                  # API URL patterns
│   └── tasks.py                 # Async task definitions (CRITICAL)
├── media/                       # File storage root
│   ├── raw_videos/              # User uploaded videos
│   │   └── {session_id}.mp4     # Named by session UUID
│   ├── poses/                   # Extracted pose files
│   │   └── {session_id}.npy     # Level-1 cleaned poses
│   ├── expert_poses/            # Reference trainer poses
│   │   ├── hand_touch.npy       # Hand touch reference
│   │   ├── toe_touch.npy        # Toe touch reference
│   │   └── bonus.npy            # Bonus movement reference
│   └── results/                 # Pipeline output files
│       └── {session_id}/        # Per-session results
│           ├── scores.json      # Level-4 similarity scores
│           ├── error_metrics.json  # Level-3 error localization
│           ├── feedback.json    # LLM feedback (optional)
│           └── feedback.txt     # Detailed feedback text
├── db.sqlite3                   # SQLite database file
└── manage.py                    # Django management script
```

### 8.3 Pipeline Integration Files

**level1_pose/ Directory**:
```
level1_pose/
├── pose_extract_cli.py          # CLI pose extraction (BACKEND INTEGRATION)
├── raider_pose_extract_2d.py    # Original pose extraction
├── level1_cleaning.py           # Level-1 cleaning algorithms
├── mp33_to_coco17.py           # Format conversion utilities
├── joints.py                    # Joint definition constants
├── visualize_level1.py         # Pose visualization tools
├── yolov8n.pt                  # YOLO model weights
└── samples/
    └── kabaddi_clip.mp4        # Sample video for testing
```

**Root Pipeline Files**:
```
run_pipeline.py                  # Main pipeline orchestrator (BACKEND CALLS THIS)
temporal_alignment.py            # Level-2 DTW implementation
error_localization.py           # Level-3 error analysis (MANDATORY OUTPUT)
pose_validation_metrics.py      # Level-4 similarity scoring
feedback_generator.py           # LLM feedback generation
pipeline_config.py             # Configuration management
pipeline_logger.py             # Logging utilities
```

### 8.4 File Naming Conventions

**Session-Based Naming**:
- Raw videos: `{session_uuid}.mp4`
- User poses: `{session_uuid}.npy`
- Results directory: `results/{session_uuid}/`

**Tutorial-Based Naming**:
- Expert poses: `expert_poses/{tutorial_name}.npy`
- AR pose data: Served dynamically, not stored

**Pipeline Output Naming**:
- Similarity scores: `scores.json` (standardized)
- Error metrics: `error_metrics.json` (standardized)
- LLM feedback: `feedback.json` and `feedback.txt`

### 8.5 File Access Patterns

**Read Operations**:
- Expert poses: Read during pipeline execution and AR data serving
- User poses: Read during pipeline execution
- Pipeline outputs: Read during result serving

**Write Operations**:
- Raw videos: Written during upload
- User poses: Written during pose extraction
- Pipeline outputs: Written during pipeline execution
- LLM feedback: Written during feedback generation

**File Lifecycle**:
1. Video uploaded → stored in raw_videos/
2. Pose extracted → stored in poses/
3. Pipeline executed → results stored in results/{session_id}/
4. Results served → files remain for caching
5. Cleanup → handled separately (not automatic)

---

## 9. Configuration Management

### 9.1 Django Settings Deep Analysis

**File: kabaddi_backend/settings.py**

**Core Django Configuration**:
```python
import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent
```
- `BASE_DIR` resolves to `kabaddi_trainer/kabaddi_backend/`
- Used as anchor for all relative path calculations
- Critical for media file storage and pipeline integration

**Security Configuration**:
```python
SECRET_KEY = 'django-insecure-kabaddi-trainer-dev-key'
DEBUG = True
ALLOWED_HOSTS = ['*']
```
- `SECRET_KEY`: Development key (MUST change for production)
- `DEBUG`: Enables detailed error pages (DISABLE for production)
- `ALLOWED_HOSTS`: Accepts all hosts (RESTRICT for production)

**Application Registration**:
```python
INSTALLED_APPS = [
    'django.contrib.contenttypes',  # Required for model relationships
    'django.contrib.auth',          # Required for user management
    'api',                          # Main application
]
```
- Minimal app list for performance
- No admin interface (API-only backend)
- No sessions or messages (stateless design)

**Middleware Configuration**:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware', 
    'django.middleware.csrf.CsrfViewMiddleware',
]
```
- Security middleware for HTTPS headers
- Common middleware for URL processing
- CSRF protection for POST requests
- No authentication middleware (API key auth would go here)

**Database Configuration**:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```
- SQLite for development simplicity
- Production should use PostgreSQL
- Database file stored in backend directory

**Media File Configuration**:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Create media directories
os.makedirs(MEDIA_ROOT / 'raw_videos', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'poses', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'expert_poses', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'results', exist_ok=True)
```
- `MEDIA_URL`: URL prefix for serving media files
- `MEDIA_ROOT`: Filesystem path for media storage
- Automatic directory creation ensures structure exists

**Pipeline Integration Configuration**:
```python
# Pipeline paths
PIPELINE_BASE_DIR = (BASE_DIR.parent.parent / 'level1_pose').resolve()
EXTRACT_POSE_SCRIPT = PIPELINE_BASE_DIR / 'pose_extract_cli.py'
RUN_PIPELINE_SCRIPT = BASE_DIR.parent.parent / 'run_pipeline.py'
```

**Path Resolution Analysis**:
- `BASE_DIR`: `kabaddi_trainer/kabaddi_backend/`
- `BASE_DIR.parent`: `kabaddi_trainer/`
- `BASE_DIR.parent.parent`: `kabaddi_trainer/` (project root)
- `PIPELINE_BASE_DIR`: `kabaddi_trainer/level1_pose/`

**Template Configuration**:
```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]
```
- Required for Django but unused (API-only backend)
- Minimal configuration for framework compatibility

**WSGI Configuration**:
```python
WSGI_APPLICATION = 'kabaddi_backend.wsgi.application'
```
- Entry point for production deployment
- Links to wsgi.py file in project directory

### 9.2 Pipeline Configuration

**File: pipeline_config.py**

```python
class PipelineConfig:
    """Configuration management for pose evaluation pipeline"""
    
    def __init__(self):
        # Pose extraction settings
        self.pose_model = "movenet_lightning.tflite"
        self.target_fps = 30.0
        
        # Visualization settings
        self.canvas_size = (640, 480)
        self.viz_fps = 30
        self.line_thickness = 2
        self.joint_radius = 4
        
        # TTS settings
        self.tts_rate = 150
        self.tts_volume = 0.8
        
        # Processing flags
        self.enable_tts = True
        self.enable_viz = True
        self.verbose = False
    
    @classmethod
    def from_args(cls, args):
        """Create configuration from command line arguments"""
        config = cls()
        
        if hasattr(args, 'pose_model'):
            config.pose_model = args.pose_model
        if hasattr(args, 'target_fps'):
            config.target_fps = args.target_fps
        if hasattr(args, 'no_tts'):
            config.enable_tts = not args.no_tts
        if hasattr(args, 'no_viz'):
            config.enable_viz = not args.no_viz
        if hasattr(args, 'verbose'):
            config.verbose = args.verbose
            
        return config
```

**Configuration Categories**:
- **Pose Extraction**: Model selection and FPS settings
- **Visualization**: Canvas size and rendering parameters
- **TTS**: Speech synthesis configuration
- **Processing**: Feature enable/disable flags

### 9.3 Environment-Specific Configuration

**Development Configuration**:
```python
# Development settings (current)
DEBUG = True
ALLOWED_HOSTS = ['*']
DATABASE = SQLite
MEDIA_STORAGE = Local filesystem
LOGGING_LEVEL = DEBUG
```

**Production Configuration** (recommended):
```python
# Production settings (to implement)
DEBUG = False
ALLOWED_HOSTS = ['api.kabaddi-trainer.com']
DATABASE = PostgreSQL with connection pooling
MEDIA_STORAGE = AWS S3 or similar
LOGGING_LEVEL = INFO
SECURITY_HEADERS = Enabled
HTTPS_REDIRECT = Enabled
```

**Configuration Management Strategy**:
- Environment variables for sensitive data
- Separate settings files for different environments
- Docker configuration for containerized deployment
- CI/CD pipeline integration for automated deployment

---

## 10. Error Handling

### 10.1 Error Handling Strategy

The system implements a multi-layered error handling approach:

**Layer 1: Input Validation**
- File size and format validation
- UUID parameter validation
- JSON payload validation
- Session state validation

**Layer 2: Pipeline Error Handling**
- Subprocess execution monitoring
- File existence verification
- JSON format validation
- Pipeline output verification

**Layer 3: System Error Handling**
- Database transaction rollback
- File cleanup on failure
- Graceful degradation
- Error logging and monitoring

### 10.2 API Error Responses

**Standard Error Format**:
```json
{
  "error": "Human-readable error message",
  "details": "Technical details for debugging",
  "timestamp": "ISO 8601 timestamp",
  "session_id": "UUID (if applicable)"
}
```

**HTTP Status Code Usage**:
- `400 Bad Request`: Client input errors
- `404 Not Found`: Resource not found
- `409 Conflict`: State conflicts (e.g., wrong session status)
- `413 Payload Too Large`: File size exceeded
- `422 Unprocessable Entity`: Valid format but invalid content
- `500 Internal Server Error`: Server-side failures
- `503 Service Unavailable`: Pipeline temporarily unavailable

### 10.3 Pipeline Error Handling

**File: api/tasks.py - Error Handling Analysis**

```python
def process_multi_level_pipeline(session_id: str):
    try:
        session = UserSession.objects.get(id=session_id)
        
        # Stage 1: Pose Extraction
        try:
            result = subprocess.run(extract_cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            session.status = 'failed'
            session.error_message = f"Pose extraction failed: {e.stderr}"
            session.save()
            raise
        
        # Stage 2: Pipeline Execution
        try:
            result = subprocess.run(pipeline_cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            session.status = 'failed'
            session.error_message = f"Pipeline execution failed: {e.stderr}"
            session.save()
            raise
        
        # Stage 3: Output Validation
        if not scores_path.exists():
            raise FileNotFoundError("Pipeline failed to generate scores.json")
        
        if not error_metrics_path.exists():
            raise FileNotFoundError("Pipeline failed to generate error_metrics.json")
        
        # Stage 4: JSON Validation
        try:
            with open(scores_path, 'r') as f:
                scores = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid scores.json format: {e}")
        
    except Exception as e:
        session.status = 'failed'
        session.error_message = str(e)
        session.save()
        raise
```

**Error Handling Principles**:
1. **Fail Fast**: Detect errors as early as possible
2. **State Consistency**: Always update session status on failure
3. **Error Preservation**: Store error messages for debugging
4. **Graceful Degradation**: Continue with partial results when possible
5. **Resource Cleanup**: Clean up temporary files on failure

### 10.4 Common Error Scenarios

**Video Upload Errors**:
```python
# File too large
if video_file.size > 100 * 1024 * 1024:
    return JsonResponse({'error': 'File too large'}, status=413)

# Invalid file format
if not video_file.name.lower().endswith(('.mp4', '.mov', '.avi')):
    return JsonResponse({'error': 'Invalid file format'}, status=422)

# Storage failure
try:
    with open(video_path, 'wb') as f:
        for chunk in video_file.chunks():
            f.write(chunk)
except IOError as e:
    return JsonResponse({'error': f'Storage failed: {str(e)}'}, status=500)
```

**Pipeline Execution Errors**:
```python
# Expert pose not found
if not expert_pose_path.exists():
    raise FileNotFoundError(f"Expert pose not found: {expert_pose_path}")

# Pipeline script not found
if not settings.RUN_PIPELINE_SCRIPT.exists():
    raise FileNotFoundError(f"Pipeline script not found: {settings.RUN_PIPELINE_SCRIPT}")

# Pipeline execution failure
try:
    result = subprocess.run(pipeline_cmd, capture_output=True, text=True, check=True)
except subprocess.CalledProcessError as e:
    error_msg = f"Pipeline failed: {e.stderr}"
    session.error_message = error_msg
    session.status = 'failed'
    session.save()
    raise RuntimeError(error_msg)
```

**Data Validation Errors**:
```python
# Missing mandatory outputs
if not error_metrics_path.exists():
    raise FileNotFoundError("Level-3 Error Localization output missing")

# Corrupted JSON files
try:
    with open(scores_path, 'r') as f:
        scores = json.load(f)
except json.JSONDecodeError as e:
    raise ValueError(f"Corrupted scores.json: {e}")

# Invalid pose data format
poses = np.load(pose_path)
if poses.shape[1:] != (17, 2):
    raise ValueError(f"Invalid pose format: {poses.shape}, expected (T, 17, 2)")
```

### 10.5 Logging and Monitoring

**Pipeline Logger Integration**:
```python
from pipeline_logger import PipelineLogger

logger = PipelineLogger(verbose=True)
logger.header("AR-Based Kabaddi Ghost Trainer - Pipeline Execution")
logger.log_stage_start(1, 4, "Pose Extraction")
logger.log_error_detailed("Pipeline execution", e, video_path)
logger.success("Pipeline completed successfully")
```

**Django Logging Configuration**:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'kabaddi_backend.log',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'api': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

**Monitoring Metrics**:
- Session creation rate
- Pipeline success/failure rate
- Average processing time per stage
- File storage usage
- API response times
- Error frequency by type

---

This completes Part 1 of the comprehensive system documentation. The documentation covers the core system architecture, user flow, backend components, pipeline integration, database design, API specifications, file structure, configuration management, and error handling.

Part 2 will continue with detailed code analysis, deployment procedures, testing strategies, performance optimization, security considerations, and maintenance procedures.