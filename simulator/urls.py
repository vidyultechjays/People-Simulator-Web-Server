from django.urls import path
from . import views

urlpatterns = [
    path('persona-generation/', views.persona_generation, name='generate_personas'),
    path('impact-assessment/', views.impact_assessment, name='impact_assessment'),
]
