"""
Url paths for persona_generation and impact assesmment,aggregate-impact and results
"""
from django.urls import path
from simulator import views

urlpatterns = [
    path("", views.landing_page, name="landing_page"),
    path("impact-assessment-new/", views.impact_assessment_new, name="impact_assessment_new"),
    
    
    
    path("persona_input/", views.persona_input, name="persona_input"),
    path("demographics_input/", views.demographics_input, name="demographics_input"),
    path('impact-assessment/', views.impact_assessment, name='impact_assessment'),
    path('aggregate-impact/', views.aggregate_emotion, name='aggregate_emotion'),
    path('results-summary/', views.results_summary, name='results_summary'),
    path('fetch_summary_api/', views.fetch_summary_api, name='fetch_summary_api'),
    path(
        'sample-profiles/<str:category_type>/<str:category_name>/<str:city_name>/<str:news_item_title>/',
        views.fetch_sample_profiles,
        name='sample_profiles'
    ),
    path('list-aggregate-emotions/', views.list_aggregate_emotions, name='list_aggregate_emotions'),
    path('optimize-content/', views.optimize_content, name='optimize_content'),
    path('optimize-content-two/', views.optimize_content_two, name='optimize_content_two'),
]
