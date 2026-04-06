import os
import sys
import django
import subprocess

sys.path.append(r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\kabaddi_backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kabaddi_backend.settings")
django.setup()

from api.models import UserSession
from django.conf import settings

session_id = '1ee12261-a6e6-4692-a888-84ff4a5ee47f'
session = UserSession.objects.get(id=session_id)

video_path = session.rawvideo.file_path
pose_path = settings.MEDIA_ROOT / 'poses' / f'{session_id}.npy'

print(f"Video Path: {video_path}")
print(f"Pose Path: {pose_path}")

try:
    print("Running extraction...")
    extract_cmd = [
        sys.executable, 
        str(settings.EXTRACT_POSE_SCRIPT),
        str(video_path), 
        str(pose_path)
    ]
    res = subprocess.run(extract_cmd, capture_output=True, text=True, check=True)
    print("Extraction successful:", res.stdout)
except subprocess.CalledProcessError as e:
    print("EXTRACTION FAILED")
    print("STDERR:", e.stderr)
    print("STDOUT:", e.stdout)
    sys.exit(1)

expert_pose_path = settings.MEDIA_ROOT / 'expert_poses' / f'{session.tutorial.name}.npy'

results_dir = settings.MEDIA_ROOT / 'results' / session_id
os.makedirs(results_dir, exist_ok=True)

try:
    print("Running pipeline...")
    pipeline_cmd = [
        sys.executable, 
        str(settings.RUN_PIPELINE_SCRIPT),
        '--expert-pose', str(expert_pose_path),
        '--user-pose', str(pose_path),
        '--output-dir', str(results_dir),
        '--no-tts',
        '--no-viz'
    ]
    res = subprocess.run(pipeline_cmd, capture_output=True, text=True, check=True)
    print("Pipeline successful:", res.stdout)
except subprocess.CalledProcessError as e:
    with open("out3.txt", "w") as f:
        f.write("PIPELINE FAILED\n")
        f.write("STDERR: " + e.stderr + "\n")
        f.write("STDOUT: " + e.stdout + "\n")
    print("Failed. Wrote to out3.txt")
except Exception as e:
    import traceback
    with open("out3.txt", "w") as f:
        f.write("GENERAL ERROR\n")
        f.write(traceback.format_exc())


