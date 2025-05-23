from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.utils.data_cleanup import clear_all_user_data

User = get_user_model()


class Command(BaseCommand):
    help = "Clears all JobListing and ChatConversation data for a specific user."

    def add_arguments(self, parser):
        parser.add_argument(
            "user_identifier", type=str, help="Username or email of the user to clear."
        )

    def handle(self, *args, **options):
        user_identifier = options["user_identifier"]
        try:
            if "@" in user_identifier:
                user = User.objects.get(email=user_identifier)
            else:
                user = User.objects.get(username=user_identifier)
        except User.DoesNotExist:
            raise CommandError(f'User "{user_identifier}" does not exist.')

        self.stdout.write(f"Preparing to clear data for user: {user.username} (ID: {user.id})")
        confirm = input(
            "Are you sure you want to proceed? This action cannot be undone. (yes/no): "
        )

        if confirm.lower() != "yes":
            self.stdout.write("Operation cancelled.")
            return

        success, message = clear_all_user_data(user.id)

        if success:
            self.stdout.write(self.style.SUCCESS(message))
        else:
            self.stderr.write(self.style.ERROR(message))
