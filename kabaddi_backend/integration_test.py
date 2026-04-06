import requests
import sys

base_url = "http://localhost:8000/api"

# Get a valid tutorial id for "Bonus" or anything active
print("Fetching tutorials...")
r = requests.get(f"{base_url}/tutorials/")
tutorials = r.json().get('tutorials', [])
if not tutorials:
    print("No active tutorials found.")
    sys.exit(1)
tut_id = tutorials[0]['id']
tut_name = tutorials[0]['name']
print(f"Using tutorial: {tut_name} ({tut_id})")

# Start session
print("Starting session...")
r = requests.post(f"{base_url}/session/start/", json={'tutorial_id': tut_id})
if r.status_code != 200:
    print(f"Failed to start session: {r.text}")
    sys.exit(1)
sess_id = r.json()['session_id']
print(f"Session started: {sess_id}")

# Upload video
print("Uploading video...")
video_path = r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\samples\3D\Techniques\Bonus\USE\bonus_left.mp4"
with open(video_path, 'rb') as f:
    files = {'video': f}
    r = requests.post(f"{base_url}/session/{sess_id}/upload-video/", files=files)

if r.status_code != 200:
    print(f"Upload failed: {r.text}")
    sys.exit(1)
print("Upload successful.")

# Assess
print("Triggering assessment...")
r = requests.post(f"{base_url}/session/{sess_id}/assess/")
print(f"Assessment status: {r.status_code}")
try:
    print("Response JSON:", r.json())
except:
    print("Response Text:", r.text)

