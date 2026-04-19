from django.urls import path
from .views import (
    HealthCheckView,
    TutorialListView,
    TutorialListAllView,
    ARPoseDataView,
    AnimationFileView,
    SessionStartView, 
    VideoUploadView,
    AssessmentTriggerView,
    SessionStatusView,
    ResultsView,
    TTSAudioView
)

urlpatterns = [
    # Health Check
    path('health/', HealthCheckView.as_view(), name='health_check'),

    # Tutorial Catalogue
    path('tutorials/', TutorialListAllView.as_view(), name='tutorial_list_all'),
    path('tutorials/<uuid:tutorial_id>/ar-poses/', ARPoseDataView.as_view(), name='ar_pose_data'),
    path('tutorials/<uuid:tutorial_id>/animation/', AnimationFileView.as_view(), name='animation_file'),
    
    # Session Management
    path('session/start/', SessionStartView.as_view(), name='session_start'),
    path('session/<uuid:session_id>/upload-video/', VideoUploadView.as_view(), name='video_upload'),
    path('session/<uuid:session_id>/assess/', AssessmentTriggerView.as_view(), name='assessment_trigger'),
    path('session/<uuid:session_id>/status/', SessionStatusView.as_view(), name='session_status'),
    path('session/<uuid:session_id>/results/', ResultsView.as_view(), name='results'),
    path('session/<uuid:session_id>/tts-audio/', TTSAudioView.as_view(), name='tts_audio'),
]