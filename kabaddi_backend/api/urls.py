from django.urls import path
from .views import (
    TutorialListView,
    ARPoseDataView,
    SessionStartView, 
    VideoUploadView,
    AssessmentTriggerView,
    SessionStatusView,
    ResultsView
)

urlpatterns = [
    # AR Playback Data
    path('tutorials/<uuid:tutorial_id>/ar-poses/', ARPoseDataView.as_view(), name='ar_pose_data'),
    
    # Session Management
    path('session/start/', SessionStartView.as_view(), name='session_start'),
    path('session/<uuid:session_id>/upload-video/', VideoUploadView.as_view(), name='video_upload'),
    path('session/<uuid:session_id>/assess/', AssessmentTriggerView.as_view(), name='assessment_trigger'),
    path('session/<uuid:session_id>/status/', SessionStatusView.as_view(), name='session_status'),
    path('session/<uuid:session_id>/results/', ResultsView.as_view(), name='results'),
]