from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models.user import User

@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    """
    Send a welcome email to new users.
    """
    if created:
        subject = f'Welcome to {settings.SITE_NAME}!'
        message = f'''
        Hello {instance.username},

        Welcome to {settings.SITE_NAME}! We're excited to have you on board.

        With {settings.SITE_NAME}, you can:
        - Track your job applications
        - Manage your resume and cover letters
        - Keep notes on your applications
        - Monitor your application status

        Get started by:
        1. Completing your profile
        2. Adding your resume
        3. Finding and applying for jobs

        If you have any questions, feel free to contact us at {settings.SITE_EMAIL}.

        Best regards,
        The {settings.SITE_NAME} Team
        '''
        send_mail(
            subject,
            message,
            settings.SITE_EMAIL,
            [instance.email],
            fail_silently=False,
        )

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a profile for new users.
    """
    if created:
        from .models.profile import Profile
        Profile.objects.create(user=instance)
