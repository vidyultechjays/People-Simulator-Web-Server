from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'people_simulator.settings')

# Initialize Celery app
app = Celery('people_simulator')

# Configure Celery to use the Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks from installed apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
