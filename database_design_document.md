# Database Design Document - AR-Based Kabaddi Ghost Trainer

## Document Information
- **Version**: 1.0
- **Date**: 2024-01-15
- **Author**: Database Design Team
- **Classification**: Technical Specification

---

## Table of Contents

1. [Database Overview](#database-overview)
2. [Conceptual Data Model](#conceptual-data-model)
3. [Logical Data Model](#logical-data-model)
4. [Physical Data Model](#physical-data-model)
5. [Data Dictionary](#data-dictionary)
6. [Constraints and Relationships](#constraints-and-relationships)
7. [Indexing Strategy](#indexing-strategy)
8. [Data Migration Scripts](#data-migration-scripts)
9. [Backup and Recovery](#backup-and-recovery)
10. [Performance Optimization](#performance-optimization)

---

## 1. Database Overview

### 1.1 Database Purpose

The database serves as the central repository for the AR-Based Kabaddi Ghost Trainer system, managing:
- Tutorial metadata and expert pose references
- User session lifecycle and status tracking
- File system references for media and results
- Pipeline execution results and analytics
- LLM-generated feedback and coaching data

### 1.2 Database Technology Stack

**Development Environment**:
- **DBMS**: SQLite 3.x
- **ORM**: Django ORM 4.2.x
- **Migration Tool**: Django Migrations
- **Admin Interface**: Django Admin

**Production Environment**:
- **DBMS**: PostgreSQL 15.x
- **Connection Pooling**: PgBouncer
- **Monitoring**: pg_stat_statements
- **Backup**: pg_dump + WAL archiving

### 1.3 Design Principles

1. **UUID Primary Keys**: All entities use UUID for security and distribution
2. **Cascade Relationships**: Proper foreign key constraints with cascade behavior
3. **Audit Trails**: Timestamp tracking for all entities
4. **Soft Deletes**: is_active flags instead of hard deletes where appropriate
5. **File References**: Store file paths, not binary data
6. **Status Tracking**: Explicit status fields for workflow management

---

## 2. Conceptual Data Model

### 2.1 Entity Relationship Overview

```
┌─────────────────┐
│    Tutorial     │
│                 │
│ • id (UUID)     │
│ • name          │
│ • description   │
│ • expert_pose   │
│ • is_active     │
│ • created_at    │
└─────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐
│  UserSession    │
│                 │
│ • id (UUID)     │
│ • tutorial_id   │
│ • status        │
│ • created_at    │
│ • updated_at    │
│ • error_message │
└─────────────────┘
         │
         ├─── 1:1 ───┐
         │           │
         ▼           ▼
┌─────────────────┐ ┌─────────────────┐
│    RawVideo     │ │  PoseArtifact   │
│                 │ │                 │
│ • id (UUID)     │ │ • id (UUID)     │
│ • session_id    │ │ • session_id    │
│ • file_path     │ │ • pose_path     │
│ • file_size     │ │ • generated_at  │
│ • uploaded_at   │ └─────────────────┘
│ • checksum      │
└─────────────────┘
         │
         │ 1:1
         ▼
┌─────────────────┐
│AnalyticalResults│
│                 │
│ • id (UUID)     │
│ • session_id    │
│ • scores_path   │
│ • errors_path   │
│ • align_path    │
│ • completed_at  │
└─────────────────┘
         │
         │ 1:1
         ▼
┌─────────────────┐
│   LLMFeedback   │
│                 │
│ • id (UUID)     │
│ • session_id    │
│ • feedback_text │
│ • audio_path    │
│ • generated_at  │
│ • llm_model     │
└─────────────────┘
```

### 2.2 Entity Descriptions

**Tutorial**: Master data for kabaddi movements and techniques
- Stores metadata for each available tutorial
- References expert pose files in the file system
- Supports soft deletion via is_active flag

**UserSession**: Central entity tracking user assessment sessions
- Links user attempts to specific tutorials
- Maintains detailed status progression through pipeline
- Stores error information for debugging

**RawVideo**: Immutable source artifact from user upload
- Stores original video file metadata
- Includes integrity checking via checksum
- One-to-one relationship with UserSession

**PoseArtifact**: Extracted and cleaned pose data
- References Level-1 cleaned pose files
- Generated from RawVideo through pose extraction
- Intermediate artifact for pipeline processing

**AnalyticalResults**: Pipeline output storage
- **CRITICAL**: Both scores_path AND errors_path are mandatory
- Level-3 Error Localization treated as first-class output
- Level-4 Similarity Scoring as summary metrics
- Optional alignment indices for debugging

**LLMFeedback**: AI-generated coaching feedback
- Text-based feedback derived from error metrics
- Optional audio feedback via TTS
- Tracks LLM model used for reproducibility

---

## 3. Logical Data Model

### 3.1 Entity Specifications

#### 3.1.1 Tutorial Entity

**Purpose**: Master data for kabaddi movement tutorials

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, NOT NULL | Unique identifier |
| name | VARCHAR(50) | UNIQUE, NOT NULL | Tutorial identifier (hand_touch, toe_touch, bonus) |
| description | TEXT | NOT NULL | Human-readable description |
| expert_pose_path | VARCHAR(255) | NOT NULL | Relative path to expert pose file |
| is_active | BOOLEAN | DEFAULT TRUE | Soft delete flag |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

**Business Rules**:
- Tutorial names must be unique across the system
- Expert pose files must exist in the file system
- Inactive tutorials are hidden from API but preserved for data integrity
- Tutorial deletion cascades to all associated sessions

#### 3.1.2 UserSession Entity

**Purpose**: Tracks individual user assessment sessions

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, NOT NULL | Unique session identifier |
| tutorial_id | UUID | FOREIGN KEY, NOT NULL | Reference to Tutorial |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'created' | Pipeline status |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Session creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last status update |
| error_message | TEXT | NULL | Error details for failed sessions |

**Status Values**:
```
created → video_uploaded → pose_extracted → level1_complete → 
level2_complete → level3_complete → scoring_complete → feedback_generated

failed (can occur at any stage)
```

**Business Rules**:
- Status transitions must follow the defined sequence
- Error messages are required for failed status
- Sessions cannot be deleted while in processing states
- Updated_at automatically updates on status changes

#### 3.1.3 RawVideo Entity

**Purpose**: Metadata for uploaded user videos

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, NOT NULL | Unique identifier |
| user_session_id | UUID | FOREIGN KEY, UNIQUE, NOT NULL | One-to-one with UserSession |
| file_path | VARCHAR(255) | NOT NULL | Absolute path to video file |
| file_size | BIGINT | NOT NULL | File size in bytes |
| uploaded_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Upload completion time |
| checksum | VARCHAR(64) | NULL | SHA-256 hash for integrity |

**Business Rules**:
- Each session can have exactly one video
- File paths must be absolute and accessible
- Checksum calculation is optional but recommended
- Video files are immutable once uploaded

#### 3.1.4 PoseArtifact Entity

**Purpose**: References to extracted pose data

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, NOT NULL | Unique identifier |
| user_session_id | UUID | FOREIGN KEY, UNIQUE, NOT NULL | One-to-one with UserSession |
| pose_level1_path | VARCHAR(255) | NOT NULL | Path to Level-1 cleaned poses |
| generated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Generation timestamp |

**Business Rules**:
- Generated from RawVideo through pose extraction pipeline
- Pose files must be in COCO-17 format (T, 17, 2)
- Level-1 cleaning is applied during generation
- Files are intermediate artifacts for pipeline processing

#### 3.1.5 AnalyticalResults Entity

**Purpose**: Pipeline output file references

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, NOT NULL | Unique identifier |
| user_session_id | UUID | FOREIGN KEY, UNIQUE, NOT NULL | One-to-one with UserSession |
| scores_json_path | VARCHAR(255) | NOT NULL | Level-4 similarity scores |
| error_metrics_json_path | VARCHAR(255) | NOT NULL | Level-3 error localization |
| alignment_indices_path | VARCHAR(255) | NULL | Level-2 alignment data |
| completed_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Pipeline completion time |

**Critical Design Notes**:
- **BOTH** scores_json_path AND error_metrics_json_path are MANDATORY
- Level-3 Error Localization is treated as first-class output, NOT optional
- Level-4 Similarity Scoring provides summary metrics
- Alignment indices are optional debugging information

#### 3.1.6 LLMFeedback Entity

**Purpose**: AI-generated coaching feedback

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, NOT NULL | Unique identifier |
| user_session_id | UUID | FOREIGN KEY, UNIQUE, NOT NULL | One-to-one with UserSession |
| feedback_text | TEXT | NOT NULL | Natural language feedback |
| audio_feedback_path | VARCHAR(255) | NULL | Optional TTS audio file |
| generated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Generation timestamp |
| llm_model_used | VARCHAR(100) | DEFAULT 'gpt-4' | LLM model identifier |

**Business Rules**:
- Feedback is generated from error_metrics.json, NOT raw video/poses
- Text feedback is mandatory, audio is optional
- LLM model tracking enables reproducibility
- Feedback generation failure does not fail the pipeline

---

## 4. Physical Data Model

### 4.1 PostgreSQL Schema Definition

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tutorial table
CREATE TABLE tutorials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    expert_pose_path VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User session table
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tutorial_id UUID NOT NULL REFERENCES tutorials(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    
    CONSTRAINT valid_status CHECK (status IN (
        'created', 'video_uploaded', 'pose_extracted', 'level1_complete',
        'level2_complete', 'level3_complete', 'scoring_complete', 
        'feedback_generated', 'failed'
    ))
);

-- Raw video table
CREATE TABLE raw_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_session_id UUID UNIQUE NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    file_path VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL CHECK (file_size > 0),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);

-- Pose artifact table
CREATE TABLE pose_artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_session_id UUID UNIQUE NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    pose_level1_path VARCHAR(255) NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Analytical results table
CREATE TABLE analytical_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_session_id UUID UNIQUE NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    scores_json_path VARCHAR(255) NOT NULL,
    error_metrics_json_path VARCHAR(255) NOT NULL,
    alignment_indices_path VARCHAR(255),
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- LLM feedback table
CREATE TABLE llm_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_session_id UUID UNIQUE NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    feedback_text TEXT NOT NULL,
    audio_feedback_path VARCHAR(255),
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    llm_model_used VARCHAR(100) DEFAULT 'gpt-4'
);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_sessions_updated_at 
    BEFORE UPDATE ON user_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 4.2 SQLite Schema (Development)

```sql
-- Tutorial table
CREATE TABLE tutorials (
    id TEXT PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    expert_pose_path VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User session table
CREATE TABLE user_sessions (
    id TEXT PRIMARY KEY,
    tutorial_id TEXT NOT NULL REFERENCES tutorials(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    
    CHECK (status IN (
        'created', 'video_uploaded', 'pose_extracted', 'level1_complete',
        'level2_complete', 'level3_complete', 'scoring_complete', 
        'feedback_generated', 'failed'
    ))
);

-- Raw video table
CREATE TABLE raw_videos (
    id TEXT PRIMARY KEY,
    user_session_id TEXT UNIQUE NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    file_path VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL CHECK (file_size > 0),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64)
);

-- Pose artifact table
CREATE TABLE pose_artifacts (
    id TEXT PRIMARY KEY,
    user_session_id TEXT UNIQUE NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    pose_level1_path VARCHAR(255) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analytical results table
CREATE TABLE analytical_results (
    id TEXT PRIMARY KEY,
    user_session_id TEXT UNIQUE NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    scores_json_path VARCHAR(255) NOT NULL,
    error_metrics_json_path VARCHAR(255) NOT NULL,
    alignment_indices_path VARCHAR(255),
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LLM feedback table
CREATE TABLE llm_feedback (
    id TEXT PRIMARY KEY,
    user_session_id TEXT UNIQUE NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    feedback_text TEXT NOT NULL,
    audio_feedback_path VARCHAR(255),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    llm_model_used VARCHAR(100) DEFAULT 'gpt-4'
);
```

---

## 5. Data Dictionary

### 5.1 Domain Definitions

| Domain | Data Type | Format | Description |
|--------|-----------|--------|-------------|
| UUID | UUID/TEXT | xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx | Universally unique identifier |
| TutorialName | VARCHAR(50) | hand_touch, toe_touch, bonus | Predefined tutorial identifiers |
| SessionStatus | VARCHAR(20) | See status enum | Pipeline execution status |
| FilePath | VARCHAR(255) | /absolute/path/to/file | Absolute file system path |
| FileSize | BIGINT | Positive integer | File size in bytes |
| Checksum | VARCHAR(64) | SHA-256 hex string | File integrity hash |
| LLMModel | VARCHAR(100) | gpt-4, claude-3, etc. | LLM model identifier |

### 5.2 Enumerated Values

**Tutorial Names**:
```
hand_touch  - Hand touch kabaddi movement
toe_touch   - Toe touch kabaddi movement  
bonus       - Bonus kabaddi movement
```

**Session Status Values**:
```
created           - Session initialized
video_uploaded    - Video file stored
pose_extracted    - Pose extraction completed
level1_complete   - Level-1 cleaning completed
level2_complete   - Level-2 alignment completed
level3_complete   - Level-3 error localization completed
scoring_complete  - Level-4 scoring completed
feedback_generated - LLM feedback generated
failed            - Pipeline failed at any stage
```

### 5.3 File Path Conventions

**Media Directory Structure**:
```
media/
├── raw_videos/           # Original user uploads
│   └── {session_uuid}.mp4
├── poses/               # Extracted pose sequences
│   └── {session_uuid}.npy
├── expert_poses/        # Reference trainer poses
│   ├── hand_touch.npy
│   ├── toe_touch.npy
│   └── bonus.npy
└── results/            # Pipeline outputs
    └── {session_uuid}/
        ├── scores.json
        ├── error_metrics.json
        ├── feedback.json
        ├── feedback.txt
        └── comparison.mp4
```

---

## 6. Constraints and Relationships

### 6.1 Primary Key Constraints

All tables use UUID primary keys for:
- **Security**: Prevents enumeration attacks
- **Distribution**: Enables database sharding
- **Uniqueness**: Globally unique across systems

### 6.2 Foreign Key Relationships

```sql
-- Tutorial → UserSession (1:N)
ALTER TABLE user_sessions 
ADD CONSTRAINT fk_session_tutorial 
FOREIGN KEY (tutorial_id) REFERENCES tutorials(id) ON DELETE CASCADE;

-- UserSession → RawVideo (1:1)
ALTER TABLE raw_videos 
ADD CONSTRAINT fk_video_session 
FOREIGN KEY (user_session_id) REFERENCES user_sessions(id) ON DELETE CASCADE;

-- UserSession → PoseArtifact (1:1)
ALTER TABLE pose_artifacts 
ADD CONSTRAINT fk_pose_session 
FOREIGN KEY (user_session_id) REFERENCES user_sessions(id) ON DELETE CASCADE;

-- UserSession → AnalyticalResults (1:1)
ALTER TABLE analytical_results 
ADD CONSTRAINT fk_results_session 
FOREIGN KEY (user_session_id) REFERENCES user_sessions(id) ON DELETE CASCADE;

-- UserSession → LLMFeedback (1:1)
ALTER TABLE llm_feedback 
ADD CONSTRAINT fk_feedback_session 
FOREIGN KEY (user_session_id) REFERENCES user_sessions(id) ON DELETE CASCADE;
```

### 6.3 Unique Constraints

```sql
-- Tutorial names must be unique
ALTER TABLE tutorials ADD CONSTRAINT unique_tutorial_name UNIQUE (name);

-- One-to-one relationships enforced by unique constraints
ALTER TABLE raw_videos ADD CONSTRAINT unique_session_video UNIQUE (user_session_id);
ALTER TABLE pose_artifacts ADD CONSTRAINT unique_session_pose UNIQUE (user_session_id);
ALTER TABLE analytical_results ADD CONSTRAINT unique_session_results UNIQUE (user_session_id);
ALTER TABLE llm_feedback ADD CONSTRAINT unique_session_feedback UNIQUE (user_session_id);
```

### 6.4 Check Constraints

```sql
-- Valid session status values
ALTER TABLE user_sessions ADD CONSTRAINT valid_session_status 
CHECK (status IN (
    'created', 'video_uploaded', 'pose_extracted', 'level1_complete',
    'level2_complete', 'level3_complete', 'scoring_complete', 
    'feedback_generated', 'failed'
));

-- Positive file sizes
ALTER TABLE raw_videos ADD CONSTRAINT positive_file_size 
CHECK (file_size > 0);

-- Non-empty required paths
ALTER TABLE analytical_results ADD CONSTRAINT non_empty_scores_path 
CHECK (LENGTH(TRIM(scores_json_path)) > 0);

ALTER TABLE analytical_results ADD CONSTRAINT non_empty_errors_path 
CHECK (LENGTH(TRIM(error_metrics_json_path)) > 0);
```

---

## 7. Indexing Strategy

### 7.1 Primary Indexes

```sql
-- Primary key indexes (automatically created)
CREATE UNIQUE INDEX idx_tutorials_pk ON tutorials(id);
CREATE UNIQUE INDEX idx_user_sessions_pk ON user_sessions(id);
CREATE UNIQUE INDEX idx_raw_videos_pk ON raw_videos(id);
CREATE UNIQUE INDEX idx_pose_artifacts_pk ON pose_artifacts(id);
CREATE UNIQUE INDEX idx_analytical_results_pk ON analytical_results(id);
CREATE UNIQUE INDEX idx_llm_feedback_pk ON llm_feedback(id);
```

### 7.2 Foreign Key Indexes

```sql
-- Foreign key indexes for join performance
CREATE INDEX idx_user_sessions_tutorial_id ON user_sessions(tutorial_id);
CREATE INDEX idx_raw_videos_session_id ON raw_videos(user_session_id);
CREATE INDEX idx_pose_artifacts_session_id ON pose_artifacts(user_session_id);
CREATE INDEX idx_analytical_results_session_id ON analytical_results(user_session_id);
CREATE INDEX idx_llm_feedback_session_id ON llm_feedback(user_session_id);
```

### 7.3 Query Optimization Indexes

```sql
-- Active tutorials lookup
CREATE INDEX idx_tutorials_active ON tutorials(is_active) WHERE is_active = TRUE;

-- Session status queries
CREATE INDEX idx_user_sessions_status ON user_sessions(status);

-- Time-based queries
CREATE INDEX idx_user_sessions_created_at ON user_sessions(created_at);
CREATE INDEX idx_user_sessions_updated_at ON user_sessions(updated_at);
CREATE INDEX idx_raw_videos_uploaded_at ON raw_videos(uploaded_at);

-- Composite indexes for common queries
CREATE INDEX idx_sessions_tutorial_status ON user_sessions(tutorial_id, status);
CREATE INDEX idx_sessions_status_updated ON user_sessions(status, updated_at);
```

### 7.4 Partial Indexes

```sql
-- Failed sessions for monitoring
CREATE INDEX idx_failed_sessions ON user_sessions(created_at) 
WHERE status = 'failed';

-- Processing sessions for monitoring
CREATE INDEX idx_processing_sessions ON user_sessions(updated_at) 
WHERE status NOT IN ('feedback_generated', 'failed');

-- Large video files for cleanup
CREATE INDEX idx_large_videos ON raw_videos(file_size, uploaded_at) 
WHERE file_size > 50 * 1024 * 1024; -- > 50MB
```

---

## 8. Data Migration Scripts

### 8.1 Initial Data Setup

```sql
-- Insert default tutorials
INSERT INTO tutorials (id, name, description, expert_pose_path) VALUES
(uuid_generate_v4(), 'hand_touch', 'Hand touch kabaddi movement', 'expert_poses/hand_touch.npy'),
(uuid_generate_v4(), 'toe_touch', 'Toe touch kabaddi movement', 'expert_poses/toe_touch.npy'),
(uuid_generate_v4(), 'bonus', 'Bonus kabaddi movement', 'expert_poses/bonus.npy');
```

### 8.2 Django Migration Files

**0001_initial.py**:
```python
from django.db import migrations, models
import uuid

class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Tutorial',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('name', models.CharField(max_length=50, unique=True)),
                ('description', models.TextField()),
                ('expert_pose_path', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, primary_key=True)),
                ('status', models.CharField(
                    choices=[
                        ('created', 'Created'),
                        ('video_uploaded', 'Video Uploaded'),
                        ('pose_extracted', 'Pose Extracted'),
                        ('level1_complete', 'Level-1 Complete'),
                        ('level2_complete', 'Level-2 Complete'),
                        ('level3_complete', 'Level-3 Complete'),
                        ('scoring_complete', 'Scoring Complete'),
                        ('feedback_generated', 'Feedback Generated'),
                        ('failed', 'Failed'),
                    ],
                    default='created',
                    max_length=20
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('tutorial', models.ForeignKey(
                    on_delete=models.CASCADE, 
                    to='api.tutorial'
                )),
            ],
        ),
        # ... other models
    ]
```

### 8.3 Data Validation Scripts

```python
# validate_data_integrity.py
import os
from django.core.management.base import BaseCommand
from api.models import Tutorial, UserSession, RawVideo, AnalyticalResults

class Command(BaseCommand):
    help = 'Validate data integrity across the system'

    def handle(self, *args, **options):
        self.validate_tutorials()
        self.validate_file_references()
        self.validate_session_consistency()

    def validate_tutorials(self):
        """Ensure all tutorial expert poses exist"""
        for tutorial in Tutorial.objects.filter(is_active=True):
            pose_path = settings.MEDIA_ROOT / tutorial.expert_pose_path
            if not pose_path.exists():
                self.stdout.write(
                    self.style.ERROR(
                        f'Missing expert pose: {tutorial.name} -> {pose_path}'
                    )
                )

    def validate_file_references(self):
        """Check that all file references point to existing files"""
        # Check raw videos
        for video in RawVideo.objects.all():
            if not os.path.exists(video.file_path):
                self.stdout.write(
                    self.style.ERROR(f'Missing video file: {video.file_path}')
                )

        # Check analytical results
        for result in AnalyticalResults.objects.all():
            if not os.path.exists(result.scores_json_path):
                self.stdout.write(
                    self.style.ERROR(f'Missing scores file: {result.scores_json_path}')
                )
            if not os.path.exists(result.error_metrics_json_path):
                self.stdout.write(
                    self.style.ERROR(f'Missing error metrics: {result.error_metrics_json_path}')
                )

    def validate_session_consistency(self):
        """Check session status consistency"""
        for session in UserSession.objects.all():
            # Sessions with results should have scoring_complete or feedback_generated
            if hasattr(session, 'analyticalresults'):
                if session.status not in ['scoring_complete', 'feedback_generated']:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Session {session.id} has results but status is {session.status}'
                        )
                    )
```

---

## 9. Backup and Recovery

### 9.1 Backup Strategy

**PostgreSQL Backup**:
```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/backups/database"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="kabaddi_trainer"

# Create backup directory
mkdir -p $BACKUP_DIR

# Full database backup
pg_dump -h localhost -U postgres -d $DB_NAME \
    --format=custom \
    --compress=9 \
    --file="$BACKUP_DIR/kabaddi_trainer_$TIMESTAMP.backup"

# Schema-only backup
pg_dump -h localhost -U postgres -d $DB_NAME \
    --schema-only \
    --file="$BACKUP_DIR/schema_$TIMESTAMP.sql"

# Data-only backup
pg_dump -h localhost -U postgres -d $DB_NAME \
    --data-only \
    --format=custom \
    --file="$BACKUP_DIR/data_$TIMESTAMP.backup"

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.backup" -mtime +30 -delete
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete

echo "Backup completed: $TIMESTAMP"
```

**File System Backup**:
```bash
#!/bin/bash
# backup_media.sh

MEDIA_DIR="/app/media"
BACKUP_DIR="/backups/media"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create incremental backup
rsync -av --link-dest="$BACKUP_DIR/latest" \
    "$MEDIA_DIR/" \
    "$BACKUP_DIR/backup_$TIMESTAMP/"

# Update latest symlink
rm -f "$BACKUP_DIR/latest"
ln -s "backup_$TIMESTAMP" "$BACKUP_DIR/latest"

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -maxdepth 1 -name "backup_*" -mtime +7 -exec rm -rf {} \;

echo "Media backup completed: $TIMESTAMP"
```

### 9.2 Recovery Procedures

**Database Recovery**:
```bash
#!/bin/bash
# restore_database.sh

BACKUP_FILE=$1
DB_NAME="kabaddi_trainer"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Drop existing database (CAUTION!)
dropdb -h localhost -U postgres $DB_NAME

# Create new database
createdb -h localhost -U postgres $DB_NAME

# Restore from backup
pg_restore -h localhost -U postgres -d $DB_NAME \
    --verbose \
    --clean \
    --if-exists \
    "$BACKUP_FILE"

echo "Database restored from: $BACKUP_FILE"
```

### 9.3 Disaster Recovery Plan

**Recovery Time Objectives (RTO)**:
- Database: 30 minutes
- File System: 1 hour
- Full System: 2 hours

**Recovery Point Objectives (RPO)**:
- Database: 1 hour (hourly backups)
- File System: 24 hours (daily backups)

**Recovery Steps**:
1. Assess damage and determine recovery scope
2. Restore database from latest backup
3. Restore file system from latest backup
4. Validate data integrity
5. Restart application services
6. Verify system functionality

---

## 10. Performance Optimization

### 10.1 Query Optimization

**Common Query Patterns**:
```sql
-- Get active tutorials (optimized with partial index)
SELECT id, name, description 
FROM tutorials 
WHERE is_active = TRUE
ORDER BY name;

-- Get session with all related data (optimized with joins)
SELECT 
    s.id, s.status, s.created_at,
    t.name as tutorial_name,
    r.file_size,
    ar.completed_at as results_completed
FROM user_sessions s
JOIN tutorials t ON s.tutorial_id = t.id
LEFT JOIN raw_videos r ON s.id = r.user_session_id
LEFT JOIN analytical_results ar ON s.id = ar.user_session_id
WHERE s.id = $1;

-- Get processing sessions for monitoring
SELECT id, status, updated_at, error_message
FROM user_sessions 
WHERE status NOT IN ('feedback_generated', 'failed')
ORDER BY updated_at DESC;
```

### 10.2 Connection Pooling

**PgBouncer Configuration**:
```ini
[databases]
kabaddi_trainer = host=localhost port=5432 dbname=kabaddi_trainer

[pgbouncer]
listen_port = 6432
listen_addr = 127.0.0.1
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
logfile = /var/log/pgbouncer/pgbouncer.log
pidfile = /var/run/pgbouncer/pgbouncer.pid
admin_users = postgres
stats_users = stats, postgres

pool_mode = transaction
server_reset_query = DISCARD ALL
max_client_conn = 100
default_pool_size = 20
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 5
max_db_connections = 50
```

### 10.3 Monitoring Queries

```sql
-- Session status distribution
SELECT status, COUNT(*) as count
FROM user_sessions 
GROUP BY status
ORDER BY count DESC;

-- Average processing times by status
SELECT 
    status,
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_seconds
FROM user_sessions 
WHERE status != 'created'
GROUP BY status
ORDER BY avg_seconds DESC;

-- File system usage
SELECT 
    SUM(file_size) as total_bytes,
    COUNT(*) as file_count,
    AVG(file_size) as avg_file_size
FROM raw_videos;

-- Failed sessions analysis
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(*) as failed_count
FROM user_sessions 
WHERE status = 'failed'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC;
```

### 10.4 Maintenance Tasks

```sql
-- Vacuum and analyze tables (PostgreSQL)
VACUUM ANALYZE tutorials;
VACUUM ANALYZE user_sessions;
VACUUM ANALYZE raw_videos;
VACUUM ANALYZE pose_artifacts;
VACUUM ANALYZE analytical_results;
VACUUM ANALYZE llm_feedback;

-- Update table statistics
ANALYZE tutorials;
ANALYZE user_sessions;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_tup_read DESC;
```

---

## 11. Conclusion

This Database Design Document provides comprehensive specifications for the AR-Based Kabaddi Ghost Trainer database system. Key design decisions include:

1. **UUID Primary Keys**: Enhanced security and distribution capability
2. **Cascade Relationships**: Proper data integrity and cleanup
3. **Status Tracking**: Detailed pipeline progress monitoring
4. **File References**: Separation of binary data and metadata
5. **Mandatory Outputs**: Both scores and error metrics as required results
6. **Performance Optimization**: Strategic indexing and query optimization

The design supports the complete user journey from tutorial selection through performance assessment, with robust data integrity, performance, and scalability considerations.

---

**Document Control**:
- Version: 1.0
- Last Updated: 2024-01-15
- Next Review: 2024-04-15
- Approval: Database Design Team