# celery_config.py
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "job_applier.settings")

app = Celery("job_applier")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Fix for the unpacking error - ensure proper worker initialization
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Acknowledge tasks after completion
    worker_disable_rate_limits=True,
    task_reject_on_worker_lost=True,
)


# Optional: Add debug task
@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


# Optional: Add task discovery logging
@app.on_after_configure.connect
def setup_task_discovery(sender, **kwargs):
    print("Discovering tasks...")
    for task in sender.tasks:
        print(f"Discovered task: {task}")
