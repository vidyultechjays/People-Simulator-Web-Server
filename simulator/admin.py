"""
This module registers the models with the Django admin site.
"""

from django.contrib import admin
from . models import Persona,EmotionalResponse,NewsItem

admin.site.register(Persona)
admin.site.register(EmotionalResponse)
admin.site.register(NewsItem)

