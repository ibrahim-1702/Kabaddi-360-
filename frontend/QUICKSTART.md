# Quick Start Guide - Kabaddi Ghost Trainer Frontend

## Setup (First Time Only)

### Option 1: Automated Setup (Recommended)

Simply run the batch file:

```bash
cd frontend
start_server.bat
```

This will automatically:
1. Install Python dependencies
2. Initialize database with "The Bonus" expert pose
3. Start the Flask backend server

### Option 2: Manual Setup

```bash
# 1. Install dependencies
cd frontend/backend
pip install -r requirements.txt

# 2. Initialize database
python init_database.py

# 3. Start server
python app.py
```

## Opening the Frontend

After the backend server is running at `http://localhost:5000`:

1. Open `frontend/index.html` in your browser
2. Or use Python's HTTP server:
   ```bash
   cd frontend
   python -m http.server 8000
   ```
   Then open: `http://localhost:8000`

## What's Pre-loaded

The database initialization automatically adds:

- **Pose Name**: "The Bonus"
- **Source**: `samples/kabaddi_clip.mp4`
- **Description**: Professional Kabaddi raider executing standard raid movement
- **Location**: `frontend/backend/data/expert_poses/the-bonus-001.mp4`

## Troubleshooting

### "Error loading expert poses"

**Cause**: Backend server not running  
**Fix**: Make sure Flask server is started (`python backend/app.py`)

### "Videos not loading in Gallery"

**Cause**: Backend server not accessible  
**Fix**: Ensure server is running on `http://localhost:5000`

### "ModuleNotFoundError: No module named 'flask'"

**Cause**: Dependencies not installed  
**Fix**: Run `pip install -r backend/requirements.txt`

### "Failed to load resource: 404"

**Cause**: Video files missing from review1 folder  
**Fix**: Ensure all review1 output videos exist in their respective directories

## File Locations

- **Expert Poses**: `frontend/backend/data/expert_poses/`
- **User Uploads**: `frontend/backend/data/user_uploads/`
- **Analysis Results**: `frontend/backend/data/results/`
- **Database**: `frontend/backend/data/poses_db.json`

## Next Steps

1. **Dashboard**: Browse and select "The Bonus" expert pose
2. **Upload**: Submit your video attempt
3. **Results**: View complete 4-level analysis
4. **Gallery**: Explore all 12 review1 demo videos
5. **Admin**: Upload additional expert poses

## Important Notes

- Backend must be running for frontend to work
- Gallery videos require backend server (served via Flask)
- All video paths now use `http://localhost:5000` prefix
- Database persists between server restarts
