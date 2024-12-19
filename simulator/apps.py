"""
Configures the Simulator application to run background tasks for emotion aggregation and persona generation when the app is ready. 
Ensures the database connection is valid before starting these tasks. 
Both tasks are executed in separate threads to avoid blocking the application.
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
        """
        Prevents the command from running twice during development with `runserver`
        """
        if os.environ.get('RUN_MAIN') != 'true':
            return

        # Ensure the database connection is valid before running commands
        if connection.settings_dict['NAME']:
            # Start the emotion aggregation background job
            def start_aggregation():
                """
                aggregate emotions background task starting
                """
                try:
                    call_command('aggregate_emotions')
                except Exception as e:
                    print(f"Failed to start emotion aggregation: {e}")

            # Start the persona generation background job
            def start_persona_generation():
                """
                generate personas background task starting
                """
                try:
                    call_command('generate_personas')
                except Exception as e:
                    print(f"Failed to start persona generation: {e}")

            # Launch threads for both tasks
            aggregation_thread = threading.Thread(target=start_aggregation, daemon=True)
            persona_thread = threading.Thread(target=start_persona_generation, daemon=True)

            aggregation_thread.start()
            persona_thread.start()
