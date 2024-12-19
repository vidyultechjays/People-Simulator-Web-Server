"""
Configures the Simulator application to run background tasks for emotion aggregation and persona generation when the app is ready. 
Ensures the database connection is valid before starting these tasks. 
Both tasks are executed in separate threads to avoid blocking the application.
"""
import os
import IPython
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
# import os
# import threading
# import logging
# from django.apps import AppConfig
# from django.db import connection
# from django.core.management import call_command

# # Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class SimulatorConfig(AppConfig):
#     """
#     Configuration class for the Simulator application.
#     """
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'simulator'

#     def ready(self):
#         """
#         Initializes background tasks when the application is ready.
#         Includes improved error handling and dependency checking.
#         """
#         # Prevent double execution in development
#         if os.environ.get('RUN_MAIN') != 'true':
#             return

#         # Verify database connection
#         if not connection.settings_dict['NAME']:
#             logger.error("Database connection not configured properly")
#             return

#         # Check required dependencies
#         try:
#             # Check for IPython
#             import IPython
#             # Check for ask_gemini utility
#             from simulator.utils.ask_gemini import ask_gemini
#         except ImportError as e:
#             logger.error(f"Missing required dependency: {e}")
#             logger.error("Please ensure all requirements are installed")
#             return

#         def start_aggregation():
#             """
#             Starts the emotion aggregation background task with improved error handling.
#             """
#             try:
#                 logger.info("Starting emotion aggregation task...")
#                 call_command('aggregate_emotions')
#             except Exception as e:
#                 logger.error(f"Failed to start emotion aggregation: {str(e)}")
#                 logger.exception("Full traceback:")

#         def start_persona_generation():
#             """
#             Starts the persona generation background task with improved error handling.
#             """
#             try:
#                 logger.info("Starting persona generation task...")
#                 call_command('generate_personas')
#             except Exception as e:
#                 logger.error(f"Failed to start persona generation: {str(e)}")
#                 logger.exception("Full traceback:")

#         # Launch threads with proper error handling
#         try:
#             aggregation_thread = threading.Thread(target=start_aggregation, daemon=True)
#             persona_thread = threading.Thread(target=start_persona_generation, daemon=True)

#             aggregation_thread.start()
#             persona_thread.start()

#             logger.info("Successfully started background tasks")
#         except Exception as e:
#             logger.error(f"Failed to start background threads: {str(e)}")