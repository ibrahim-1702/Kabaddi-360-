"""
Extracts expert pose .npy files for footwork techniques and registers
them as Tutorial entries in the Django DB.

Run from kabaddi_backend/:
    python preprocess_footwork.py
"""
import os
import sys
import subprocess
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kabaddi_backend.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from api.models import Tutorial

PYTHON_EXEC = settings.PYTHON_EXEC
EXTRACT_SCRIPT = str(settings.EXTRACT_POSE_SCRIPT)
EXPERT_POSES_DIR = settings.MEDIA_ROOT / 'expert_poses'

PROJECT_ROOT = settings.BASE_DIR.parent

TECHNIQUES = [
    {
        'name': 'cross_foot_dose',
        'description': 'Cross foot dose — lateral footwork technique',
        'video': str(PROJECT_ROOT / 'samples' / '3D' / 'Techniques' / 'FootWork' / 'USE' / 'cross_foot_dose.mp4'),
    },
    {
        'name': 'footwork_crosslegs_shuffle',
        'description': 'Cross-legs shuffle — evasive footwork technique',
        'video': str(PROJECT_ROOT / 'samples' / '3D' / 'Techniques' / 'FootWork' / 'USE' / 'footwork_crosslegs_shuffle.mp4'),
    },
    {
        'name': 'footwork1',
        'description': 'Footwork pattern 1 — basic agility drill',
        'video': str(PROJECT_ROOT / 'samples' / '3D' / 'Techniques' / 'FootWork' / 'USE' / 'footwork1.mp4'),
    },
    {
        'name': 'footwork2',
        'description': 'Footwork pattern 2 — advanced agility drill',
        'video': str(PROJECT_ROOT / 'samples' / '3D' / 'Techniques' / 'FootWork' / 'USE' / 'footwork2.mp4'),
    },
]

python_cmd = PYTHON_EXEC.split() if isinstance(PYTHON_EXEC, str) else [PYTHON_EXEC]

for t in TECHNIQUES:
    npy_path = EXPERT_POSES_DIR / f"{t['name']}.npy"
    expert_pose_rel = f"expert_poses/{t['name']}.npy"

    # Step 1: Extract pose
    if npy_path.exists():
        print(f"[SKIP] Pose already exists: {npy_path.name}")
    else:
        print(f"[EXTRACT] {t['name']} from {os.path.basename(t['video'])} ...")
        result = subprocess.run(
            [*python_cmd, EXTRACT_SCRIPT, t['video'], str(npy_path)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr[-300:]}")
            continue
        print(f"  OK -> {npy_path.name}")

    # Step 2: Register in DB
    tutorial, created = Tutorial.objects.get_or_create(
        name=t['name'],
        defaults={
            'description': t['description'],
            'expert_pose_path': expert_pose_rel,
            'is_active': True,
        }
    )
    if created:
        print(f"[DB] Created tutorial: {t['name']}")
    else:
        print(f"[DB] Already exists: {t['name']}")

print("\nDone.")
