# API Specification Document - AR-Based Kabaddi Ghost Trainer

## Document Information
- **Version**: 1.0
- **Date**: 2024-01-15
- **Author**: API Design Team
- **Classification**: Technical Specification

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Request/Response Format](#requestresponse-format)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Tutorial Management API](#tutorial-management-api)
7. [Session Management API](#session-management-api)
8. [File Upload API](#file-upload-api)
9. [Results & Analytics API](#results--analytics-api)
10. [Health & Monitoring API](#health--monitoring-api)
11. [SDK & Integration Examples](#sdk--integration-examples)
12. [Versioning Strategy](#versioning-strategy)

---

## 1. API Overview

### 1.1 Base Information

**Base URL**: `https://api.kabaddi-trainer.com/api/`
**Protocol**: HTTPS only
**Content-Type**: `application/json` (except file uploads)
**API Version**: v1 (current)

### 1.2 Supported Operations

The API supports the complete user journey:
1. **Tutorial Discovery**: Browse available kabaddi movements
2. **AR Data Retrieval**: Get pose data for AR ghost rendering
3. **Session Management**: Create and track assessment sessions
4. **Video Upload**: Submit user performance videos
5. **Pipeline Execution**: Trigger pose analysis and scoring
6. **Results Retrieval**: Access scores, error metrics, and feedback

### 1.3 Architecture Principles

- **RESTful Design**: Resource-based URLs with HTTP verbs
- **Stateless**: Each request contains all necessary information
- **Idempotent**: Safe operations can be repeated without side effects
- **Consistent**: Uniform response formats and error handling
- **Secure**: UUID-based identifiers prevent enumeration attacks

---

## 2. Authentication & Authorization

### 2.1 Current Implementation (Development)

**Status**: No authentication required
**Access**: Open API for development and testing

### 2.2 Production Implementation (Future)

**Authentication Method**: API Key Authentication
```http
GET /api/tutorials/
Host: api.kabaddi-trainer.com
X-API-Key: your-api-key-here
Accept: application/json
```

**API Key Management**:
```json
{
  "api_key": "kb_live_1234567890abcdef",
  "environment": "production",
  "permissions": ["read", "write"],
  "rate_limit": "1000/hour",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

### 2.3 Authorization Levels

| Level | Permissions | Use Case |
|-------|-------------|----------|
| **Read-Only** | GET operations only | Mobile app (read tutorials, results) |
| **Standard** | Full CRUD operations | Mobile app (complete functionality) |
| **Admin** | System management | Backend administration |

---

## 3. Request/Response Format

### 3.1 Request Headers

**Required Headers**:
```http
Content-Type: application/json
Accept: application/json
User-Agent: KabaddiTrainer/1.0 (iOS/Android)
```

**Optional Headers**:
```http
X-API-Key: your-api-key-here          # Authentication
X-Request-ID: uuid-for-tracing        # Request tracing
X-Client-Version: 1.2.3               # Client version
```

### 3.2 Response Format

**Success Response Structure**:
```json
{
  "success": true,
  "data": {
    // Response payload
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "version": "1.0"
  }
}
```

**Error Response Structure**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "tutorial_id",
      "reason": "Required field missing"
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "version": "1.0"
  }
}
```

### 3.3 Data Types

| Type | Format | Example | Description |
|------|--------|---------|-------------|
| **UUID** | String | `550e8400-e29b-41d4-a716-446655440000` | Unique identifier |
| **Timestamp** | ISO 8601 | `2024-01-15T10:30:45.123456Z` | UTC timestamp |
| **FileSize** | Integer | `15728640` | Bytes |
| **Score** | Float | `85.2` | 0-100 scale |
| **Status** | Enum | `"video_uploaded"` | Predefined values |

---

## 4. Error Handling

### 4.1 HTTP Status Codes

| Code | Status | Description | Usage |
|------|--------|-------------|-------|
| **200** | OK | Success | Successful GET, PUT, PATCH |
| **201** | Created | Resource created | Successful POST |
| **204** | No Content | Success, no body | Successful DELETE |
| **400** | Bad Request | Invalid input | Validation errors |
| **401** | Unauthorized | Authentication required | Missing/invalid API key |
| **403** | Forbidden | Access denied | Insufficient permissions |
| **404** | Not Found | Resource not found | Invalid ID or path |
| **409** | Conflict | Resource conflict | Duplicate creation |
| **422** | Unprocessable Entity | Semantic errors | Business logic violations |
| **429** | Too Many Requests | Rate limit exceeded | Throttling |
| **500** | Internal Server Error | Server error | Unexpected failures |
| **503** | Service Unavailable | Temporary unavailable | Maintenance mode |

### 4.2 Error Codes

**Client Errors (4xx)**:
```json
{
  "VALIDATION_ERROR": "Input validation failed",
  "MISSING_FIELD": "Required field not provided",
  "INVALID_FORMAT": "Field format is incorrect",
  "RESOURCE_NOT_FOUND": "Requested resource does not exist",
  "DUPLICATE_RESOURCE": "Resource already exists",
  "INVALID_STATUS": "Operation not allowed in current status",
  "FILE_TOO_LARGE": "Uploaded file exceeds size limit",
  "UNSUPPORTED_FORMAT": "File format not supported"
}
```

**Server Errors (5xx)**:
```json
{
  "INTERNAL_ERROR": "Unexpected server error",
  "PIPELINE_FAILURE": "Processing pipeline failed",
  "STORAGE_ERROR": "File storage operation failed",
  "DATABASE_ERROR": "Database operation failed",
  "EXTERNAL_SERVICE_ERROR": "External service unavailable"
}
```

### 4.3 Error Response Examples

**Validation Error**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": {
      "tutorial_id": ["This field is required"],
      "video": ["File size exceeds 100MB limit"]
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Resource Not Found**:
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Session not found",
    "details": {
      "resource": "UserSession",
      "id": "invalid-uuid-here"
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

## 5. Rate Limiting

### 5.1 Rate Limit Policies

| Endpoint Category | Limit | Window | Burst |
|------------------|-------|--------|-------|
| **Tutorial Browsing** | 100 req/min | 1 minute | 20 |
| **Session Management** | 50 req/min | 1 minute | 10 |
| **File Upload** | 10 req/min | 1 minute | 2 |
| **Results Retrieval** | 200 req/min | 1 minute | 50 |
| **Health Checks** | 1000 req/min | 1 minute | 100 |

### 5.2 Rate Limit Headers

**Response Headers**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248000
X-RateLimit-Window: 60
```

**Rate Limit Exceeded Response**:
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
      "limit": 100,
      "window": "1 minute",
      "retry_after": 45
    }
  }
}
```

---

## 6. Tutorial Management API

### 6.1 List Tutorials

**Endpoint**: `GET /api/tutorials/`
**Purpose**: Retrieve list of available kabaddi tutorials

**Request**:
```http
GET /api/tutorials/ HTTP/1.1
Host: api.kabaddi-trainer.com
Accept: application/json
```

**Response**:
```json
{
  "success": true,
  "data": {
    "tutorials": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "hand_touch",
        "description": "Hand touch kabaddi movement - fundamental raiding technique",
        "difficulty": "beginner",
        "duration_seconds": 5.0,
        "total_frames": 150,
        "created_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "name": "toe_touch",
        "description": "Toe touch kabaddi movement - advanced raiding technique",
        "difficulty": "intermediate",
        "duration_seconds": 4.5,
        "total_frames": 135,
        "created_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "name": "bonus",
        "description": "Bonus kabaddi movement - expert level technique",
        "difficulty": "advanced",
        "duration_seconds": 6.0,
        "total_frames": 180,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total_count": 3,
    "active_count": 3
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `active_only` | Boolean | `true` | Filter to active tutorials only |
| `difficulty` | String | `null` | Filter by difficulty level |
| `limit` | Integer | `50` | Maximum results to return |
| `offset` | Integer | `0` | Results offset for pagination |

### 6.2 Get Tutorial Details

**Endpoint**: `GET /api/tutorials/{tutorial_id}/`
**Purpose**: Retrieve detailed information about a specific tutorial

**Request**:
```http
GET /api/tutorials/550e8400-e29b-41d4-a716-446655440000/ HTTP/1.1
Host: api.kabaddi-trainer.com
Accept: application/json
```

**Response**:
```json
{
  "success": true,
  "data": {
    "tutorial": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "hand_touch",
      "description": "Hand touch kabaddi movement - fundamental raiding technique",
      "difficulty": "beginner",
      "duration_seconds": 5.0,
      "total_frames": 150,
      "fps": 30,
      "pose_format": "COCO-17",
      "joints_count": 17,
      "created_at": "2024-01-01T00:00:00Z",
      "metadata": {
        "movement_type": "raiding",
        "body_parts": ["hands", "torso", "legs"],
        "key_points": ["approach", "touch", "return"],
        "common_errors": ["poor_timing", "incorrect_posture", "slow_return"]
      }
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440001"
  }
}
```

### 6.3 Get AR Pose Data

**Endpoint**: `GET /api/tutorials/{tutorial_id}/ar-poses/`
**Purpose**: Retrieve AR-ready pose data for mobile app ghost rendering

**Request**:
```http
GET /api/tutorials/550e8400-e29b-41d4-a716-446655440000/ar-poses/ HTTP/1.1
Host: api.kabaddi-trainer.com
Accept: application/json
```

**Response**:
```json
{
  "success": true,
  "data": {
    "tutorial_id": "550e8400-e29b-41d4-a716-446655440000",
    "tutorial_name": "hand_touch",
    "total_frames": 150,
    "duration": 5.0,
    "fps": 30,
    "pose_format": "COCO-17",
    "coordinate_system": "normalized",
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
          },
          {
            "name": "right_shoulder",
            "x": 0.6,
            "y": 0.4,
            "z": 0.0,
            "confidence": 1.0
          }
          // ... 14 more joints
        ]
      },
      {
        "frame": 1,
        "timestamp": 0.033,
        "joints": [
          // ... joint data for frame 1
        ]
      }
      // ... 148 more frames
    ]
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440002"
  }
}
```

**AR Pose Data Specification**:
- **Coordinates**: Normalized (0.0-1.0) for device independence
- **Z-Coordinate**: Always 0.0 for pseudo-3D (anchored in 3D space)
- **Confidence**: 1.0 for all joints (cleaned expert data)
- **Joint Order**: COCO-17 standard format
- **Frame Rate**: 30 FPS for smooth AR playback

---

## 7. Session Management API

### 7.1 Create Session

**Endpoint**: `POST /api/session/start/`
**Purpose**: Initialize a new user assessment session

**Request**:
```http
POST /api/session/start/ HTTP/1.1
Host: api.kabaddi-trainer.com
Content-Type: application/json

{
  "tutorial_id": "550e8400-e29b-41d4-a716-446655440000",
  "client_info": {
    "platform": "iOS",
    "version": "1.2.3",
    "device_model": "iPhone 14 Pro"
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "session": {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "tutorial": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "hand_touch",
        "description": "Hand touch kabaddi movement"
      },
      "status": "created",
      "created_at": "2024-01-15T10:30:45.123456Z",
      "expires_at": "2024-01-15T22:30:45.123456Z"
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440003"
  }
}
```

**Validation Rules**:
- `tutorial_id` must be a valid UUID
- Tutorial must exist and be active
- Client info is optional but recommended for analytics

### 7.2 Get Session Status

**Endpoint**: `GET /api/session/{session_id}/status/`
**Purpose**: Check current session status and progress

**Request**:
```http
GET /api/session/660e8400-e29b-41d4-a716-446655440000/status/ HTTP/1.1
Host: api.kabaddi-trainer.com
Accept: application/json
```

**Response**:
```json
{
  "success": true,
  "data": {
    "session": {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "status": "level2_complete",
      "progress": {
        "current_stage": "Level-3 Error Localization",
        "completed_stages": [
          "Video Upload",
          "Pose Extraction", 
          "Level-1 Cleaning",
          "Level-2 Temporal Alignment"
        ],
        "remaining_stages": [
          "Level-3 Error Localization",
          "Level-4 Similarity Scoring",
          "LLM Feedback Generation"
        ],
        "progress_percentage": 57
      },
      "created_at": "2024-01-15T10:30:45.123456Z",
      "updated_at": "2024-01-15T10:32:15.789012Z",
      "estimated_completion": "2024-01-15T10:35:00.000000Z",
      "error_message": null
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:32:30.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440004"
  }
}
```

**Status Values**:
| Status | Description | Progress % |
|--------|-------------|------------|
| `created` | Session initialized | 0% |
| `video_uploaded` | Video file stored | 14% |
| `pose_extracted` | Pose extraction completed | 28% |
| `level1_complete` | Level-1 cleaning completed | 42% |
| `level2_complete` | Level-2 alignment completed | 57% |
| `level3_complete` | Level-3 error localization completed | 71% |
| `scoring_complete` | Level-4 scoring completed | 85% |
| `feedback_generated` | LLM feedback generated | 100% |
| `failed` | Pipeline failed | N/A |

### 7.3 Cancel Session

**Endpoint**: `DELETE /api/session/{session_id}/`
**Purpose**: Cancel an active session and cleanup resources

**Request**:
```http
DELETE /api/session/660e8400-e29b-41d4-a716-446655440000/ HTTP/1.1
Host: api.kabaddi-trainer.com
```

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "Session cancelled successfully",
    "cleanup": {
      "files_removed": 3,
      "storage_freed": "52.3 MB"
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:35:00.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440005"
  }
}
```

---

## 8. File Upload API

### 8.1 Upload Video

**Endpoint**: `POST /api/session/{session_id}/upload-video/`
**Purpose**: Upload user performance video for analysis

**Request**:
```http
POST /api/session/660e8400-e29b-41d4-a716-446655440000/upload-video/ HTTP/1.1
Host: api.kabaddi-trainer.com
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="video"; filename="user_attempt.mp4"
Content-Type: video/mp4

[binary video data]
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```

**Response**:
```json
{
  "success": true,
  "data": {
    "upload": {
      "session_id": "660e8400-e29b-41d4-a716-446655440000",
      "file_info": {
        "filename": "user_attempt.mp4",
        "size": 15728640,
        "duration": 8.5,
        "format": "mp4",
        "resolution": "1920x1080",
        "fps": 30
      },
      "status": "video_uploaded",
      "uploaded_at": "2024-01-15T10:31:00.123456Z",
      "checksum": "sha256:a1b2c3d4e5f6..."
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:31:00.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440006"
  }
}
```

**Upload Constraints**:
- **Maximum Size**: 100 MB
- **Supported Formats**: MP4, MOV, AVI
- **Minimum Duration**: 2 seconds
- **Maximum Duration**: 30 seconds
- **Resolution**: 480p minimum, 4K maximum
- **Frame Rate**: 15-60 FPS

**Validation Errors**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "File validation failed",
    "details": {
      "file_size": "File exceeds 100MB limit (actual: 125MB)",
      "duration": "Video too long (actual: 45s, max: 30s)",
      "format": "Unsupported format: .avi"
    }
  }
}
```

### 8.2 Trigger Assessment

**Endpoint**: `POST /api/session/{session_id}/assess/`
**Purpose**: Start the pose analysis pipeline

**Request**:
```http
POST /api/session/660e8400-e29b-41d4-a716-446655440000/assess/ HTTP/1.1
Host: api.kabaddi-trainer.com
Content-Type: application/json

{
  "options": {
    "enable_feedback": true,
    "enable_visualization": false,
    "priority": "normal"
  }
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "assessment": {
      "session_id": "660e8400-e29b-41d4-a716-446655440000",
      "status": "processing",
      "pipeline": {
        "stages": [
          "Pose Extraction",
          "Level-1 Cleaning", 
          "Level-2 Temporal Alignment",
          "Level-3 Error Localization",
          "Level-4 Similarity Scoring",
          "LLM Feedback Generation"
        ],
        "estimated_duration": "3-5 minutes",
        "priority": "normal"
      },
      "started_at": "2024-01-15T10:31:30.123456Z"
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:31:30.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440007"
  }
}
```

**Prerequisites**:
- Session must exist
- Session status must be `video_uploaded`
- Video file must be accessible
- Expert pose must exist for tutorial

---

## 9. Results & Analytics API

### 9.1 Get Assessment Results

**Endpoint**: `GET /api/session/{session_id}/results/`
**Purpose**: Retrieve complete assessment results and feedback

**Request**:
```http
GET /api/session/660e8400-e29b-41d4-a716-446655440000/results/ HTTP/1.1
Host: api.kabaddi-trainer.com
Accept: application/json
```

**Response**:
```json
{
  "success": true,
  "data": {
    "results": {
      "session_id": "660e8400-e29b-41d4-a716-446655440000",
      "tutorial": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "hand_touch"
      },
      "scores": {
        "overall": 82.1,
        "structural": 85.2,
        "temporal": 78.9,
        "breakdown": {
          "pose_accuracy": 85.2,
          "timing_consistency": 78.9,
          "movement_fluidity": 80.5,
          "technique_adherence": 84.7
        }
      },
      "error_metrics": {
        "summary": {
          "total_frames": 150,
          "joints_analyzed": 17,
          "average_error": 0.18,
          "max_error": 0.67,
          "error_std": 0.12
        },
        "joint_analysis": {
          "most_problematic": [
            {
              "joint": "right_elbow",
              "mean_error": 0.25,
              "max_error": 0.67,
              "improvement_potential": "high"
            },
            {
              "joint": "left_shoulder", 
              "mean_error": 0.18,
              "max_error": 0.45,
              "improvement_potential": "medium"
            }
          ],
          "best_performing": [
            {
              "joint": "nose",
              "mean_error": 0.08,
              "max_error": 0.15,
              "performance": "excellent"
            }
          ]
        },
        "temporal_analysis": {
          "phases": {
            "early": {
              "performance": "good",
              "average_error": 0.15,
              "key_issues": ["initial_positioning"]
            },
            "mid": {
              "performance": "needs_improvement", 
              "average_error": 0.22,
              "key_issues": ["elbow_extension", "timing"]
            },
            "late": {
              "performance": "good",
              "average_error": 0.16,
              "key_issues": ["return_posture"]
            }
          }
        }
      },
      "feedback": {
        "overall_assessment": "Good effort! Your performance shows solid fundamentals with room for improvement in timing and elbow positioning.",
        "strengths": [
          "Excellent head and torso positioning throughout the movement",
          "Good initial approach and stance",
          "Consistent leg positioning and balance"
        ],
        "areas_for_improvement": [
          "Focus on right elbow extension during the touch phase",
          "Work on timing consistency, especially in the mid-phase",
          "Improve shoulder alignment during the return movement"
        ],
        "specific_recommendations": [
          {
            "area": "Right Elbow",
            "issue": "Insufficient extension during touch",
            "suggestion": "Practice slow-motion touches focusing on full arm extension",
            "priority": "high"
          },
          {
            "area": "Timing",
            "issue": "Inconsistent pace in mid-phase",
            "suggestion": "Use metronome training to develop consistent rhythm",
            "priority": "medium"
          }
        ],
        "next_steps": [
          "Practice the movement 10 times focusing on elbow extension",
          "Record another attempt after practicing the recommendations",
          "Consider trying the toe_touch tutorial for advanced techniques"
        ],
        "generated_at": "2024-01-15T10:35:00.123456Z",
        "model_used": "gpt-4"
      },
      "processing_info": {
        "pipeline_duration": "4m 23s",
        "stages_completed": 6,
        "completed_at": "2024-01-15T10:35:53.123456Z"
      }
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:36:00.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440008"
  }
}
```

**Prerequisites**:
- Session must exist
- Session status must be `scoring_complete` or `feedback_generated`
- Pipeline must have completed successfully

### 9.2 Get Detailed Error Metrics

**Endpoint**: `GET /api/session/{session_id}/error-metrics/`
**Purpose**: Retrieve detailed frame-by-frame error analysis

**Request**:
```http
GET /api/session/660e8400-e29b-41d4-a716-446655440000/error-metrics/ HTTP/1.1
Host: api.kabaddi-trainer.com
Accept: application/json
```

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_frames` | Boolean | `false` | Include frame-by-frame data |
| `joint_filter` | String | `null` | Filter to specific joints |
| `phase_filter` | String | `null` | Filter to specific phases |

**Response**:
```json
{
  "success": true,
  "data": {
    "error_metrics": {
      "metadata": {
        "total_frames": 150,
        "joints_count": 17,
        "analysis_type": "euclidean_distance",
        "coordinate_system": "normalized"
      },
      "frame_errors": {
        "shape": [150, 17],
        "summary": {
          "min": 0.02,
          "max": 0.67,
          "mean": 0.18,
          "std": 0.12,
          "percentiles": {
            "25th": 0.09,
            "50th": 0.15,
            "75th": 0.24,
            "95th": 0.42
          }
        },
        "data": [
          // Frame-by-frame data (if include_frames=true)
          [0.12, 0.08, 0.15, ...], // Frame 0 errors for all 17 joints
          [0.11, 0.09, 0.16, ...], // Frame 1 errors for all 17 joints
          // ... 148 more frames
        ]
      },
      "joint_aggregates": {
        "nose": {
          "mean": 0.08,
          "max": 0.15,
          "std": 0.03,
          "rank": 1,
          "performance": "excellent"
        },
        "left_shoulder": {
          "mean": 0.15,
          "max": 0.45,
          "std": 0.12,
          "rank": 8,
          "performance": "good"
        },
        "right_elbow": {
          "mean": 0.25,
          "max": 0.67,
          "std": 0.18,
          "rank": 17,
          "performance": "needs_improvement"
        }
        // ... 14 more joints
      },
      "temporal_phases": {
        "early": {
          "frames": "0-49",
          "duration": "1.67s",
          "joint_errors": {
            "nose": 0.07,
            "left_shoulder": 0.12,
            "right_elbow": 0.19
            // ... 14 more joints
          },
          "phase_score": 85.3
        },
        "mid": {
          "frames": "50-99", 
          "duration": "1.67s",
          "joint_errors": {
            "nose": 0.09,
            "left_shoulder": 0.18,
            "right_elbow": 0.32
            // ... 14 more joints
          },
          "phase_score": 76.8
        },
        "late": {
          "frames": "100-149",
          "duration": "1.67s", 
          "joint_errors": {
            "nose": 0.08,
            "left_shoulder": 0.16,
            "right_elbow": 0.24
            // ... 14 more joints
          },
          "phase_score": 82.1
        }
      }
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:36:30.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440009"
  }
}
```

### 9.3 Download Visualization

**Endpoint**: `GET /api/session/{session_id}/visualization/`
**Purpose**: Download AR comparison video (if generated)

**Request**:
```http
GET /api/session/660e8400-e29b-41d4-a716-446655440000/visualization/ HTTP/1.1
Host: api.kabaddi-trainer.com
Accept: video/mp4
```

**Response**:
```http
HTTP/1.1 200 OK
Content-Type: video/mp4
Content-Length: 5242880
Content-Disposition: attachment; filename="comparison_660e8400.mp4"

[binary video data]
```

**Alternative JSON Response** (if video not available):
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Visualization video not generated",
    "details": {
      "reason": "Visualization was disabled for this session",
      "alternatives": ["Request new assessment with visualization enabled"]
    }
  }
}
```

---

## 10. Health & Monitoring API

### 10.1 System Health Check

**Endpoint**: `GET /api/health/`
**Purpose**: Check overall system health and component status

**Request**:
```http
GET /api/health/ HTTP/1.1
Host: api.kabaddi-trainer.com
Accept: application/json
```

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-15T10:37:00.123456Z",
    "version": "1.0.0",
    "uptime": "72h 15m 30s",
    "checks": {
      "database": {
        "status": "healthy",
        "response_time": "2ms",
        "connections": {
          "active": 5,
          "max": 100
        }
      },
      "filesystem": {
        "status": "healthy",
        "disk_usage": {
          "used": "45.2GB",
          "available": "154.8GB",
          "percentage": 22.6
        }
      },
      "pipeline_scripts": {
        "status": "healthy",
        "scripts_found": 4,
        "last_execution": "2024-01-15T10:35:53.123456Z"
      },
      "external_services": {
        "llm_service": {
          "status": "healthy",
          "response_time": "450ms"
        }
      }
    },
    "metrics": {
      "active_sessions": 12,
      "processing_queue": 3,
      "completed_today": 47,
      "error_rate": "0.8%"
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:37:00.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440010"
  }
}
```

### 10.2 System Metrics

**Endpoint**: `GET /api/metrics/`
**Purpose**: Retrieve detailed system performance metrics

**Request**:
```http
GET /api/metrics/ HTTP/1.1
Host: api.kabaddi-trainer.com
Accept: application/json
```

**Response**:
```json
{
  "success": true,
  "data": {
    "metrics": {
      "sessions": {
        "total": 1247,
        "active": 12,
        "completed": 1198,
        "failed": 37,
        "success_rate": 97.0
      },
      "tutorials": {
        "total": 3,
        "active": 3,
        "popularity": {
          "hand_touch": 45.2,
          "toe_touch": 32.1,
          "bonus": 22.7
        }
      },
      "performance": {
        "avg_pipeline_duration": "4m 12s",
        "avg_response_time": "245ms",
        "throughput": {
          "requests_per_minute": 23.5,
          "sessions_per_hour": 8.2
        }
      },
      "storage": {
        "total_videos": 1247,
        "total_size": "156.3GB",
        "avg_video_size": "125.4MB"
      },
      "errors": {
        "last_24h": 12,
        "most_common": [
          {
            "error": "PIPELINE_FAILURE",
            "count": 5,
            "percentage": 41.7
          },
          {
            "error": "FILE_TOO_LARGE", 
            "count": 4,
            "percentage": 33.3
          }
        ]
      }
    },
    "time_range": {
      "start": "2024-01-14T10:37:00.123456Z",
      "end": "2024-01-15T10:37:00.123456Z",
      "duration": "24 hours"
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:37:00.123456Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440011"
  }
}
```

---

## 11. SDK & Integration Examples

### 11.1 JavaScript/TypeScript SDK

```typescript
// kabaddi-trainer-sdk.ts
export class KabaddiTrainerAPI {
  private baseURL: string;
  private apiKey?: string;

  constructor(baseURL: string, apiKey?: string) {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...options.headers,
    };

    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new APIError(error.error.code, error.error.message);
    }

    return response.json();
  }

  // Tutorial methods
  async getTutorials(): Promise<Tutorial[]> {
    const response = await this.request<{data: {tutorials: Tutorial[]}}>('/tutorials/');
    return response.data.tutorials;
  }

  async getTutorial(id: string): Promise<Tutorial> {
    const response = await this.request<{data: {tutorial: Tutorial}}>(`/tutorials/${id}/`);
    return response.data.tutorial;
  }

  async getARPoses(tutorialId: string): Promise<ARPoseData> {
    const response = await this.request<{data: ARPoseData}>(`/tutorials/${tutorialId}/ar-poses/`);
    return response.data;
  }

  // Session methods
  async createSession(tutorialId: string): Promise<Session> {
    const response = await this.request<{data: {session: Session}}>('/session/start/', {
      method: 'POST',
      body: JSON.stringify({ tutorial_id: tutorialId }),
    });
    return response.data.session;
  }

  async uploadVideo(sessionId: string, videoFile: File): Promise<UploadResult> {
    const formData = new FormData();
    formData.append('video', videoFile);

    const response = await fetch(`${this.baseURL}/session/${sessionId}/upload-video/`, {
      method: 'POST',
      headers: this.apiKey ? { 'X-API-Key': this.apiKey } : {},
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new APIError(error.error.code, error.error.message);
    }

    const result = await response.json();
    return result.data.upload;
  }

  async triggerAssessment(sessionId: string): Promise<AssessmentResult> {
    const response = await this.request<{data: {assessment: AssessmentResult}}>(
      `/session/${sessionId}/assess/`, 
      { method: 'POST' }
    );
    return response.data.assessment;
  }

  async getSessionStatus(sessionId: string): Promise<SessionStatus> {
    const response = await this.request<{data: {session: SessionStatus}}>(
      `/session/${sessionId}/status/`
    );
    return response.data.session;
  }

  async getResults(sessionId: string): Promise<AssessmentResults> {
    const response = await this.request<{data: {results: AssessmentResults}}>(
      `/session/${sessionId}/results/`
    );
    return response.data.results;
  }

  // Polling utility
  async pollForCompletion(
    sessionId: string, 
    onProgress?: (status: SessionStatus) => void
  ): Promise<AssessmentResults> {
    while (true) {
      const status = await this.getSessionStatus(sessionId);
      
      if (onProgress) {
        onProgress(status);
      }

      if (status.status === 'feedback_generated') {
        return this.getResults(sessionId);
      }

      if (status.status === 'failed') {
        throw new Error(`Assessment failed: ${status.error_message}`);
      }

      // Wait 2 seconds before next poll
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
}

// Type definitions
export interface Tutorial {
  id: string;
  name: string;
  description: string;
  difficulty: string;
  duration_seconds: number;
  total_frames: number;
}

export interface Session {
  id: string;
  tutorial: {
    id: string;
    name: string;
    description: string;
  };
  status: string;
  created_at: string;
  expires_at: string;
}

export interface SessionStatus {
  id: string;
  status: string;
  progress: {
    current_stage: string;
    completed_stages: string[];
    remaining_stages: string[];
    progress_percentage: number;
  };
  created_at: string;
  updated_at: string;
  estimated_completion: string;
  error_message?: string;
}

export class APIError extends Error {
  constructor(public code: string, message: string) {
    super(message);
    this.name = 'APIError';
  }
}
```

### 11.2 Usage Example

```typescript
// Example usage
async function assessUserPerformance() {
  const api = new KabaddiTrainerAPI('https://api.kabaddi-trainer.com/api');

  try {
    // 1. Get available tutorials
    const tutorials = await api.getTutorials();
    console.log('Available tutorials:', tutorials);

    // 2. Create session for hand_touch tutorial
    const handTouchTutorial = tutorials.find(t => t.name === 'hand_touch');
    const session = await api.createSession(handTouchTutorial.id);
    console.log('Session created:', session.id);

    // 3. Upload user video
    const videoFile = document.getElementById('videoInput').files[0];
    const uploadResult = await api.uploadVideo(session.id, videoFile);
    console.log('Video uploaded:', uploadResult);

    // 4. Trigger assessment
    const assessment = await api.triggerAssessment(session.id);
    console.log('Assessment started:', assessment);

    // 5. Poll for completion with progress updates
    const results = await api.pollForCompletion(session.id, (status) => {
      console.log(`Progress: ${status.progress.progress_percentage}%`);
      updateProgressBar(status.progress.progress_percentage);
    });

    // 6. Display results
    console.log('Assessment complete!');
    console.log('Overall score:', results.scores.overall);
    console.log('Feedback:', results.feedback.overall_assessment);
    
    displayResults(results);

  } catch (error) {
    if (error instanceof APIError) {
      console.error('API Error:', error.code, error.message);
    } else {
      console.error('Unexpected error:', error);
    }
  }
}
```

### 11.3 Python SDK

```python
# kabaddi_trainer_sdk.py
import requests
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class Tutorial:
    id: str
    name: str
    description: str
    difficulty: str
    duration_seconds: float
    total_frames: int

@dataclass 
class Session:
    id: str
    tutorial: Dict[str, Any]
    status: str
    created_at: str
    expires_at: str

class KabaddiTrainerAPI:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'X-API-Key': api_key})
        
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'KabaddiTrainer-Python-SDK/1.0'
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        
        if not response.ok:
            error_data = response.json()
            raise APIError(
                error_data['error']['code'], 
                error_data['error']['message']
            )
        
        return response.json()

    def get_tutorials(self) -> List[Tutorial]:
        """Get list of available tutorials"""
        response = self._request('GET', '/tutorials/')
        return [
            Tutorial(**tutorial) 
            for tutorial in response['data']['tutorials']
        ]

    def get_tutorial(self, tutorial_id: str) -> Tutorial:
        """Get specific tutorial details"""
        response = self._request('GET', f'/tutorials/{tutorial_id}/')
        return Tutorial(**response['data']['tutorial'])

    def get_ar_poses(self, tutorial_id: str) -> Dict[str, Any]:
        """Get AR pose data for tutorial"""
        response = self._request('GET', f'/tutorials/{tutorial_id}/ar-poses/')
        return response['data']

    def create_session(self, tutorial_id: str) -> Session:
        """Create new assessment session"""
        response = self._request(
            'POST', 
            '/session/start/',
            json={'tutorial_id': tutorial_id}
        )
        return Session(**response['data']['session'])

    def upload_video(self, session_id: str, video_path: str) -> Dict[str, Any]:
        """Upload video file for assessment"""
        with open(video_path, 'rb') as video_file:
            files = {'video': video_file}
            # Remove Content-Type header for multipart upload
            headers = {k: v for k, v in self.session.headers.items() 
                      if k.lower() != 'content-type'}
            
            response = requests.post(
                f"{self.base_url}/session/{session_id}/upload-video/",
                files=files,
                headers=headers
            )
            
            if not response.ok:
                error_data = response.json()
                raise APIError(
                    error_data['error']['code'],
                    error_data['error']['message']
                )
            
            return response.json()['data']['upload']

    def trigger_assessment(self, session_id: str) -> Dict[str, Any]:
        """Start assessment pipeline"""
        response = self._request('POST', f'/session/{session_id}/assess/')
        return response['data']['assessment']

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get current session status"""
        response = self._request('GET', f'/session/{session_id}/status/')
        return response['data']['session']

    def get_results(self, session_id: str) -> Dict[str, Any]:
        """Get assessment results"""
        response = self._request('GET', f'/session/{session_id}/results/')
        return response['data']['results']

    def poll_for_completion(
        self, 
        session_id: str, 
        poll_interval: int = 2,
        timeout: int = 600,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Poll session until completion"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_session_status(session_id)
            
            if progress_callback:
                progress_callback(status)
            
            if status['status'] == 'feedback_generated':
                return self.get_results(session_id)
            
            if status['status'] == 'failed':
                raise AssessmentError(f"Assessment failed: {status.get('error_message')}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Assessment did not complete within {timeout} seconds")

class APIError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")

class AssessmentError(Exception):
    pass

# Usage example
if __name__ == "__main__":
    api = KabaddiTrainerAPI('https://api.kabaddi-trainer.com/api')
    
    # Get tutorials
    tutorials = api.get_tutorials()
    print(f"Found {len(tutorials)} tutorials")
    
    # Create session
    hand_touch = next(t for t in tutorials if t.name == 'hand_touch')
    session = api.create_session(hand_touch.id)
    print(f"Created session: {session.id}")
    
    # Upload video and assess
    upload_result = api.upload_video(session.id, 'user_video.mp4')
    print(f"Video uploaded: {upload_result['file_info']['size']} bytes")
    
    assessment = api.trigger_assessment(session.id)
    print("Assessment started")
    
    # Poll for results
    def progress_callback(status):
        progress = status['progress']['progress_percentage']
        print(f"Progress: {progress}%")
    
    results = api.poll_for_completion(session.id, progress_callback=progress_callback)
    print(f"Assessment complete! Score: {results['scores']['overall']}")
```

---

## 12. Versioning Strategy

### 12.1 API Versioning Approach

**Strategy**: URL Path Versioning
- Current: `/api/v1/tutorials/`
- Future: `/api/v2/tutorials/`

**Version Support Policy**:
- **Current Version**: Full support and new features
- **Previous Version**: Bug fixes and security updates only
- **Deprecated Version**: 6-month sunset period with migration support

### 12.2 Backward Compatibility

**Breaking Changes** (require new version):
- Removing endpoints or fields
- Changing response structure
- Modifying authentication requirements
- Altering error codes or formats

**Non-Breaking Changes** (same version):
- Adding new endpoints
- Adding optional fields to requests
- Adding fields to responses
- Improving error messages

### 12.3 Migration Guide

**v1 to v2 Migration** (future):
```json
{
  "migration_guide": {
    "deprecated_endpoints": [
      {
        "old": "GET /api/v1/session/{id}/status/",
        "new": "GET /api/v2/sessions/{id}/",
        "changes": "Consolidated session endpoints"
      }
    ],
    "new_features": [
      {
        "feature": "Batch operations",
        "endpoint": "POST /api/v2/sessions/batch/",
        "description": "Create multiple sessions at once"
      }
    ],
    "timeline": {
      "v2_release": "2024-06-01",
      "v1_deprecation": "2024-12-01",
      "v1_sunset": "2025-06-01"
    }
  }
}
```

---

## 13. Conclusion

This API Specification Document provides comprehensive documentation for the AR-Based Kabaddi Ghost Trainer API. The API is designed with the following principles:

1. **RESTful Design**: Consistent, resource-based endpoints
2. **Security First**: UUID identifiers and comprehensive error handling
3. **Developer Experience**: Clear documentation and SDK support
4. **Scalability**: Rate limiting and performance considerations
5. **Reliability**: Detailed error responses and status tracking

The API supports the complete user journey from tutorial discovery through performance assessment and feedback delivery, enabling rich mobile AR experiences with robust backend processing.

---

**Document Control**:
- Version: 1.0
- Last Updated: 2024-01-15
- Next Review: 2024-04-15
- Approval: API Design Team