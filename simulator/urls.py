from django.urls import path
from . import views

urlpatterns = [
    path('persona_generation/', views.persona_generation, name='persona_generation'),
    path('impact-assessment/', views.impact_assessment, name='impact_assessment'),
]
