# Kabaddi Ghost Trainer - Frontend Demo Website

This is the demonstration website for the Kabaddi Ghost Trainer project, featuring:
- **Admin Panel**: Upload expert pose videos
- **User Dashboard**: Select and analyze poses
- **Results Viewer**: View all 4 pipeline levels
- **Demo Gallery**: Browse all review1 videos

## Project Structure

```
frontend/
├── backend/
│   ├── app.py                 # Flask API server
│   ├── pipeline_runner.py     # Pipeline integration
│   ├── requirements.txt       # Python dependencies
│   └── data/                  # File storage
│       ├── expert_poses/
│       ├── user_uploads/
│       └── results/
├── index.html                 # Landing page
├── admin.html                 # Admin panel
├── dashboard.html             # User dashboard
├── upload.html                # Upload page
├── results.html               # Results viewer
├── gallery.html               # Demo gallery
├── style.css                  # Design system
└── app.js                     # JavaScript utilities
```

## Quick Start

### 1. Install Backend Dependencies

```bash
cd frontend/backend
pip install -r requirements.txt
```

### 2. Start Backend Server

```bash
python app.py
```

Server will start at `http://localhost:5000`

### 3. Open Frontend

Open `frontend/index.html` in your browser, or use a simple HTTP server:

```bash
# Python 3
cd frontend
python -m http.server 8000

# Then open http://localhost:8000
```

## Features

### Admin Panel (`admin.html`)
- Upload expert pose videos
- Add name and description
- Auto-generate thumbnails
- View existing poses

### User Dashboard (`dashboard.html`)
- Browse expert poses as cards
- Video preview on hover
- Select pose for analysis

### Upload Page (`upload.html`)
- Upload user video
- Video preview
- File validation
- Progress tracking

### Results Page (`results.html`)
- Overall scores (structural, temporal, overall)
- All 4 pipeline levels:
  - Level-1: Pose extraction & cleaning
  - Level-2: Temporal alignment (DTW)
  - Level-3: Error localization
  - Level-4: Similarity scoring
- Joint error statistics
- Download results as JSON

### Gallery (`gallery.html`)
- All 12 review1 demo videos
- Organized by pipeline level
- Inline video players

## API Endpoints

### Expert Pose Management
- **POST** `/api/admin/upload-expert` - Upload expert video
- **GET** `/api/poses` - List all expert poses

### User Analysis
- **POST** `/api/upload-user-video` - Upload user video
- **POST** `/api/analyze` - Trigger pipeline execution
- **GET** `/api/results/<session_id>` - Get analysis results
- **GET** `/api/results/<session_id>/download` - Download JSON results

### Demo Content
- **GET** `/api/review1/videos` - List review1 demo videos

## Color Palette

The design uses a modern dark theme inspired by the provided reference:

- **Background**: `#0a0e1a` (primary), `#0d1117` (secondary)
- **Accent Blue**: `#1e59f2` (interactive elements)
- **Success Green**: `#00ff87` (complete states)
- **Text**: White primary, `#8b949e` secondary
- **Borders**: Subtle dark with accent highlights

## Technology Stack

**Frontend**:
- HTML5 + CSS3 (Vanilla)
- JavaScript (ES6+)
- Inter font family
- Responsive grid layouts

**Backend**:
- Flask 3.0
- Flask-CORS
- OpenCV (thumbnail generation)
- Integration with existing pipeline

**Pipeline Integration**:
- Executes `run_pipeline.py`
- Runs `level1_pose/pose_extract_cli.py`
- Organizes results automatically

## Workflow

1. **Admin uploads expert pose** → Saved to `expert_poses/`
2. **User selects pose** → Stored in sessionStorage
3. **User uploads video** → Saved to `user_uploads/`
4. **Pipeline executes**:
   - Extract expert pose (if needed)
   - Extract user pose
   - Run complete 4-level pipeline
   - Generate visualizations
5. **Results displayed** → All videos + scores + JSON data

## Notes

- Videos support: MP4, AVI, MOV, MKV
- Max file size: 100MB
- Sessions auto-cleanup after 7 days (configurable)
- All poses stored in COCO-17 format
- DTW alignment handles speed variations
- Color-coded error visualization

## Development

To modify the design:
1. Edit `style.css` for styling changes
2. CSS variables at the top for easy theming
3. All pages use the same design system

To add new API endpoints:
1. Add route in `backend/app.py`
2. Update `app.js` if needed
3. Modify frontend pages to call new endpoint

## Troubleshooting

**Backend not connecting**:
- Ensure Flask server is running on port 5000
- Check CORS is enabled
- Verify paths in `app.py`

**Videos not playing**:
- Check video codec (H.264 recommended)
- Ensure paths are correct
- Check browser console for errors

**Pipeline fails**:
- Verify all dependencies installed
- Check `run_pipeline.py` works standalone
- Review pipeline logs in terminal

## Credits

- **Project**: MCA SEM 4 - Kabaddi Ghost Trainer
- **Pipeline**: YOLO + MediaPipe + DTW + Error Analysis
- **Design**: Inspired by modern developer tools
- **Colors**: Based on provided reference image
