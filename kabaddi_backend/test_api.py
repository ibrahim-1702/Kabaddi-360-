import sys
import urllib.request
sys.path.append(r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\kabaddi_backend")

url = 'http://localhost:8000/api/session/1ee12261-a6e6-4692-a888-84ff4a5ee47f/assess/'
try:
    req = urllib.request.Request(url, method='POST', headers={'Content-Type': 'application/json'}, data=b'{}')
    resp = urllib.request.urlopen(req)
    print("SUCCESS")
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}")
    print(e.read().decode())
except Exception as e:
    print(f"Error: {e}")
