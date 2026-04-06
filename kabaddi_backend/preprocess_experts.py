import sys
import subprocess
import os

python_exe = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\venv\Scripts\python.exe"
extract_script = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\level1_pose\pose_extract_cli.py"

bonus_vid = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\samples\3D\Techniques\Bonus\USE\bonus_left.mp4"
bonus_out = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\kabaddi_backend\media\expert_poses\bonus.npy"

hand_vid = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\samples\3D\Techniques\HandTouch\USE\hand_left.mp4"
hand_out = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\kabaddi_backend\media\expert_poses\hand_touch.npy"

# Ensure output directory exists
os.makedirs(os.path.dirname(bonus_out), exist_ok=True)

try:
    print(f"Running extract on {bonus_vid}...")
    subprocess.run([python_exe, extract_script, bonus_vid, bonus_out], check=True)
    print("Bonus extracted successfully.")
except Exception as e:
    print(f"Failed to extract Bonus: {e}")

try:
    print(f"Running extract on {hand_vid}...")
    subprocess.run([python_exe, extract_script, hand_vid, hand_out], check=True)
    print("HandTouch extracted successfully.")
except Exception as e:
    print(f"Failed to extract HandTouch: {e}")

print("Pre-processing complete.")
