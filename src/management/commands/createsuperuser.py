from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser with additional fields'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str)
        parser.add_argument('--email', type=str)
        parser.add_argument('--password', type=str)
        parser.add_argument('--phone', type=str, default='')
        parser.add_argument('--location', type=str, default='')
        parser.add_argument('--bio', type=str, default='')

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        password = options.get('password')
        phone = options.get('phone')
        location = options.get('location')
        bio = options.get('bio')

        if not username or not email or not password:
            self.stdout.write(self.style.ERROR('Username, email, and password are required.'))
            return

        try:
            with transaction.atomic():
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    phone=phone,
                    location=location,
                    bio=bio
                )
                self.stdout.write(self.style.SUCCESS(f'Superuser {username} created successfully.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}'))
