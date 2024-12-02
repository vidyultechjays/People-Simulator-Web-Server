"""
This module registers the models with the Django admin site.
"""

from django.contrib import admin
from simulator.models import Persona,EmotionalResponse,NewsItem,AggregateEmotion

admin.site.register(Persona)
admin.site.register(EmotionalResponse)
admin.site.register(NewsItem)
admin.site.register(AggregateEmotion)
