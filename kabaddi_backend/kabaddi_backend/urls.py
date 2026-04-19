from django.urls import path, include

urlpatterns = [
    path('api/', include('api.urls')),
    path('llm_feedback/', include('llm_feedback.urls')),
]