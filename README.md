# Kabaddi Ghost Trainer

AI-powered Kabaddi movement analysis system using computer vision and temporal alignment algorithms for real-time pose comparison and feedback generation.

## Features

- **Pose Extraction**: YOLO person detection + MediaPipe pose estimation (COCO-17 format)
- **Temporal Alignment**: Dynamic Time Warping (DTW) for movement synchronization
- **Error Localization**: Frame-wise joint error computation with phase segmentation
- **Similarity Scoring**: 0-100 scale performance assessment
- **Real-time Feedback**: AI-powered coaching insights
- **Visual Results**: Side-by-side skeleton comparison videos

## Architecture

4-level pipeline processing:
1. **Level 1**: Pose extraction and cleaning
2. **Level 2**: Temporal alignment using DTW
3. **Level 3**: Error localization and analysis
4. **Level 4**: Similarity scoring and feedback generation

## Quick Start

### Frontend (Web Interface)
```bash
cd frontend
python backend/app.py
```
Open `http://localhost:5000` in your browser.

### Django Backend
```bash
cd kabaddi_backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Level 1 Pose Pipeline
```bash
cd level1_pose
pip install -r requirements.txt
python demo_run.py
```

## Project Structure

```
kabaddi_trainer/
├── frontend/           # Web interface and Flask backend
├── kabaddi_backend/    # Django REST API
├── level1_pose/        # Core pose extraction pipeline
├── documents/          # Algorithm documentation
├── samples/            # Test videos and data
└── legacy/             # Deprecated code
```

## Requirements

- Python 3.8+
- OpenCV
- MediaPipe
- YOLO v8
- NumPy
- Flask/Django

## Input Format

- Video files (MP4)
- Pose data: numpy.ndarray shape (T, 17, 2) - COCO-17 skeleton format

## Development Status

✅ Level 1: Pose extraction pipeline  
✅ Level 2: Temporal alignment  
✅ Level 3: Error localization  
✅ Level 4: Similarity scoring  
✅ Web interface  
✅ Django backend  

## License

Academic project - MCA Semester 4