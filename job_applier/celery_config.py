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