"""
Kabaddi Ghost Trainer - Flask Backend API
Provides REST endpoints for frontend demo website
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
import cv2

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent  # Project root (kabaddi_trainer/)
UPLOAD_FOLDER = Path(__file__).parent / 'data'  # backend/data/
EXPERT_FOLDER = UPLOAD_FOLDER / 'expert_poses'
USER_FOLDER = UPLOAD_FOLDER / 'user_uploads'
RESULTS_FOLDER = UPLOAD_FOLDER / 'results'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Create directories
for folder in [EXPERT_FOLDER, USER_FOLDER, RESULTS_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)

# In-memory database (for demo - use a real DB in production)
expert_poses_db = []


# Helper Functions
# =============================================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_thumbnail(video_path, output_path):
    """Generate thumbnail from video first frame"""
    try:
        cap = cv2.VideoCapture(str(video_path))
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(str(output_path), frame)
            return True
        return False
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return False


def get_video_duration(video_path):
    """Get video duration in seconds"""
    try:
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        
        if fps > 0:
            duration = frame_count / fps
            return f"{int(duration)}s"
        return "N/A"
    except:
        return "N/A"


# API Endpoints
# =============================================================================

@app.route('/api/admin/upload-expert', methods=['POST'])
def upload_expert_pose():
    """Upload expert pose video"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        name = request.form.get('name', 'Unnamed Pose')
        description = request.form.get('description', '')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Generate unique ID
        pose_id = str(uuid.uuid4())
        
        # Save video
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        video_filename = f"{pose_id}.{ext}"
        video_path = EXPERT_FOLDER / video_filename
        file.save(str(video_path))
        
        # Generate thumbnail
        thumbnail_filename = f"{pose_id}_thumb.jpg"
        thumbnail_path = EXPERT_FOLDER / thumbnail_filename
        generate_thumbnail(video_path, thumbnail_path)
        
        # Get video duration
        duration = get_video_duration(video_path)
        
        # Save to database
        pose_data = {
            'id': pose_id,
            'name': name,
            'description': description,
            'video_url': f'/data/expert_poses/{video_filename}',
            'thumbnail': f'/data/expert_poses/{thumbnail_filename}',
            'duration': duration,
            'uploaded_at': datetime.now().isoformat()
        }
        expert_poses_db.append(pose_data)
        
        # Save DB to JSON file
        db_file = UPLOAD_FOLDER / 'poses_db.json'
        with open(db_file, 'w') as f:
            json.dump(expert_poses_db, f, indent=2)
        
        return jsonify({
            'success': True,
            'pose_id': pose_id,
            'message': 'Expert pose uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/poses', methods=['GET'])
def get_expert_poses():
    """Get list of all expert poses"""
    # Load from JSON file if exists
    db_file = UPLOAD_FOLDER / 'poses_db.json'
    if db_file.exists():
        with open(db_file, 'r') as f:
            poses = json.load(f)
        return jsonify(poses)
    
    return jsonify(expert_poses_db)


@app.route('/api/upload-user-video', methods=['POST'])
def upload_user_video():
    """Upload user video for analysis"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        pose_id = request.form.get('pose_id')
        
        if not pose_id:
            return jsonify({'error': 'Pose ID required'}), 400
        
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Save user video
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        user_video_filename = f"user_{session_id}.{ext}"
        user_video_path = USER_FOLDER / user_video_filename
        file.save(str(user_video_path))
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'video_path': str(user_video_path)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    """Trigger pipeline analysis"""
    try:
        data = request.json
        session_id = data.get('session_id')
        pose_id = data.get('pose_id')
        user_video_path = data.get('user_video_path')
        
        if not all([session_id, pose_id, user_video_path]):
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Import pipeline runner
        from pipeline_runner import run_analysis_pipeline
        
        # Run pipeline
        result = run_analysis_pipeline(
            session_id=session_id,
            pose_id=pose_id,
            user_video_path=user_video_path
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/results/<session_id>', methods=['GET'])
def get_results(session_id):
    """Get analysis results for a session"""
    try:
        results_file = RESULTS_FOLDER / session_id / 'results.json'
        
        if not results_file.exists():
            return jsonify({'error': 'Results not found'}), 404
        
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/results/<session_id>/download', methods=['GET'])
def download_results(session_id):
    """Download complete results as JSON"""
    try:
        results_file = RESULTS_FOLDER / session_id / 'results.json'
        
        if not results_file.exists():
            return jsonify({'error': 'Results not found'}), 404
        
        return send_file(results_file, as_attachment=True, download_name=f'results_{session_id}.json')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/review1/videos', methods=['GET'])
def get_review1_videos():
    """Get list of all review1 demo videos"""
    review1_dir = BASE_DIR / 'review1'
    
    videos = {
        'level1': [],
        'level2': [],
        'level3': [],
        'level4': []
    }
    
    # Level 1 videos
    level1_output = review1_dir / 'level1_pose' / 'outputs'
    if level1_output.exists():
        for video in sorted(level1_output.glob('*.mp4')):
            videos['level1'].append({
                'name': video.name,
                'path': str(video.relative_to(BASE_DIR))
            })
    
    # Level 2 videos
    level2_output = review1_dir / 'level2' / 'Outputs'
    if level2_output.exists():
        for video in sorted(level2_output.glob('*.mp4')):
            videos['level2'].append({
                'name': video.name,
                'path': str(video.relative_to(BASE_DIR))
            })
    
    # Level 3 videos
    level3_output = review1_dir / 'visualization' / 'level3'
    if level3_output.exists():
        for video in level3_output.glob('*.mp4'):
            videos['level3'].append({
                'name': video.name,
                'path': str(video.relative_to(BASE_DIR))
            })
    
    # Level 4 videos
    level4_output = review1_dir / 'visualization' / 'level4'
    if level4_output.exists():
        for video in level4_output.glob('*.mp4'):
            videos['level4'].append({
                'name': video.name,
                'path': str(video.relative_to(BASE_DIR))
            })
    
    return jsonify(videos)


# Static file serving for video/data
@app.route('/data/<path:filename>')
def serve_data(filename):
    """Serve uploaded files"""
    return send_file(UPLOAD_FOLDER / filename)


@app.route('/review1/<path:filename>')
def serve_review1(filename):
    """Serve review1 demo files"""
    file_path = BASE_DIR / 'review1' / filename
    print(f"Attempting to serve: {file_path}")
    print(f"File exists: {file_path.exists()}")
    if not file_path.exists():
        return jsonify({'error': 'File not found', 'path': str(file_path)}), 404
    return send_file(file_path)


# Main
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("Kabaddi Ghost Trainer - Backend API Server")
    print("=" * 70)
    print(f"Base Directory: {BASE_DIR}")
    print(f"Data Directory: {UPLOAD_FOLDER}")
    print(f"\nStarting server at http://localhost:5000")
    print("=" * 70)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
