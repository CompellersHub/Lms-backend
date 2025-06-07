# your_app_name/tasks.py

from celery import shared_task
from django.conf import settings
from anymail.message import AnymailMessage # <--- Use AnymailMessage
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email_task(self, user_id):
    """
    Celery task to send a welcome email asynchronously using Anymail (Brevo).
    """
    try:
        user = User.objects.get(id=user_id)
        if not user.email:
            logger.warning(f"User {user.username} (ID: {user_id}) has no email, skipping welcome email.")
            return

        user_email = user.email
        user_name = user.get_full_name() or user.username

        # Get the Brevo template ID from settings
        # You can hardcode this here, or fetch from settings
        brevo_signup_template_id = 1 # Ensure this is in your settings

        # Data for your Brevo template's placeholders (e.g., {{ params.name }})
        # Anymail uses 'merge_global_data' for global template params
        # or 'merge_data' for recipient-specific merge vars.
        # For Brevo, usually global data covers most template needs.
        merge_data = {
            "name": user_name, # Corresponds to {{ params.name }} in Brevo template
            "platform_name": "Titans Careers", # Corresponds to {{ params.platform_name }}
            # Add any other dynamic data your Brevo template expects
        }

        # Create and send the AnymailMessage
        message = AnymailMessage(
            to=[user_email],
            # If from_email is not set, it defaults to DEFAULT_FROM_EMAIL in settings
            # from_email=settings.DEFAULT_FROM_EMAIL,
            template_id= 1,
            merge_global_data=merge_data, # Pass data to the template
            # You can still set a subject here, it will override the template's subject if needed
            # subject=f"Welcome to Our Platform, {user_name}!"
        )

        message.send()
        logger.info(f"Welcome email successfully sent to {user_email} via Anymail (Brevo) asynchronously.")

    except User.DoesNotExist:
        logger.error(f"Celery task: User with ID {user_id} not found for welcome email.")
    except Exception as e:
        logger.error(f"Unhandled error in send_welcome_email_task for user ID {user_id}: {e}", exc_info=True)
        # Re-raise to allow Celery to handle retries or mark as failed
        raise self.retry(exc=e, countdown=self.default_retry_delay)