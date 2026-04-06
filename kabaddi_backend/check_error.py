import sys
import os
import django

sys.path.append(r"C:\Users\msibr\Documents\MCA\SEM_4\Project\kabaddi_trainer\kabaddi_backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kabaddi_backend.settings")
django.setup()

from api.models import UserSession

session = UserSession.objects.order_by('-created_at').first()
if session:
    print(f"Session: {session.id}")
    print(f"Status: {session.status}")
    print(f"Error Message: {session.error_message}")
else:
    print("No sessions found.")
