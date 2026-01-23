# Testing and Validation Document - AR-Based Kabaddi Ghost Trainer

## Document Information
- **Version**: 1.0
- **Date**: 2024-01-15
- **Author**: QA Team
- **Classification**: Technical Specification

---

## Table of Contents

1. [Testing Strategy Overview](#testing-strategy-overview)
2. [Unit Testing Framework](#unit-testing-framework)
3. [Integration Testing](#integration-testing)
4. [Performance Testing](#performance-testing)
5. [API Testing](#api-testing)
6. [Pipeline Validation](#pipeline-validation)
7. [Test Data Management](#test-data-management)
8. [Continuous Integration](#continuous-integration)

---

## 1. Testing Strategy Overview

### 1.1 Testing Pyramid

```
                    ┌─────────────────┐
                    │   E2E Tests     │  ← 10% (Mobile + Backend)
                    │   (Slow)        │
                    └─────────────────┘
                  ┌───────────────────────┐
                  │   Integration Tests   │  ← 20% (API + Pipeline)
                  │   (Medium)            │
                  └───────────────────────┘
              ┌─────────────────────────────────┐
              │        Unit Tests               │  ← 70% (Individual functions)
              │        (Fast)                   │
              └─────────────────────────────────┘
```

### 1.2 Test Categories

| Category | Coverage | Tools | Execution |
|----------|----------|-------|-----------|
| **Unit Tests** | Individual functions/methods | pytest, unittest | Local + CI |
| **Integration Tests** | Component interactions | pytest, requests | CI + Staging |
| **Performance Tests** | Speed, memory, throughput | pytest-benchmark | CI + Production |
| **API Tests** | REST endpoints | pytest, httpx | CI + Staging |
| **Pipeline Tests** | Algorithm accuracy | pytest, numpy.testing | CI + Validation |
| **E2E Tests** | Complete user flows | Selenium, Appium | Staging + Production |

### 1.3 Quality Gates

**Code Coverage Requirements**:
- Unit Tests: ≥ 90%
- Integration Tests: ≥ 80%
- Critical Path Coverage: 100%

**Performance Requirements**:
- API Response Time: < 500ms (95th percentile)
- Pipeline Execution: < 5 minutes
- Memory Usage: < 2GB peak

---

## 2. Unit Testing Framework

### 2.1 Test Structure

```python
# test_temporal_alignment.py
import pytest
import numpy as np
from temporal_alignment import temporal_alignment, extract_pelvis_trajectory

class TestTemporalAlignment:
    """Test suite for temporal alignment algorithms."""
    
    def setup_method(self):
        """Setup test data before each test."""
        # Create deterministic test poses
        self.user_poses = self.create_test_poses(frames=100, movement='linear')
        self.expert_poses = self.create_test_poses(frames=120, movement='linear')
        
    def create_test_poses(self, frames: int, movement: str) -> np.ndarray:
        """Create synthetic pose data for testing."""
        poses = np.zeros((frames, 17, 2))
        
        if movement == 'linear':
            # Linear movement pattern
            for t in range(frames):
                progress = t / frames
                poses[t, :, 0] = 0.3 + 0.4 * progress  # x movement
                poses[t, :, 1] = 0.5 + 0.2 * np.sin(2 * np.pi * progress)  # y oscillation
        
        # Set hip positions (joints 11, 12)
        poses[:, 11, :] = poses[:, 0, :] + [-0.1, 0.3]  # left hip
        poses[:, 12, :] = poses[:, 0, :] + [0.1, 0.3]   # right hip
        
        return poses
    
    def test_pelvis_extraction(self):
        """Test pelvis trajectory extraction."""
        pelvis = extract_pelvis_trajectory(self.user_poses)
        
        # Check output shape
        assert pelvis.shape == (100, 2)
        
        # Verify pelvis is midpoint of hips
        expected_pelvis = (self.user_poses[:, 11, :] + self.user_poses[:, 12, :]) / 2.0
        np.testing.assert_array_almost_equal(pelvis, expected_pelvis)
    
    def test_alignment_output_format(self):
        """Test DTW alignment output format."""
        user_indices, expert_indices = temporal_alignment(self.user_poses, self.expert_poses)
        
        # Check output types
        assert isinstance(user_indices, list)
        assert isinstance(expert_indices, list)
        assert len(user_indices) == len(expert_indices)
        
        # Check index ranges
        assert all(0 <= idx < 100 for idx in user_indices)
        assert all(0 <= idx < 120 for idx in expert_indices)
    
    def test_alignment_monotonicity(self):
        """Test that alignment indices are monotonic."""
        user_indices, expert_indices = temporal_alignment(self.user_poses, self.expert_poses)
        
        # Indices should be non-decreasing
        for i in range(1, len(user_indices)):
            assert user_indices[i] >= user_indices[i-1]
            assert expert_indices[i] >= expert_indices[i-1]
    
    def test_identical_sequences(self):
        """Test alignment of identical sequences."""
        user_indices, expert_indices = temporal_alignment(self.user_poses, self.user_poses)
        
        # Should produce diagonal alignment
        expected_indices = list(range(100))
        assert user_indices == expected_indices
        assert expert_indices == expected_indices
    
    @pytest.mark.parametrize("user_frames,expert_frames", [
        (50, 75), (100, 80), (150, 200)
    ])
    def test_different_sequence_lengths(self, user_frames, expert_frames):
        """Test alignment with different sequence lengths."""
        user_poses = self.create_test_poses(user_frames, 'linear')
        expert_poses = self.create_test_poses(expert_frames, 'linear')
        
        user_indices, expert_indices = temporal_alignment(user_poses, expert_poses)
        
        # Check alignment path properties
        assert len(user_indices) > 0
        assert len(expert_indices) > 0
        assert user_indices[0] == 0
        assert expert_indices[0] == 0
        assert user_indices[-1] == user_frames - 1
        assert expert_indices[-1] == expert_frames - 1
```

### 2.2 Error Localization Tests

```python
# test_error_localization.py
import pytest
import numpy as np
from error_localization import compute_error_metrics, get_joint_ranking

class TestErrorLocalization:
    """Test suite for error localization algorithms."""
    
    def setup_method(self):
        """Setup test data."""
        # Create aligned test sequences with known errors
        self.T = 150
        self.aligned_user = np.random.randn(self.T, 17, 2) * 0.1
        self.aligned_expert = np.random.randn(self.T, 17, 2) * 0.1
        
        # Add known errors to specific joints
        self.aligned_user[:, 5, :] += 0.2  # Left shoulder offset
        self.aligned_user[:, 9, :] += 0.1  # Left wrist offset
    
    def test_error_metrics_structure(self):
        """Test error metrics output structure."""
        metrics = compute_error_metrics(self.aligned_user, self.aligned_expert)
        
        # Check required keys
        required_keys = ['frame_errors', 'joint_aggregates', 'metadata']
        for key in required_keys:
            assert key in metrics
        
        # Check frame_errors structure
        frame_errors = metrics['frame_errors']
        assert frame_errors['shape'] == [150, 17]
        assert len(frame_errors['data']) == 150
        assert len(frame_errors['data'][0]) == 17
        
        # Check joint_aggregates structure
        joint_aggregates = metrics['joint_aggregates']
        assert len(joint_aggregates) == 17
        
        for joint_name, stats in joint_aggregates.items():
            assert 'mean' in stats
            assert 'max' in stats
            assert 'std' in stats
    
    def test_temporal_phases(self):
        """Test temporal phase analysis."""
        metrics = compute_error_metrics(
            self.aligned_user, 
            self.aligned_expert,
            enable_temporal_phases=True
        )
        
        assert 'temporal_phases' in metrics
        
        phases = metrics['temporal_phases']
        expected_phases = ['early', 'mid', 'late']
        
        for phase in expected_phases:
            assert phase in phases
            assert len(phases[phase]['joint_means']) == 17
    
    def test_known_error_detection(self):
        """Test detection of artificially introduced errors."""
        # Create sequences with no error
        perfect_user = self.aligned_expert.copy()
        
        # Add known error to joint 5 (left_shoulder)
        error_magnitude = 0.3
        perfect_user[:, 5, :] += error_magnitude
        
        metrics = compute_error_metrics(perfect_user, self.aligned_expert)
        
        # Left shoulder should have highest error
        joint_ranking = get_joint_ranking(metrics, 'mean')
        worst_joint, worst_error = joint_ranking[0]
        
        assert worst_joint == 'left_shoulder'
        assert abs(worst_error - error_magnitude) < 0.05  # Allow small tolerance
    
    def test_zero_error_case(self):
        """Test perfect alignment case."""
        metrics = compute_error_metrics(self.aligned_expert, self.aligned_expert)
        
        # All errors should be zero
        for joint_name, stats in metrics['joint_aggregates'].items():
            assert abs(stats['mean']) < 1e-10
            assert abs(stats['max']) < 1e-10
            assert abs(stats['std']) < 1e-10
```

### 2.3 Similarity Scoring Tests

```python
# test_similarity_scoring.py
import pytest
import numpy as np
from pose_validation_metrics import PoseValidationMetrics

class TestSimilarityScoring:
    """Test suite for similarity scoring algorithms."""
    
    def setup_method(self):
        """Setup test data."""
        self.metrics = PoseValidationMetrics()
        self.perfect_poses = np.random.randn(100, 17, 2) * 0.1
        
    def test_perfect_similarity(self):
        """Test scoring of identical sequences."""
        scores = self.metrics.user_evaluation_score(
            self.perfect_poses, 
            self.perfect_poses
        )
        
        # Perfect similarity should yield high scores
        assert scores['overall'] > 95.0
        assert scores['structural'] > 95.0
        assert scores['temporal'] > 95.0
    
    def test_score_ranges(self):
        """Test that scores are in valid ranges."""
        # Create imperfect user poses
        noisy_poses = self.perfect_poses + np.random.randn(100, 17, 2) * 0.05
        
        scores = self.metrics.user_evaluation_score(noisy_poses, self.perfect_poses)
        
        # All scores should be in [0, 100] range
        for score_name, score_value in scores.items():
            assert 0.0 <= score_value <= 100.0, f"{score_name} score out of range: {score_value}"
    
    def test_score_degradation(self):
        """Test that scores decrease with increasing error."""
        base_scores = self.metrics.user_evaluation_score(
            self.perfect_poses, 
            self.perfect_poses
        )
        
        # Add increasing amounts of noise
        noise_levels = [0.01, 0.05, 0.1, 0.2]
        previous_score = base_scores['overall']
        
        for noise_level in noise_levels:
            noisy_poses = self.perfect_poses + np.random.randn(100, 17, 2) * noise_level
            scores = self.metrics.user_evaluation_score(noisy_poses, self.perfect_poses)
            
            # Score should decrease with more noise
            assert scores['overall'] <= previous_score + 1.0  # Allow small tolerance
            previous_score = scores['overall']
    
    @pytest.mark.parametrize("sequence_length", [50, 100, 200, 300])
    def test_different_sequence_lengths(self, sequence_length):
        """Test scoring with different sequence lengths."""
        user_poses = np.random.randn(sequence_length, 17, 2) * 0.1
        expert_poses = np.random.randn(sequence_length, 17, 2) * 0.1
        
        scores = self.metrics.user_evaluation_score(user_poses, expert_poses)
        
        # Should produce valid scores regardless of length
        assert isinstance(scores, dict)
        assert 'overall' in scores
        assert 0.0 <= scores['overall'] <= 100.0
```

---

## 3. Integration Testing

### 3.1 API Integration Tests

```python
# test_api_integration.py
import pytest
import requests
import tempfile
import os
from pathlib import Path

class TestAPIIntegration:
    """Integration tests for API endpoints."""
    
    @pytest.fixture(scope="class")
    def api_client(self):
        """Setup API client for testing."""
        base_url = os.getenv('TEST_API_URL', 'http://localhost:8000/api')
        return APITestClient(base_url)
    
    @pytest.fixture
    def sample_video(self):
        """Create sample video file for testing."""
        # Create temporary video file
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            # Write minimal MP4 header (for testing purposes)
            f.write(b'\x00\x00\x00\x20ftypmp4\x00')  # Minimal MP4 signature
            f.write(b'x' * 1024 * 1024)  # 1MB of data
            return f.name
    
    def test_complete_user_flow(self, api_client, sample_video):
        """Test complete user flow from tutorial to results."""
        
        # Step 1: Get tutorials
        tutorials = api_client.get_tutorials()
        assert len(tutorials) > 0
        
        tutorial_id = tutorials[0]['id']
        
        # Step 2: Create session
        session = api_client.create_session(tutorial_id)
        assert 'id' in session
        assert session['status'] == 'created'
        
        session_id = session['id']
        
        # Step 3: Upload video
        upload_result = api_client.upload_video(session_id, sample_video)
        assert upload_result['status'] == 'video_uploaded'
        
        # Step 4: Trigger assessment
        assessment = api_client.trigger_assessment(session_id)
        assert assessment['status'] == 'processing'
        
        # Step 5: Poll for completion
        results = api_client.poll_for_completion(session_id, timeout=300)
        
        # Verify results structure
        assert 'scores' in results
        assert 'error_metrics' in results
        assert 'overall' in results['scores']
        
        # Cleanup
        os.unlink(sample_video)
    
    def test_error_handling(self, api_client):
        """Test API error handling."""
        
        # Test invalid tutorial ID
        with pytest.raises(APIError) as exc_info:
            api_client.create_session('invalid-uuid')
        
        assert exc_info.value.status_code == 400
        
        # Test invalid session ID
        with pytest.raises(APIError) as exc_info:
            api_client.get_session_status('invalid-uuid')
        
        assert exc_info.value.status_code == 404
    
    def test_concurrent_sessions(self, api_client, sample_video):
        """Test handling of concurrent sessions."""
        import threading
        import time
        
        tutorials = api_client.get_tutorials()
        tutorial_id = tutorials[0]['id']
        
        results = []
        errors = []
        
        def create_and_process_session():
            try:
                # Create session
                session = api_client.create_session(tutorial_id)
                session_id = session['id']
                
                # Upload video
                api_client.upload_video(session_id, sample_video)
                
                # Trigger assessment
                api_client.trigger_assessment(session_id)
                
                results.append(session_id)
            except Exception as e:
                errors.append(str(e))
        
        # Create 5 concurrent sessions
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=create_and_process_session)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        
        # Cleanup
        os.unlink(sample_video)

class APITestClient:
    """Test client for API interactions."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def get_tutorials(self):
        response = self.session.get(f"{self.base_url}/tutorials/")
        response.raise_for_status()
        return response.json()['data']['tutorials']
    
    def create_session(self, tutorial_id: str):
        response = self.session.post(
            f"{self.base_url}/session/start/",
            json={'tutorial_id': tutorial_id}
        )
        if not response.ok:
            raise APIError(response.status_code, response.text)
        return response.json()['data']['session']
    
    def upload_video(self, session_id: str, video_path: str):
        with open(video_path, 'rb') as f:
            files = {'video': f}
            response = self.session.post(
                f"{self.base_url}/session/{session_id}/upload-video/",
                files=files
            )
        if not response.ok:
            raise APIError(response.status_code, response.text)
        return response.json()['data']['upload']
    
    def trigger_assessment(self, session_id: str):
        response = self.session.post(f"{self.base_url}/session/{session_id}/assess/")
        if not response.ok:
            raise APIError(response.status_code, response.text)
        return response.json()['data']['assessment']
    
    def get_session_status(self, session_id: str):
        response = self.session.get(f"{self.base_url}/session/{session_id}/status/")
        if not response.ok:
            raise APIError(response.status_code, response.text)
        return response.json()['data']['session']
    
    def get_results(self, session_id: str):
        response = self.session.get(f"{self.base_url}/session/{session_id}/results/")
        if not response.ok:
            raise APIError(response.status_code, response.text)
        return response.json()['data']['results']
    
    def poll_for_completion(self, session_id: str, timeout: int = 300):
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_session_status(session_id)
            
            if status['status'] == 'feedback_generated':
                return self.get_results(session_id)
            
            if status['status'] == 'failed':
                raise Exception(f"Assessment failed: {status.get('error_message')}")
            
            time.sleep(2)
        
        raise TimeoutError(f"Assessment did not complete within {timeout} seconds")

class APIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")
```

---

## 4. Performance Testing

### 4.1 Pipeline Performance Tests

```python
# test_performance.py
import pytest
import time
import numpy as np
import psutil
import os
from temporal_alignment import temporal_alignment
from error_localization import compute_error_metrics

class TestPerformance:
    """Performance tests for pipeline components."""
    
    @pytest.mark.benchmark
    def test_temporal_alignment_performance(self, benchmark):
        """Benchmark temporal alignment algorithm."""
        # Create test data
        user_poses = np.random.randn(150, 17, 2)
        expert_poses = np.random.randn(150, 17, 2)
        
        # Benchmark the function
        result = benchmark(temporal_alignment, user_poses, expert_poses)
        
        # Verify result format
        user_indices, expert_indices = result
        assert len(user_indices) > 0
        assert len(expert_indices) > 0
    
    @pytest.mark.benchmark
    def test_error_localization_performance(self, benchmark):
        """Benchmark error localization algorithm."""
        # Create aligned test data
        aligned_user = np.random.randn(150, 17, 2)
        aligned_expert = np.random.randn(150, 17, 2)
        
        # Benchmark the function
        result = benchmark(compute_error_metrics, aligned_user, aligned_expert)
        
        # Verify result structure
        assert 'frame_errors' in result
        assert 'joint_aggregates' in result
    
    @pytest.mark.parametrize("sequence_length", [50, 100, 200, 300, 500])
    def test_scalability(self, sequence_length):
        """Test performance scaling with sequence length."""
        user_poses = np.random.randn(sequence_length, 17, 2)
        expert_poses = np.random.randn(sequence_length, 17, 2)
        
        # Measure execution time
        start_time = time.time()
        user_indices, expert_indices = temporal_alignment(user_poses, expert_poses)
        execution_time = time.time() - start_time
        
        # Performance should scale reasonably
        expected_max_time = (sequence_length / 100) ** 2 * 0.1  # O(n²) scaling
        assert execution_time < expected_max_time, f"Too slow for {sequence_length} frames: {execution_time}s"
    
    def test_memory_usage(self):
        """Test memory usage during pipeline execution."""
        # Monitor memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create large test data
        user_poses = np.random.randn(300, 17, 2)
        expert_poses = np.random.randn(300, 17, 2)
        
        # Execute pipeline components
        user_indices, expert_indices = temporal_alignment(user_poses, expert_poses)
        
        aligned_user = user_poses[user_indices]
        aligned_expert = expert_poses[expert_indices]
        
        error_metrics = compute_error_metrics(aligned_user, aligned_expert)
        
        # Check peak memory usage
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        
        # Should not exceed 100MB for this test size
        max_memory_mb = 100 * 1024 * 1024
        assert memory_increase < max_memory_mb, f"Memory usage too high: {memory_increase / 1024 / 1024:.1f}MB"
    
    def test_concurrent_processing(self):
        """Test performance under concurrent load."""
        import threading
        import queue
        
        # Create test data
        test_cases = [
            (np.random.randn(100, 17, 2), np.random.randn(100, 17, 2))
            for _ in range(10)
        ]
        
        results_queue = queue.Queue()
        
        def process_alignment(user_poses, expert_poses):
            start_time = time.time()
            result = temporal_alignment(user_poses, expert_poses)
            execution_time = time.time() - start_time
            results_queue.put(execution_time)
        
        # Start concurrent threads
        threads = []
        start_time = time.time()
        
        for user_poses, expert_poses in test_cases:
            thread = threading.Thread(
                target=process_alignment, 
                args=(user_poses, expert_poses)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect results
        execution_times = []
        while not results_queue.empty():
            execution_times.append(results_queue.get())
        
        # Verify performance
        assert len(execution_times) == 10
        avg_execution_time = sum(execution_times) / len(execution_times)
        
        # Concurrent execution should not be significantly slower
        assert avg_execution_time < 1.0, f"Average execution time too high: {avg_execution_time}s"
        assert total_time < 10.0, f"Total concurrent time too high: {total_time}s"
```

### 4.2 Load Testing

```python
# test_load.py
import pytest
import requests
import threading
import time
import statistics

class TestLoadTesting:
    """Load testing for API endpoints."""
    
    @pytest.fixture
    def api_base_url(self):
        return os.getenv('TEST_API_URL', 'http://localhost:8000/api')
    
    def test_tutorial_list_load(self, api_base_url):
        """Load test for tutorial list endpoint."""
        results = []
        errors = []
        
        def make_request():
            try:
                start_time = time.time()
                response = requests.get(f"{api_base_url}/tutorials/")
                end_time = time.time()
                
                if response.status_code == 200:
                    results.append(end_time - start_time)
                else:
                    errors.append(f"HTTP {response.status_code}")
            except Exception as e:
                errors.append(str(e))
        
        # Create 50 concurrent requests
        threads = []
        for _ in range(50):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Analyze results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 50
        
        avg_response_time = statistics.mean(results)
        p95_response_time = statistics.quantiles(results, n=20)[18]  # 95th percentile
        
        # Performance assertions
        assert avg_response_time < 0.5, f"Average response time too high: {avg_response_time}s"
        assert p95_response_time < 1.0, f"95th percentile too high: {p95_response_time}s"
        assert total_time < 10.0, f"Total time too high: {total_time}s"
    
    def test_session_creation_load(self, api_base_url):
        """Load test for session creation."""
        # Get tutorial ID first
        response = requests.get(f"{api_base_url}/tutorials/")
        tutorials = response.json()['data']['tutorials']
        tutorial_id = tutorials[0]['id']
        
        results = []
        errors = []
        
        def create_session():
            try:
                start_time = time.time()
                response = requests.post(
                    f"{api_base_url}/session/start/",
                    json={'tutorial_id': tutorial_id}
                )
                end_time = time.time()
                
                if response.status_code == 200:
                    results.append(end_time - start_time)
                else:
                    errors.append(f"HTTP {response.status_code}")
            except Exception as e:
                errors.append(str(e))
        
        # Create 20 concurrent session creation requests
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=create_session)
            threads.append(thread)
        
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Analyze results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 20
        
        avg_response_time = statistics.mean(results)
        
        # Performance assertions
        assert avg_response_time < 1.0, f"Average response time too high: {avg_response_time}s"
        assert total_time < 15.0, f"Total time too high: {total_time}s"
```

---

## 5. Test Data Management

### 5.1 Test Data Generation

```python
# test_data_generator.py
import numpy as np
from pathlib import Path
import json

class TestDataGenerator:
    """Generate synthetic test data for validation."""
    
    @staticmethod
    def generate_pose_sequence(
        frames: int = 150,
        movement_type: str = 'linear',
        noise_level: float = 0.01,
        seed: int = 42
    ) -> np.ndarray:
        """Generate synthetic pose sequence."""
        np.random.seed(seed)
        
        poses = np.zeros((frames, 17, 2))
        
        if movement_type == 'linear':
            # Linear movement from left to right
            for t in range(frames):
                progress = t / frames
                
                # Base position
                base_x = 0.2 + 0.6 * progress
                base_y = 0.5
                
                # Set all joints relative to base
                poses[t, :, 0] = base_x + np.random.randn(17) * noise_level
                poses[t, :, 1] = base_y + np.random.randn(17) * noise_level
                
                # Adjust specific joints for realistic pose
                poses[t, 0, :] = [base_x, base_y - 0.2]  # nose (head up)
                poses[t, 5, :] = [base_x - 0.1, base_y - 0.1]  # left shoulder
                poses[t, 6, :] = [base_x + 0.1, base_y - 0.1]  # right shoulder
                poses[t, 11, :] = [base_x - 0.05, base_y + 0.2]  # left hip
                poses[t, 12, :] = [base_x + 0.05, base_y + 0.2]  # right hip
        
        elif movement_type == 'circular':
            # Circular movement pattern
            for t in range(frames):
                angle = 2 * np.pi * t / frames
                
                center_x = 0.5 + 0.2 * np.cos(angle)
                center_y = 0.5 + 0.2 * np.sin(angle)
                
                poses[t, :, 0] = center_x + np.random.randn(17) * noise_level
                poses[t, :, 1] = center_y + np.random.randn(17) * noise_level
        
        elif movement_type == 'kabaddi_touch':
            # Simulate kabaddi hand touch movement
            for t in range(frames):
                progress = t / frames
                
                if progress < 0.3:  # Approach phase
                    x = 0.2 + 0.4 * (progress / 0.3)
                    y = 0.5
                elif progress < 0.7:  # Touch phase
                    x = 0.6 + 0.2 * np.sin(10 * np.pi * (progress - 0.3))
                    y = 0.5 - 0.1 * (progress - 0.3) / 0.4
                else:  # Return phase
                    return_progress = (progress - 0.7) / 0.3
                    x = 0.6 - 0.4 * return_progress
                    y = 0.4 + 0.1 * return_progress
                
                # Set joint positions
                poses[t, 0, :] = [x, y - 0.2]  # nose
                poses[t, 5, :] = [x - 0.1, y - 0.1]  # left shoulder
                poses[t, 6, :] = [x + 0.1, y - 0.1]  # right shoulder
                poses[t, 9, :] = [x + 0.15, y - 0.15]  # right wrist (extended)
                poses[t, 11, :] = [x - 0.05, y + 0.2]  # left hip
                poses[t, 12, :] = [x + 0.05, y + 0.2]  # right hip
        
        return poses
    
    @staticmethod
    def create_test_dataset(output_dir: Path):
        """Create comprehensive test dataset."""
        output_dir.mkdir(exist_ok=True)
        
        # Generate different movement types
        movements = {
            'hand_touch': 'kabaddi_touch',
            'linear_movement': 'linear',
            'circular_movement': 'circular'
        }
        
        dataset_info = {
            'created_at': '2024-01-15T10:00:00Z',
            'format': 'COCO-17',
            'coordinate_system': 'normalized',
            'sequences': {}
        }
        
        for name, movement_type in movements.items():
            # Generate expert sequence
            expert_poses = TestDataGenerator.generate_pose_sequence(
                frames=150,
                movement_type=movement_type,
                noise_level=0.005,  # Low noise for expert
                seed=42
            )
            
            # Generate user sequences with varying quality
            user_sequences = {}
            
            for quality, noise_level in [('perfect', 0.005), ('good', 0.02), ('poor', 0.08)]:
                user_poses = TestDataGenerator.generate_pose_sequence(
                    frames=140,  # Slightly different length
                    movement_type=movement_type,
                    noise_level=noise_level,
                    seed=123
                )
                
                user_file = output_dir / f'{name}_user_{quality}.npy'
                np.save(user_file, user_poses)
                user_sequences[quality] = str(user_file)
            
            # Save expert sequence
            expert_file = output_dir / f'{name}_expert.npy'
            np.save(expert_file, expert_poses)
            
            dataset_info['sequences'][name] = {
                'expert': str(expert_file),
                'users': user_sequences,
                'movement_type': movement_type,
                'expert_frames': expert_poses.shape[0]
            }
        
        # Save dataset info
        with open(output_dir / 'dataset_info.json', 'w') as f:
            json.dump(dataset_info, f, indent=2)
        
        return dataset_info

# Usage
if __name__ == "__main__":
    generator = TestDataGenerator()
    dataset_info = generator.create_test_dataset(Path('test_data'))
    print("Test dataset created successfully")
```

### 5.2 Validation Test Suite

```python
# test_validation.py
import pytest
import numpy as np
import json
from pathlib import Path
from run_pipeline import main as run_pipeline

class TestValidation:
    """Validation tests using synthetic and real data."""
    
    @pytest.fixture(scope="class")
    def test_dataset(self):
        """Load test dataset."""
        dataset_path = Path('test_data')
        if not dataset_path.exists():
            pytest.skip("Test dataset not available")
        
        with open(dataset_path / 'dataset_info.json') as f:
            return json.load(f)
    
    def test_perfect_user_scoring(self, test_dataset):
        """Test scoring of perfect user performance."""
        for movement_name, movement_data in test_dataset['sequences'].items():
            expert_path = movement_data['expert']
            perfect_user_path = movement_data['users']['perfect']
            
            # Load poses
            expert_poses = np.load(expert_path)
            user_poses = np.load(perfect_user_path)
            
            # Run pipeline components
            from temporal_alignment import temporal_alignment
            from error_localization import compute_error_metrics
            from pose_validation_metrics import PoseValidationMetrics
            
            # Align sequences
            user_indices, expert_indices = temporal_alignment(user_poses, expert_poses)
            aligned_user = user_poses[user_indices]
            aligned_expert = expert_poses[expert_indices]
            
            # Compute scores
            metrics = PoseValidationMetrics()
            scores = metrics.user_evaluation_score(aligned_user, aligned_expert)
            
            # Perfect user should score very high
            assert scores['overall'] > 90.0, f"Perfect user scored too low for {movement_name}: {scores['overall']}"
            assert scores['structural'] > 90.0
            assert scores['temporal'] > 85.0
    
    def test_score_ordering(self, test_dataset):
        """Test that scores order correctly by quality."""
        for movement_name, movement_data in test_dataset['sequences'].items():
            expert_path = movement_data['expert']
            expert_poses = np.load(expert_path)
            
            scores_by_quality = {}
            
            # Compute scores for each quality level
            for quality in ['perfect', 'good', 'poor']:
                user_path = movement_data['users'][quality]
                user_poses = np.load(user_path)
                
                # Run pipeline
                from temporal_alignment import temporal_alignment
                from pose_validation_metrics import PoseValidationMetrics
                
                user_indices, expert_indices = temporal_alignment(user_poses, expert_poses)
                aligned_user = user_poses[user_indices]
                aligned_expert = expert_poses[expert_indices]
                
                metrics = PoseValidationMetrics()
                scores = metrics.user_evaluation_score(aligned_user, aligned_expert)
                
                scores_by_quality[quality] = scores['overall']
            
            # Verify score ordering
            assert scores_by_quality['perfect'] >= scores_by_quality['good'], \
                f"Perfect should score >= good for {movement_name}"
            assert scores_by_quality['good'] >= scores_by_quality['poor'], \
                f"Good should score >= poor for {movement_name}"
    
    def test_error_localization_accuracy(self, test_dataset):
        """Test error localization accuracy."""
        movement_name = 'hand_touch'
        movement_data = test_dataset['sequences'][movement_name]
        
        expert_poses = np.load(movement_data['expert'])
        user_poses = np.load(movement_data['users']['poor'])
        
        # Introduce known error to specific joint
        user_poses_with_error = user_poses.copy()
        error_joint_idx = 9  # right_wrist
        error_magnitude = 0.1
        user_poses_with_error[:, error_joint_idx, :] += error_magnitude
        
        # Run error localization
        from temporal_alignment import temporal_alignment
        from error_localization import compute_error_metrics, get_joint_ranking
        
        user_indices, expert_indices = temporal_alignment(user_poses_with_error, expert_poses)
        aligned_user = user_poses_with_error[user_indices]
        aligned_expert = expert_poses[expert_indices]
        
        error_metrics = compute_error_metrics(aligned_user, aligned_expert)
        joint_ranking = get_joint_ranking(error_metrics, 'mean')
        
        # The joint with added error should be among top 3 problematic joints
        top_3_joints = [joint_name for joint_name, _ in joint_ranking[:3]]
        assert 'right_wrist' in top_3_joints, f"Failed to detect error in right_wrist. Top 3: {top_3_joints}"
    
    @pytest.mark.slow
    def test_end_to_end_pipeline(self, test_dataset, tmp_path):
        """Test complete end-to-end pipeline execution."""
        movement_name = 'hand_touch'
        movement_data = test_dataset['sequences'][movement_name]
        
        expert_path = movement_data['expert']
        user_path = movement_data['users']['good']
        
        # Create temporary output directory
        output_dir = tmp_path / 'pipeline_output'
        output_dir.mkdir()
        
        # Mock command line arguments
        class MockArgs:
            expert_pose = expert_path
            user_pose = user_path
            output_dir = str(output_dir)
            no_tts = True
            no_viz = True
            verbose = False
        
        args = MockArgs()
        
        # Run complete pipeline
        try:
            from run_pipeline import main
            main(args)
        except SystemExit:
            pass  # Pipeline may exit normally
        
        # Verify outputs
        assert (output_dir / 'scores.json').exists(), "scores.json not generated"
        assert (output_dir / 'error_metrics.json').exists(), "error_metrics.json not generated"
        assert (output_dir / 'feedback.json').exists(), "feedback.json not generated"
        
        # Verify output format
        with open(output_dir / 'scores.json') as f:
            scores = json.load(f)
            assert 'overall' in scores
            assert 'structural' in scores
            assert 'temporal' in scores
        
        with open(output_dir / 'error_metrics.json') as f:
            error_metrics = json.load(f)
            assert 'frame_errors' in error_metrics
            assert 'joint_aggregates' in error_metrics
```

---

## 6. Continuous Integration

### 6.1 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
    
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
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Generate test data
      run: |
        python test_data_generator.py
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=. --cov-report=xml
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost/test_kabaddi_trainer
      run: |
        pytest tests/integration/ -v
    
    - name: Run performance tests
      run: |
        pytest tests/performance/ -v --benchmark-only
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
    
    - name: Run linting
      run: |
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Type checking
      run: |
        mypy --ignore-missing-imports .

  api-test:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Start Django server
      run: |
        cd kabaddi_backend
        python manage.py migrate
        python manage.py create_tutorials
        python manage.py runserver &
        sleep 10
      env:
        DJANGO_SETTINGS_MODULE: kabaddi_backend.settings
    
    - name: Run API tests
      run: |
        pytest tests/api/ -v
      env:
        TEST_API_URL: http://localhost:8000/api
    
    - name: Stop Django server
      run: |
        pkill -f "python manage.py runserver"
```

### 6.2 Test Configuration

```python
# pytest.ini
[tool:pytest]
minversion = 6.0
addopts = 
    -ra 
    -q 
    --strict-markers 
    --strict-config
    --cov=.
    --cov-branch
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
testpaths = tests
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    benchmark: marks tests as benchmarks
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    api: marks tests as API tests
    performance: marks tests as performance tests

# conftest.py
import pytest
import numpy as np
from pathlib import Path

@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory."""
    return Path(__file__).parent / "test_data"

@pytest.fixture
def sample_poses():
    """Provide sample pose data for testing."""
    return np.random.randn(100, 17, 2)

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment."""
    # Set random seed for reproducible tests
    np.random.seed(42)
    
    # Create test data if it doesn't exist
    test_data_dir = Path(__file__).parent / "test_data"
    if not test_data_dir.exists():
        from test_data_generator import TestDataGenerator
        TestDataGenerator.create_test_dataset(test_data_dir)

@pytest.fixture
def django_db_setup(django_db_setup, django_db_blocker):
    """Setup Django test database."""
    with django_db_blocker.unblock():
        from django.core.management import call_command
        call_command('migrate', verbosity=0, interactive=False)
        call_command('create_tutorials', verbosity=0)
```

---

## 7. Conclusion

This Testing and Validation Document provides comprehensive coverage for the AR-Based Kabaddi Ghost Trainer system. The testing strategy includes:

1. **Unit Tests**: 70% coverage focusing on individual algorithm components
2. **Integration Tests**: 20% coverage for component interactions
3. **End-to-End Tests**: 10% coverage for complete user workflows
4. **Performance Tests**: Benchmarking and load testing
5. **Validation Tests**: Accuracy verification with synthetic data

The testing framework ensures system reliability, performance, and correctness across all components from pose algorithms to API endpoints.

---

**Document Control**:
- Version: 1.0
- Last Updated: 2024-01-15
- Next Review: 2024-04-15
- Approval: QA Team