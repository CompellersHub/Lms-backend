# your_app_name/tasks.py

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
import logging
from datetime import datetime # Import datetime for timestamping

# Import Brevo SDK
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

User = get_user_model()
logger = logging.getLogger(__name__)

# --- Brevo API Configuration (from Django settings) ---
BREVO_API_KEY = settings.BREVO_API_KEY
BREVO_WELCOME_LIST_ID = settings.BREVO_WELCOME_LIST_ID # This is the ID of your target contact list

# Initialize Brevo Contacts API client (will be created per task execution)
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = BREVO_API_KEY

@shared_task(bind=True, max_retries=5, default_retry_delay=300) # Increased retries and delay for external API calls
def add_user_to_brevo_list_task(self, user_id: int):
    """
    Celery task to add/update a user in Brevo contact list.
    This task does NOT send a welcome email directly.
    It expects Brevo automation to handle any email sending based on list addition.
    """
    user = None # Initialize user for finally block or error handling outside main try
    try:
        user = User.objects.get(id=user_id)
        if not user.email:
            logger.warning(f"User {user.username} (ID: {user_id}) has no email, skipping adding to Brevo list.")
            # Optional: Update user's sync status to 'no_email' if you track this
            if hasattr(user, 'brevo_sync_status'):
                user.brevo_sync_status = "brevo_skipped_no_email"
                user.save(update_fields=['brevo_sync_status'])
            return

        user_email = user.email
        user_first_name = getattr(user, 'first_name', None)
        user_last_name = getattr(user, 'last_name', None)
        user_username = user.username # Keep for logging clarity

        api_instance_contacts = sib_api_v3_sdk.ContactsApi(sib_api_v3_sdk.ApiClient(configuration))

        try:
            attributes = {}
            if user_first_name:
                attributes["FNAME"] = user_first_name
            if user_last_name:
                attributes["LNAME"] = user_last_name
            # Add any other custom attributes you wish to sync from your User model
            # For example, if you have a 'phone_number' field:
            # if user.phone_number:
            #    attributes["SMS"] = user.phone_number # Make sure it's in a Brevo-compatible format

            create_contact_body = sib_api_v3_sdk.CreateContact(
                email=user_email,
                attributes=attributes,
                list_ids=[BREVO_WELCOME_LIST_ID], # The list where you want to add the contact
                update_enabled=True # Crucial: updates contact if email exists, adds to specified list
            )
            api_instance_contacts.create_contact(create_contact_body)
            logger.info(f"User '{user_email}' (ID: {user_id}) successfully added/updated in Brevo list {BREVO_WELCOME_LIST_ID}.")

            # Update user's sync status in your DB (assuming you have these fields on User model)
            if hasattr(user, 'brevo_sync_status'):
                user.brevo_sync_status = "brevo_synced"
                user.brevo_sync_date = datetime.now()
                user.save(update_fields=['brevo_sync_status', 'brevo_sync_date'])

            return True

        except ApiException as e_api:
            logger.error(f"Brevo API Error adding user '{user_email}' (ID: {user_id}) to list: {e_api}", exc_info=True)
            # Decide if this type of API error should cause a retry
            if e_api.status in [429, 500, 502, 503, 504]: # Retry on common transient errors
                # Re-raise to trigger Celery's retry mechanism
                raise self.retry(exc=e_api, countdown=self.default_retry_delay)
            else:
                # For non-retryable errors (e.g., 400 Bad Request, invalid API key etc.), mark as failed
                if hasattr(user, 'brevo_sync_status'):
                    user.brevo_sync_status = f"brevo_failed_{e_api.status}"
                    user.brevo_sync_error = str(e_api)
                    user.save(update_fields=['brevo_sync_status', 'brevo_sync_error'])
                return False

    except User.DoesNotExist:
        logger.error(f"Celery task: User with ID {user_id} not found for Brevo list sync.", exc_info=True)
        return False
    except Exception as e:
        logger.critical(f"Unhandled critical error in Brevo list sync task for user ID {user_id}: {e}", exc_info=True)
        # For any unexpected errors, still retry based on task configuration
        # You might want to categorize these as "unknown_error" in your status field
        if hasattr(user, 'brevo_sync_status'):
            user.brevo_sync_status = "brevo_failed_unknown"
            user.brevo_sync_error = str(e)
            user.save(update_fields=['brevo_sync_status', 'brevo_sync_error'])
        raise self.retry(exc=e, countdown=self.default_retry_delay)

# --- Celery Signals (Optional, but good for monitoring) ---
from celery.signals import task_success, task_failure

@task_success.connect(sender=add_user_to_brevo_list_task)
def brevo_list_add_success_handler(sender, result, **kwargs):
    task_id = kwargs.get('task_id')
    user_id = kwargs.get('args')[0] if kwargs.get('args') else 'N/A'
    logger.info(f"Celery Signal: Brevo list add task '{task_id}' for User ID {user_id} succeeded. Result: {result}")

@task_failure.connect(sender=add_user_to_brevo_list_task)
def brevo_list_add_failure_handler(sender, task_id, exception, args, kwargs, traceback, einfo, **_kwargs):
    user_id = args[0] if args else 'N/A'
    logger.error(f"Celery Signal: Brevo list add task '{task_id}' for User ID {user_id} failed with exception: {exception}")
    # This signal could trigger external alerts or more advanced error reporting