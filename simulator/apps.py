"""
This module defines the configuration for the Simulator application.
"""
import os
import threading
from django.apps import AppConfig
from django.core.management import call_command
from django.db import connection

class SimulatorConfig(AppConfig):
    """
    Configuration class for the Simulator application.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'simulator'

    def ready(self):
        if os.environ.get('RUN_MAIN') != 'true':
            return
        
        if connection.settings_dict['NAME']:
            def start_aggregation():
                try:
                    call_command('aggregate_emotions')
                except Exception as e:
                    print(f"Failed to start emotion aggregation: {e}")

            thread = threading.Thread(target=start_aggregation, daemon=True)
            thread.start()