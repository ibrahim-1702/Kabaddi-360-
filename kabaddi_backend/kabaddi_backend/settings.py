import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Add parent directory to Python path for llm_feedback module
PROJECT_ROOT = BASE_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

SECRET_KEY = 'django-insecure-kabaddi-trainer-dev-key'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'api',
    'llm_feedback',
]

MIDDLEWARE = [
    'kabaddi_backend.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
]


ROOT_URLCONF = 'kabaddi_backend.urls'

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

WSGI_APPLICATION = 'kabaddi_backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Create media directories
os.makedirs(MEDIA_ROOT / 'raw_videos', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'poses', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'expert_poses', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'results', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'animations', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'tts_audio', exist_ok=True)

# Pipeline paths
PIPELINE_BASE_DIR = Path(__file__).resolve().parent.parent.parent / 'level1_pose'
EXTRACT_POSE_SCRIPT = PIPELINE_BASE_DIR / 'pose_extract_cli.py'
RUN_PIPELINE_SCRIPT = Path(__file__).resolve().parent.parent.parent / 'run_pipeline.py'

# ML execution requires Python 3.10 (has mediapipe, ultralytics, lapx)
import shutil
_PY310 = shutil.which('py')
PYTHON_EXEC = f'{_PY310} -3.10' if _PY310 else sys.executable

VALID_TUTORIALS = ['hand_touch', 'toe_touch', 'bonus', 'cross_foot_dose', 'footwork_crosslegs_shuffle', 'footwork1', 'footwork2']

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'