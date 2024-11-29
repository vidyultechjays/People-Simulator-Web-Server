"""
This module defines the configuration for the Simulator application.
"""
from django.apps import AppConfig


class SimulatorConfig(AppConfig):
    """
    Configuration class for the Simulator application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'simulator'
