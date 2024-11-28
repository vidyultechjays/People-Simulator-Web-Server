"""
This module registers the models with the Django admin site.
"""

from django.contrib import admin
from . models import Persona

admin.site.register(Persona)
