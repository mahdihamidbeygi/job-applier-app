from django.core.management.base import BaseCommand
from core.models import JobListing
from django.conf import settings
import os


class Command(BaseCommand):
    help = "Removes all job records and their associated files"

    def handle(self, *args, **options):
        # Get count before deletion
        count = JobListing.objects.count()

        # Delete associated files first
        for job in JobListing.objects.all():
            if job.tailored_resume:
                try:
                    os.remove(job.tailored_resume.path)
                except:
                    pass
            if job.tailored_cover_letter:
                try:
                    os.remove(job.tailored_cover_letter.path)
                except:
                    pass

        # Delete all job records
        JobListing.objects.all().delete()

        self.stdout.write(self.style.SUCCESS(f"Successfully removed {count} job records"))
