"""
Url paths for persona_generation and impact assesmment
"""
from django.urls import path
from . import views

urlpatterns = [
    path('persona_generation/', views.persona_generation, name='persona_generation'),
    path('impact-assessment/', views.impact_assessment, name='impact_assessment'),
    path('aggregate-impact/', views.aggregate_emotion, name='aggregate_emotion'),
    path('results/<int:news_item_id>/', views.results, name='results'),
    path('results-summary/', views.results_summary, name='results_summary'),

]
