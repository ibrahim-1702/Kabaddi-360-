# AR-Based Kabaddi Ghost Trainer - Complete System Documentation (Part 3)

## Table of Contents (Part 3)

17. [Testing Strategy](#testing-strategy)
18. [Deployment Procedures](#deployment-procedures)
19. [Maintenance and Monitoring](#maintenance-and-monitoring)
20. [Troubleshooting Guide](#troubleshooting-guide)
21. [Future Enhancements](#future-enhancements)
22. [Development Guidelines](#development-guidelines)
23. [API Integration Guide](#api-integration-guide)
24. [System Limitations](#system-limitations)

---

## 17. Testing Strategy

### 17.1 Testing Architecture

**Testing Pyramid Structure**:
```
                    ┌─────────────────┐
                    │   E2E Tests     │  ← Full system integration
                    │   (Mobile App)  │
                    └─────────────────┘
                  ┌───────────────────────┐
                  │   Integration Tests   │  ← API + Pipeline
                  │   (Backend + ML)      │
                  └───────────────────────┘
              ┌─────────────────────────────────┐
              │        Unit Tests               │  ← Individual components
              │  (Models, Views, Pipeline)      │
              └─────────────────────────────────┘
```

### 17.2 Unit Testing Implementation

**Django Model Tests**:
```python
# tests/test_models.py
import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError
from api.models import Tutorial, UserSession, RawVideo, AnalyticalResults

class TutorialModelTest(TestCase):
    def setUp(self):
        self.tutorial = Tutorial.objects.create(
            name='test_tutorial',
            description='Test tutorial description',
            expert_pose_path='expert_poses/test.npy',
            is_active=True
        )
    
    def test_tutorial_creation(self):
        """Test tutorial model creation and fields"""
        self.assertIsInstance(self.tutorial.id, uuid.UUID)
        self.assertEqual(self.tutorial.name, 'test_tutorial')
        self.assertTrue(self.tutorial.is_active)
        self.assertIsNotNone(self.tutorial.created_at)
    
    def test_tutorial_str_representation(self):
        """Test string representation"""
        self.assertEqual(str(self.tutorial), 'test_tutorial')
    
    def test_unique_name_constraint(self):
        """Test unique constraint on tutorial name"""
        with self.assertRaises(Exception):
            Tutorial.objects.create(
                name='test_tutorial',  # Duplicate name
                description='Another description',
                expert_pose_path='expert_poses/test2.npy'
            )

class UserSessionModelTest(TestCase):
    def setUp(self):
        self.tutorial = Tutorial.objects.create(
            name='test_tutorial',
            description='Test description',
            expert_pose_path='expert_poses/test.npy'
        )
        self.session = UserSession.objects.create(tutorial=self.tutorial)
    
    def test_session_creation(self):
        """Test session creation with default values"""
        self.assertEqual(self.session.status, 'created')
        self.assertEqual(self.session.tutorial, self.tutorial)
        self.assertIsNone(self.session.error_message)
    
    def test_status_choices(self):
        """Test valid status transitions"""
        valid_statuses = [
            'created', 'video_uploaded', 'pose_extracted',
            'level1_complete', 'level2_complete', 'level3_complete',
            'scoring_complete', 'feedback_generated', 'failed'
        ]
        
        for status in valid_statuses:
            self.session.status = status
            self.session.save()
            self.session.refresh_from_db()
            self.assertEqual(self.session.status, status)
    
    def test_session_cascade_delete(self):
        """Test cascade deletion when tutorial is deleted"""
        session_id = self.session.id
        self.tutorial.delete()
        
        with self.assertRaises(UserSession.DoesNotExist):
            UserSession.objects.get(id=session_id)

class AnalyticalResultsModelTest(TestCase):
    def setUp(self):
        self.tutorial = Tutorial.objects.create(
            name='test_tutorial',
            description='Test description',
            expert_pose_path='expert_poses/test.npy'
        )
        self.session = UserSession.objects.create(tutorial=self.tutorial)
    
    def test_mandatory_fields(self):
        """Test that both scores and error_metrics paths are required"""
        # Should succeed with both fields
        results = AnalyticalResults.objects.create(
            user_session=self.session,
            scores_json_path='results/test/scores.json',
            error_metrics_json_path='results/test/error_metrics.json'
        )
        self.assertIsNotNone(results.completed_at)
        
        # Test field requirements at database level would require
        # database constraints or model validation
    
    def test_one_to_one_relationship(self):
        """Test one-to-one relationship with UserSession"""
        AnalyticalResults.objects.create(
            user_session=self.session,
            scores_json_path='results/test/scores.json',
            error_metrics_json_path='results/test/error_metrics.json'
        )
        
        # Should raise error for duplicate results
        with self.assertRaises(Exception):
            AnalyticalResults.objects.create(
                user_session=self.session,
                scores_json_path='results/test2/scores.json',
                error_metrics_json_path='results/test2/error_metrics.json'
            )
```

**API View Tests**:
```python
# tests/test_views.py
import json
import tempfile
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from api.models import Tutorial, UserSession

class TutorialViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.tutorial = Tutorial.objects.create(
            name='hand_touch',
            description='Hand touch movement',
            expert_pose_path='expert_poses/hand_touch.npy',
            is_active=True
        )
        self.inactive_tutorial = Tutorial.objects.create(
            name='inactive_tutorial',
            description='Inactive tutorial',
            expert_pose_path='expert_poses/inactive.npy',
            is_active=False
        )
    
    def test_tutorial_list_view(self):
        """Test tutorial list endpoint"""
        response = self.client.get(reverse('tutorial_list'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('tutorials', data)
        self.assertEqual(len(data['tutorials']), 1)  # Only active tutorials
        
        tutorial_data = data['tutorials'][0]
        self.assertEqual(tutorial_data['name'], 'hand_touch')
        self.assertEqual(tutorial_data['description'], 'Hand touch movement')
    
    def test_tutorial_list_excludes_inactive(self):
        """Test that inactive tutorials are excluded"""
        response = self.client.get(reverse('tutorial_list'))
        data = json.loads(response.content)
        
        tutorial_names = [t['name'] for t in data['tutorials']]
        self.assertNotIn('inactive_tutorial', tutorial_names)

class SessionViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.tutorial = Tutorial.objects.create(
            name='test_tutorial',
            description='Test description',
            expert_pose_path='expert_poses/test.npy'
        )
    
    def test_session_start_success(self):
        """Test successful session creation"""
        data = {'tutorial_id': str(self.tutorial.id)}
        response = self.client.post(
            reverse('session_start'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        
        self.assertIn('session_id', response_data)
        self.assertEqual(response_data['tutorial'], 'test_tutorial')
        self.assertEqual(response_data['status'], 'created')
        
        # Verify session was created in database
        session = UserSession.objects.get(id=response_data['session_id'])
        self.assertEqual(session.tutorial, self.tutorial)
    
    def test_session_start_missing_tutorial_id(self):
        """Test session creation with missing tutorial_id"""
        response = self.client.post(
            reverse('session_start'),
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'tutorial_id required')
    
    def test_session_start_invalid_tutorial_id(self):
        """Test session creation with invalid tutorial_id"""
        invalid_uuid = '00000000-0000-0000-0000-000000000000'
        data = {'tutorial_id': invalid_uuid}
        
        response = self.client.post(
            reverse('session_start'),
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Invalid tutorial_id')
    
    def test_video_upload_success(self):
        """Test successful video upload"""
        session = UserSession.objects.create(tutorial=self.tutorial)
        
        # Create mock video file
        video_content = b'fake video content'
        video_file = SimpleUploadedFile(
            'test_video.mp4',
            video_content,
            content_type='video/mp4'
        )
        
        response = self.client.post(
            reverse('video_upload', kwargs={'session_id': session.id}),
            {'video': video_file}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['session_id'], str(session.id))
        self.assertEqual(data['status'], 'video_uploaded')
        self.assertEqual(data['file_size'], len(video_content))
        
        # Verify session status updated
        session.refresh_from_db()
        self.assertEqual(session.status, 'video_uploaded')
    
    def test_video_upload_file_too_large(self):
        """Test video upload with file size exceeding limit"""
        session = UserSession.objects.create(tutorial=self.tutorial)
        
        # Create large mock file (over 100MB limit)
        large_content = b'x' * (101 * 1024 * 1024)
        large_file = SimpleUploadedFile(
            'large_video.mp4',
            large_content,
            content_type='video/mp4'
        )
        
        response = self.client.post(
            reverse('video_upload', kwargs={'session_id': session.id}),
            {'video': large_file}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'File too large')
    
    def test_session_status_view(self):
        """Test session status endpoint"""
        session = UserSession.objects.create(
            tutorial=self.tutorial,
            status='level1_complete'
        )
        
        response = self.client.get(
            reverse('session_status', kwargs={'session_id': session.id})
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['session_id'], str(session.id))
        self.assertEqual(data['status'], 'level1_complete')
        self.assertIsNotNone(data['updated_at'])
```

**Pipeline Component Tests**:
```python
# tests/test_pipeline.py
import numpy as np
from django.test import TestCase
from temporal_alignment import temporal_alignment, extract_pelvis_trajectory
from error_localization import compute_error_metrics

class TemporalAlignmentTest(TestCase):
    def setUp(self):
        # Create test pose sequences
        self.user_poses = np.random.randn(100, 17, 2)
        self.expert_poses = np.random.randn(120, 17, 2)
        
        # Set hip positions (joints 11 and 12)
        self.user_poses[:, 11, :] = np.random.randn(100, 2) * 0.1 + [0.4, 0.6]
        self.user_poses[:, 12, :] = np.random.randn(100, 2) * 0.1 + [0.6, 0.6]
        
        self.expert_poses[:, 11, :] = np.random.randn(120, 2) * 0.1 + [0.4, 0.6]
        self.expert_poses[:, 12, :] = np.random.randn(120, 2) * 0.1 + [0.6, 0.6]
    
    def test_pelvis_trajectory_extraction(self):
        """Test pelvis trajectory extraction from poses"""
        pelvis = extract_pelvis_trajectory(self.user_poses)
        
        self.assertEqual(pelvis.shape, (100, 2))
        
        # Verify pelvis is midpoint of hips
        expected_pelvis = (self.user_poses[:, 11, :] + self.user_poses[:, 12, :]) / 2.0
        np.testing.assert_array_almost_equal(pelvis, expected_pelvis)
    
    def test_temporal_alignment_output_format(self):
        """Test DTW alignment output format"""
        user_indices, expert_indices = temporal_alignment(
            self.user_poses, self.expert_poses
        )
        
        self.assertIsInstance(user_indices, list)
        self.assertIsInstance(expert_indices, list)
        self.assertEqual(len(user_indices), len(expert_indices))
        
        # Check index ranges
        self.assertTrue(all(0 <= idx < 100 for idx in user_indices))
        self.assertTrue(all(0 <= idx < 120 for idx in expert_indices))
    
    def test_temporal_alignment_monotonicity(self):
        """Test that alignment indices are monotonic"""
        user_indices, expert_indices = temporal_alignment(
            self.user_poses, self.expert_poses
        )
        
        # Indices should be non-decreasing (monotonic)
        for i in range(1, len(user_indices)):
            self.assertGreaterEqual(user_indices[i], user_indices[i-1])
            self.assertGreaterEqual(expert_indices[i], expert_indices[i-1])

class ErrorLocalizationTest(TestCase):
    def setUp(self):
        # Create aligned test sequences
        self.aligned_user = np.random.randn(150, 17, 2)
        self.aligned_expert = np.random.randn(150, 17, 2)
        
        # Add some known errors for testing
        self.aligned_user[:, 5, :] += 0.2  # Left shoulder offset
        self.aligned_user[:, 9, :] += 0.1  # Left wrist offset
    
    def test_error_metrics_output_structure(self):
        """Test error metrics output structure"""
        metrics = compute_error_metrics(
            self.aligned_user, self.aligned_expert
        )
        
        # Check required keys
        required_keys = ['frame_errors', 'joint_aggregates', 'metadata']
        for key in required_keys:
            self.assertIn(key, metrics)
        
        # Check frame_errors structure
        frame_errors = metrics['frame_errors']
        self.assertEqual(frame_errors['shape'], [150, 17])
        self.assertEqual(len(frame_errors['data']), 150)
        self.assertEqual(len(frame_errors['data'][0]), 17)
        
        # Check joint_aggregates structure
        joint_aggregates = metrics['joint_aggregates']
        self.assertEqual(len(joint_aggregates), 17)
        
        for joint_name, stats in joint_aggregates.items():
            self.assertIn('mean', stats)
            self.assertIn('max', stats)
            self.assertIn('std', stats)
    
    def test_error_metrics_temporal_phases(self):
        """Test temporal phase analysis"""
        metrics = compute_error_metrics(
            self.aligned_user, self.aligned_expert,
            enable_temporal_phases=True
        )
        
        self.assertIn('temporal_phases', metrics)
        
        phases = metrics['temporal_phases']
        expected_phases = ['early', 'mid', 'late']
        
        for phase in expected_phases:
            self.assertIn(phase, phases)
            self.assertEqual(len(phases[phase]), 17)  # All joints
    
    def test_error_computation_accuracy(self):
        """Test error computation accuracy"""
        # Create simple test case with known errors
        user_poses = np.zeros((10, 17, 2))
        expert_poses = np.zeros((10, 17, 2))
        
        # Add known error to joint 0 (nose)
        user_poses[:, 0, 0] = 1.0  # x-coordinate offset of 1.0
        
        metrics = compute_error_metrics(user_poses, expert_poses)
        
        # Check that nose has error of 1.0
        nose_stats = metrics['joint_aggregates']['nose']
        self.assertAlmostEqual(nose_stats['mean'], 1.0, places=5)
        self.assertAlmostEqual(nose_stats['max'], 1.0, places=5)
        self.assertAlmostEqual(nose_stats['std'], 0.0, places=5)
```

### 17.3 Integration Testing

**API Integration Tests**:
```python
# tests/test_integration.py
import os
import json
import tempfile
import numpy as np
from django.test import TestCase, TransactionTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from api.models import Tutorial, UserSession, AnalyticalResults
from api.tasks import process_multi_level_pipeline

class PipelineIntegrationTest(TransactionTestCase):
    def setUp(self):
        self.tutorial = Tutorial.objects.create(
            name='test_tutorial',
            description='Test description',
            expert_pose_path='expert_poses/test.npy'
        )
        
        # Create temporary expert pose file
        self.temp_dir = tempfile.mkdtemp()
        self.expert_pose_path = os.path.join(self.temp_dir, 'test.npy')
        expert_poses = np.random.randn(100, 17, 2)
        np.save(self.expert_pose_path, expert_poses)
    
    def tearDown(self):
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('api.tasks.subprocess.run')
    @patch('api.tasks.settings.MEDIA_ROOT', new_callable=lambda: tempfile.mkdtemp())
    def test_complete_pipeline_execution(self, mock_media_root, mock_subprocess):
        """Test complete pipeline execution flow"""
        # Setup mock subprocess responses
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout='Success',
            stderr=''
        )
        
        # Create session with uploaded video
        session = UserSession.objects.create(
            tutorial=self.tutorial,
            status='video_uploaded'
        )
        
        # Create mock video file
        video_path = os.path.join(mock_media_root, 'raw_videos', f'{session.id}.mp4')
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        with open(video_path, 'wb') as f:
            f.write(b'fake video content')
        
        # Create RawVideo record
        from api.models import RawVideo
        RawVideo.objects.create(
            user_session=session,
            file_path=video_path,
            file_size=100
        )
        
        # Create mock pipeline outputs
        results_dir = os.path.join(mock_media_root, 'results', str(session.id))
        os.makedirs(results_dir, exist_ok=True)
        
        scores_path = os.path.join(results_dir, 'scores.json')
        error_metrics_path = os.path.join(results_dir, 'error_metrics.json')
        
        with open(scores_path, 'w') as f:
            json.dump({'overall': 85.0, 'structural': 80.0, 'temporal': 90.0}, f)
        
        with open(error_metrics_path, 'w') as f:
            json.dump({
                'joint_aggregates': {'nose': {'mean': 0.1, 'max': 0.3, 'std': 0.05}},
                'frame_errors': {'shape': [100, 17], 'data': [[0.1] * 17] * 100}
            }, f)
        
        # Create mock pose file
        poses_dir = os.path.join(mock_media_root, 'poses')
        os.makedirs(poses_dir, exist_ok=True)
        pose_path = os.path.join(poses_dir, f'{session.id}.npy')
        user_poses = np.random.randn(100, 17, 2)
        np.save(pose_path, user_poses)
        
        # Execute pipeline
        with patch('api.tasks.settings.MEDIA_ROOT', mock_media_root):
            with patch('api.tasks.settings.EXTRACT_POSE_SCRIPT', '/fake/script.py'):
                with patch('api.tasks.settings.RUN_PIPELINE_SCRIPT', '/fake/pipeline.py'):
                    process_multi_level_pipeline(str(session.id))
        
        # Verify session status updated
        session.refresh_from_db()
        self.assertEqual(session.status, 'feedback_generated')
        
        # Verify AnalyticalResults created
        results = AnalyticalResults.objects.get(user_session=session)
        self.assertEqual(results.scores_json_path, scores_path)
        self.assertEqual(results.error_metrics_json_path, error_metrics_path)
        
        # Verify subprocess calls
        self.assertEqual(mock_subprocess.call_count, 2)  # Pose extraction + pipeline

class EndToEndAPITest(TestCase):
    def setUp(self):
        self.tutorial = Tutorial.objects.create(
            name='hand_touch',
            description='Hand touch movement',
            expert_pose_path='expert_poses/hand_touch.npy'
        )
    
    def test_complete_user_flow(self):
        """Test complete user flow from tutorial selection to results"""
        # Step 1: Get tutorials
        response = self.client.get('/api/tutorials/')
        self.assertEqual(response.status_code, 200)
        
        tutorials = json.loads(response.content)['tutorials']
        tutorial_id = tutorials[0]['id']
        
        # Step 2: Start session
        response = self.client.post(
            '/api/session/start/',
            data=json.dumps({'tutorial_id': tutorial_id}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        session_data = json.loads(response.content)
        session_id = session_data['session_id']
        
        # Step 3: Upload video
        video_file = SimpleUploadedFile(
            'test_video.mp4',
            b'fake video content',
            content_type='video/mp4'
        )
        
        response = self.client.post(
            f'/api/session/{session_id}/upload-video/',
            {'video': video_file}
        )
        self.assertEqual(response.status_code, 200)
        
        # Step 4: Check status
        response = self.client.get(f'/api/session/{session_id}/status/')
        self.assertEqual(response.status_code, 200)
        
        status_data = json.loads(response.content)
        self.assertEqual(status_data['status'], 'video_uploaded')
        
        # Step 5: Trigger assessment (would normally be async)
        response = self.client.post(f'/api/session/{session_id}/assess/')
        self.assertEqual(response.status_code, 200)
        
        # Verify session exists and has correct status
        session = UserSession.objects.get(id=session_id)
        self.assertEqual(session.status, 'pose_extracted')
```

### 17.4 Performance Testing

**Load Testing Configuration**:
```python
# tests/test_performance.py
import time
import threading
from django.test import TestCase
from django.test.utils import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

class PerformanceTest(TestCase):
    def setUp(self):
        from api.models import Tutorial
        self.tutorial = Tutorial.objects.create(
            name='perf_test',
            description='Performance test tutorial',
            expert_pose_path='expert_poses/perf_test.npy'
        )
    
    def test_concurrent_session_creation(self):
        """Test concurrent session creation performance"""
        num_threads = 10
        results = []
        
        def create_session():
            start_time = time.time()
            response = self.client.post(
                '/api/session/start/',
                data={'tutorial_id': str(self.tutorial.id)},
                content_type='application/json'
            )
            end_time = time.time()
            
            results.append({
                'status_code': response.status_code,
                'duration': end_time - start_time
            })
        
        # Create threads
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=create_session)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify all requests succeeded
        self.assertEqual(len(results), num_threads)
        for result in results:
            self.assertEqual(result['status_code'], 200)
        
        # Performance assertions
        avg_duration = sum(r['duration'] for r in results) / len(results)
        self.assertLess(avg_duration, 1.0)  # Average < 1 second
        self.assertLess(total_time, 5.0)    # Total < 5 seconds
    
    def test_large_video_upload_performance(self):
        """Test large video upload performance"""
        from api.models import UserSession
        
        session = UserSession.objects.create(tutorial=self.tutorial)
        
        # Create 50MB test file
        large_content = b'x' * (50 * 1024 * 1024)
        large_file = SimpleUploadedFile(
            'large_video.mp4',
            large_content,
            content_type='video/mp4'
        )
        
        start_time = time.time()
        response = self.client.post(
            f'/api/session/{session.id}/upload-video/',
            {'video': large_file}
        )
        upload_time = time.time() - start_time
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(upload_time, 30.0)  # Should complete within 30 seconds
```

---

## 18. Deployment Procedures

### 18.1 Development Environment Setup

**Local Development Setup**:
```bash
# Clone repository
git clone https://github.com/your-org/kabaddi-trainer.git
cd kabaddi-trainer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
cd kabaddi_backend
python manage.py migrate
python manage.py create_tutorials

# Create media directories
mkdir -p media/{raw_videos,poses,expert_poses,results}

# Copy expert pose files
cp ../level1_pose/raider_pose_level1.npy media/expert_poses/hand_touch.npy
cp ../level1_pose/raider_pose_level1.npy media/expert_poses/toe_touch.npy
cp ../level1_pose/raider_pose_level1.npy media/expert_poses/bonus.npy

# Run development server
python manage.py runserver
```

**Development Dependencies**:
```txt
# requirements-dev.txt
Django==4.2.7
numpy==1.24.3
opencv-python==4.8.1.78
ultralytics==8.0.196
mediapipe==0.10.7

# Development tools
pytest==7.4.3
pytest-django==4.5.2
black==23.9.1
flake8==6.1.0
coverage==7.3.2

# Optional: Async processing
celery==5.3.4
redis==5.0.1
```

### 18.2 Production Deployment

**Docker Configuration**:
```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create media directories
RUN mkdir -p media/{raw_videos,poses,expert_poses,results}

# Set environment variables
ENV DJANGO_SETTINGS_MODULE=kabaddi_backend.settings
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD ["sh", "-c", "python kabaddi_backend/manage.py migrate && python kabaddi_backend/manage.py runserver 0.0.0.0:8000"]
```

**Docker Compose Configuration**:
```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./media:/app/media
      - ./logs:/app/logs
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:password@db:5432/kabaddi_trainer
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=kabaddi_trainer
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  celery:
    build: .
    command: celery -A kabaddi_backend worker -l info
    volumes:
      - ./media:/app/media
      - ./logs:/app/logs
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:password@db:5432/kabaddi_trainer
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - ./media:/app/media
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
```

**Nginx Configuration**:
```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream django {
        server web:8000;
    }

    server {
        listen 80;
        server_name api.kabaddi-trainer.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.kabaddi-trainer.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        client_max_body_size 100M;

        location / {
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /media/ {
            alias /app/media/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

**Production Settings**:
```python
# kabaddi_backend/settings_production.py
import os
from .settings import *

DEBUG = False
ALLOWED_HOSTS = ['api.kabaddi-trainer.com', 'localhost']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ['DB_HOST'],
        'PORT': os.environ['DB_PORT'],
        'CONN_MAX_AGE': 600,
    }
}

# Celery Configuration
CELERY_BROKER_URL = os.environ['REDIS_URL']
CELERY_RESULT_BACKEND = os.environ['REDIS_URL']
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/django.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### 18.3 Deployment Scripts

**Deployment Script**:
```bash
#!/bin/bash
# deploy.sh

set -e

echo "Starting deployment..."

# Pull latest code
git pull origin main

# Build Docker images
docker-compose build

# Run database migrations
docker-compose run --rm web python kabaddi_backend/manage.py migrate

# Collect static files (if using static files)
docker-compose run --rm web python kabaddi_backend/manage.py collectstatic --noinput

# Restart services
docker-compose down
docker-compose up -d

# Wait for services to start
sleep 10

# Health check
curl -f http://localhost:8000/api/tutorials/ || exit 1

echo "Deployment completed successfully!"
```

**Database Backup Script**:
```bash
#!/bin/bash
# backup_db.sh

BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="kabaddi_trainer_${TIMESTAMP}.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
docker-compose exec -T db pg_dump -U user kabaddi_trainer > "$BACKUP_DIR/$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_DIR/$BACKUP_FILE"

# Keep only last 7 days of backups
find $BACKUP_DIR -name "kabaddi_trainer_*.sql.gz" -mtime +7 -delete

echo "Database backup completed: $BACKUP_FILE.gz"
```

### 18.4 CI/CD Pipeline

**GitHub Actions Workflow**:
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_kabaddi_trainer
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_kabaddi_trainer
      run: |
        cd kabaddi_backend
        python manage.py test
    
    - name: Run linting
      run: |
        flake8 kabaddi_backend/
        black --check kabaddi_backend/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to server
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /opt/kabaddi-trainer
          git pull origin main
          ./deploy.sh
```

---

## 19. Maintenance and Monitoring

### 19.1 System Monitoring

**Health Check Endpoints**:
```python
# api/health.py
import os
import json
from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.conf import settings

class HealthCheckView(View):
    def get(self, request):
        """Comprehensive health check endpoint"""
        health_status = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'checks': {}
        }
        
        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status['checks']['database'] = 'healthy'
        except Exception as e:
            health_status['checks']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # File system check
        try:
            media_root = settings.MEDIA_ROOT
            for directory in ['raw_videos', 'poses', 'expert_poses', 'results']:
                dir_path = os.path.join(media_root, directory)
                if not os.path.exists(dir_path):
                    raise Exception(f'Directory {directory} does not exist')
            health_status['checks']['filesystem'] = 'healthy'
        except Exception as e:
            health_status['checks']['filesystem'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Pipeline scripts check
        try:
            if not os.path.exists(settings.EXTRACT_POSE_SCRIPT):
                raise Exception('Pose extraction script not found')
            if not os.path.exists(settings.RUN_PIPELINE_SCRIPT):
                raise Exception('Pipeline script not found')
            health_status['checks']['pipeline'] = 'healthy'
        except Exception as e:
            health_status['checks']['pipeline'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Disk space check
        try:
            statvfs = os.statvfs(settings.MEDIA_ROOT)
            free_space = statvfs.f_frsize * statvfs.f_bavail
            total_space = statvfs.f_frsize * statvfs.f_blocks
            usage_percent = ((total_space - free_space) / total_space) * 100
            
            if usage_percent > 90:
                health_status['checks']['disk_space'] = f'warning: {usage_percent:.1f}% used'
            else:
                health_status['checks']['disk_space'] = f'healthy: {usage_percent:.1f}% used'
        except Exception as e:
            health_status['checks']['disk_space'] = f'error: {str(e)}'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return JsonResponse(health_status, status=status_code)

class MetricsView(View):
    def get(self, request):
        """System metrics endpoint"""
        from api.models import UserSession, Tutorial
        
        metrics = {
            'sessions': {
                'total': UserSession.objects.count(),
                'active': UserSession.objects.exclude(status='failed').count(),
                'completed': UserSession.objects.filter(status='feedback_generated').count(),
                'failed': UserSession.objects.filter(status='failed').count(),
            },
            'tutorials': {
                'total': Tutorial.objects.count(),
                'active': Tutorial.objects.filter(is_active=True).count(),
            }
        }
        
        # Add status breakdown
        status_counts = {}
        for status_choice in UserSession.STATUS_CHOICES:
            status = status_choice[0]
            count = UserSession.objects.filter(status=status).count()
            status_counts[status] = count
        
        metrics['session_status'] = status_counts
        
        return JsonResponse(metrics)
```

**Monitoring Configuration**:
```python
# monitoring/prometheus.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from django.http import HttpResponse

# Metrics
REQUEST_COUNT = Counter('django_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('django_request_duration_seconds', 'Request duration')
ACTIVE_SESSIONS = Gauge('kabaddi_active_sessions', 'Number of active sessions')
PIPELINE_DURATION = Histogram('kabaddi_pipeline_duration_seconds', 'Pipeline execution time')

def metrics_view(request):
    """Prometheus metrics endpoint"""
    return HttpResponse(generate_latest(), content_type='text/plain')

# Middleware for request metrics
class PrometheusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        REQUEST_DURATION.observe(duration)
        REQUEST_COUNT.labels(method=request.method, endpoint=request.path).inc()
        
        return response
```

### 19.2 Log Management

**Structured Logging Configuration**:
```python
# logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
        
        return json.dumps(log_entry)

# Usage in views
import logging
logger = logging.getLogger(__name__)

def upload_video(request, session_id):
    logger.info(
        "Video upload started",
        extra={'session_id': session_id, 'file_size': request.FILES['video'].size}
    )
    
    # Process upload...
    
    logger.info(
        "Video upload completed",
        extra={'session_id': session_id, 'duration': processing_time}
    )
```

**Log Aggregation with ELK Stack**:
```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
      - ./logs:/logs
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

### 19.3 Performance Monitoring

**Database Query Monitoring**:
```python
# monitoring/db_monitor.py
import time
from django.db import connection
from django.conf import settings

class DatabaseMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.DEBUG:
            initial_queries = len(connection.queries)
        
        start_time = time.time()
        response = self.get_response(request)
        end_time = time.time()
        
        if settings.DEBUG:
            query_count = len(connection.queries) - initial_queries
            duration = end_time - start_time
            
            if query_count > 10:  # Alert on excessive queries
                logger.warning(
                    f"High query count: {query_count} queries in {duration:.2f}s",
                    extra={
                        'path': request.path,
                        'query_count': query_count,
                        'duration': duration
                    }
                )
        
        return response
```

**Pipeline Performance Tracking**:
```python
# api/performance.py
import time
from contextlib import contextmanager
from django.core.cache import cache

@contextmanager
def track_pipeline_stage(stage_name, session_id):
    """Context manager to track pipeline stage performance"""
    start_time = time.time()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        
        # Store performance metrics
        cache_key = f"pipeline_perf_{session_id}_{stage_name}"
        cache.set(cache_key, duration, timeout=3600)
        
        # Log performance
        logger.info(
            f"Pipeline stage completed: {stage_name}",
            extra={
                'session_id': session_id,
                'stage': stage_name,
                'duration': duration
            }
        )

# Usage in tasks.py
def process_multi_level_pipeline(session_id):
    with track_pipeline_stage('pose_extraction', session_id):
        # Pose extraction code...
        pass
    
    with track_pipeline_stage('temporal_alignment', session_id):
        # Temporal alignment code...
        pass
```

### 19.4 Automated Maintenance Tasks

**Cleanup Scripts**:
```python
# management/commands/cleanup_old_files.py
import os
import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import UserSession

class Command(BaseCommand):
    help = 'Clean up old files and sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete files older than N days'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = datetime.now() - timedelta(days=days)
        
        self.stdout.write(f"Cleaning up files older than {days} days...")
        
        # Find old sessions
        old_sessions = UserSession.objects.filter(created_at__lt=cutoff_date)
        
        deleted_files = 0
        freed_space = 0
        
        for session in old_sessions:
            # Clean up video files
            try:
                video = session.rawvideo
                if os.path.exists(video.file_path):
                    file_size = os.path.getsize(video.file_path)
                    if not dry_run:
                        os.remove(video.file_path)
                    deleted_files += 1
                    freed_space += file_size
            except:
                pass
            
            # Clean up pose files
            try:
                pose = session.poseartifact
                if os.path.exists(pose.pose_level1_path):
                    file_size = os.path.getsize(pose.pose_level1_path)
                    if not dry_run:
                        os.remove(pose.pose_level1_path)
                    deleted_files += 1
                    freed_space += file_size
            except:
                pass
            
            # Clean up results directory
            results_dir = os.path.join(
                settings.MEDIA_ROOT, 'results', str(session.id)
            )
            if os.path.exists(results_dir):
                for root, dirs, files in os.walk(results_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        if not dry_run:
                            os.remove(file_path)
                        deleted_files += 1
                        freed_space += file_size
                
                if not dry_run:
                    os.rmdir(results_dir)
            
            # Delete session from database
            if not dry_run:
                session.delete()
        
        freed_mb = freed_space / (1024 * 1024)
        
        if dry_run:
            self.stdout.write(
                f"Would delete {deleted_files} files, "
                f"freeing {freed_mb:.2f} MB"
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {deleted_files} files, "
                    f"freed {freed_mb:.2f} MB"
                )
            )
```

**Database Maintenance**:
```python
# management/commands/db_maintenance.py
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Perform database maintenance tasks'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Analyze tables for query optimization
            cursor.execute("ANALYZE;")
            
            # Vacuum database (PostgreSQL)
            cursor.execute("VACUUM;")
            
            # Update statistics
            cursor.execute("UPDATE pg_stat_user_tables SET n_tup_ins = 0;")
        
        self.stdout.write(
            self.style.SUCCESS('Database maintenance completed')
        )
```

---

## 20. Troubleshooting Guide

### 20.1 Common Issues and Solutions

**Issue: Pipeline Execution Fails**
```
Error: Pipeline execution failed: FileNotFoundError: Expert pose not found
```

**Diagnosis Steps**:
1. Check expert pose file exists:
   ```bash
   ls -la media/expert_poses/
   ```

2. Verify tutorial configuration:
   ```python
   from api.models import Tutorial
   tutorials = Tutorial.objects.all()
   for t in tutorials:
       print(f"{t.name}: {t.expert_pose_path}")
   ```

3. Check file permissions:
   ```bash
   ls -la media/expert_poses/hand_touch.npy
   ```

**Solutions**:
- Copy expert pose files to correct location
- Update tutorial expert_pose_path in database
- Fix file permissions: `chmod 644 media/expert_poses/*.npy`

**Issue: Video Upload Fails**
```
Error: File too large
```

**Diagnosis Steps**:
1. Check file size limit in settings
2. Verify nginx client_max_body_size
3. Check available disk space

**Solutions**:
```python
# Increase file size limit in settings.py
MAX_VIDEO_SIZE = 200 * 1024 * 1024  # 200MB

# Update nginx configuration
client_max_body_size 200M;
```

**Issue: Pose Extraction Script Not Found**
```
Error: can't open file 'pose_extract_cli.py': No such file or directory
```

**Diagnosis Steps**:
1. Check script path in settings:
   ```python
   from django.conf import settings
   print(settings.EXTRACT_POSE_SCRIPT)
   print(settings.EXTRACT_POSE_SCRIPT.exists())
   ```

2. Verify script permissions:
   ```bash
   ls -la level1_pose/pose_extract_cli.py
   ```

**Solutions**:
- Ensure script exists at configured path
- Make script executable: `chmod +x level1_pose/pose_extract_cli.py`
- Update EXTRACT_POSE_SCRIPT path in settings

### 20.2 Performance Issues

**Issue: Slow Pipeline Execution**

**Diagnosis**:
```python
# Add timing to pipeline stages
import time

def timed_pipeline_stage(stage_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            print(f"{stage_name}: {duration:.2f}s")
            return result
        return wrapper
    return decorator

@timed_pipeline_stage("Pose Extraction")
def extract_poses():
    # Implementation
    pass
```

**Solutions**:
- Use GPU acceleration for pose estimation
- Reduce video resolution before processing
- Implement frame skipping for long videos
- Use parallel processing for batch operations

**Issue: High Memory Usage**

**Diagnosis**:
```python
import psutil
import os

def log_memory_usage(stage):
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"{stage}: {memory_mb:.2f} MB")

# Use throughout pipeline
log_memory_usage("Start")
# ... processing ...
log_memory_usage("After pose extraction")
```

**Solutions**:
- Process video in chunks instead of loading entirely
- Use generators for large data processing
- Clear variables after use: `del large_array`
- Implement memory limits in Docker containers

### 20.3 Database Issues

**Issue: Database Connection Errors**

**Diagnosis**:
```python
from django.db import connection
from django.core.management.color import no_style

def test_db_connection():
    try:
        connection.ensure_connection()
        print("Database connection: OK")
    except Exception as e:
        print(f"Database connection failed: {e}")

def check_db_tables():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print(f"Tables: {[t[0] for t in tables]}")
```

**Solutions**:
- Check database server status
- Verify connection parameters
- Run migrations: `python manage.py migrate`
- Check database user permissions

**Issue: Migration Conflicts**

**Diagnosis**:
```bash
python manage.py showmigrations
python manage.py migrate --plan
```

**Solutions**:
```bash
# Reset migrations (development only)
python manage.py migrate api zero
rm api/migrations/0*.py
python manage.py makemigrations api
python manage.py migrate

# Fake migration (if schema already correct)
python manage.py migrate --fake api 0001
```

### 20.4 API Issues

**Issue: CSRF Token Errors**

**Diagnosis**:
- Check if CSRF middleware is enabled
- Verify CSRF exemption on API endpoints
- Check request headers

**Solutions**:
```python
# Ensure CSRF exemption for API views
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def api_view(request):
    # Implementation
    pass

# Or implement proper API authentication
class APIKeyAuthentication:
    def authenticate(self, request):
        # Implementation
        pass
```

**Issue: JSON Parsing Errors**

**Diagnosis**:
```python
import json

def debug_json_request(request):
    try:
        data = json.loads(request.body)
        print(f"Parsed JSON: {data}")
        return data
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Request body: {request.body}")
        raise
```

**Solutions**:
- Validate JSON format before parsing
- Add proper error handling for malformed JSON
- Log request body for debugging

### 20.5 Deployment Issues

**Issue: Docker Container Fails to Start**

**Diagnosis**:
```bash
# Check container logs
docker-compose logs web

# Check container status
docker-compose ps

# Debug container interactively
docker-compose run --rm web bash
```

**Solutions**:
- Check Dockerfile syntax
- Verify all dependencies are installed
- Ensure proper file permissions
- Check environment variables

**Issue: Static Files Not Served**

**Diagnosis**:
```python
# Check static files configuration
from django.conf import settings
print(f"STATIC_URL: {settings.STATIC_URL}")
print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
```

**Solutions**:
```bash
# Collect static files
python manage.py collectstatic --noinput

# Configure nginx to serve static files
location /static/ {
    alias /app/static/;
}
```

---

This completes Part 3 of the comprehensive system documentation. The documentation now covers testing strategies, deployment procedures, maintenance and monitoring, troubleshooting guides, and provides a complete reference for the AR-Based Kabaddi Ghost Trainer system.

The three-part documentation provides over 50 pages of detailed technical information covering every aspect of the system from architecture and implementation to deployment and maintenance.