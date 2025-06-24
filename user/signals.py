from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from pymongo import MongoClient
from .models import *
import os
from django.conf import settings
from bson import ObjectId
from courses.mongo_utils import get_mongo_db
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django_rest_passwordreset.signals import reset_password_token_created 
from django.contrib.auth.signals import user_logged_in
from anymail.message import AnymailMessage 
import logging
import threading
from django.urls import reverse
from django.contrib.auth import get_user_model
from pymongo.errors import PyMongoError
from django.contrib.sites.shortcuts import get_current_site
# from .tasks import send_welcome_email_task


def model_to_dict(instance):
    return instance.to_dict()

# Signal to handle saving and updating models
@receiver(post_save, sender=CustomUser)
def sync_customuser_to_mongodb(sender, instance, **kwargs):
    db = get_mongo_db()
    collection_name = sender.__name__.lower() + 's'
    data = model_to_dict(instance)
    data['django_id'] = instance.pk
    course_details = []
    if hasattr(instance, 'course'):  # Check if the 'course' related manager exists
        courses_collection = db['courses']
        for course in instance.course.all():
            related_course_doc = courses_collection.find_one({'django_id': course.pk})
            if related_course_doc:
                course_details.append(related_course_doc)
    data['course'] = course_details  # Store a list of MongoDB Course details

    existing_document = db[collection_name].find_one({"django_id": instance.pk})
    if existing_document:
        db[collection_name].update_one({"_id": existing_document['_id']}, {"$set": data})
    else:
        db[collection_name].insert_one(data)

@receiver(post_delete, sender=CustomUser)
def delete_customuser_from_mongodb(sender, instance, **kwargs):
    db = get_mongo_db()
    collection_name = sender.__name__.lower() + 's'
    db[collection_name].delete_one({"django_id": instance.pk})


@receiver(post_save, sender=TeacherProfile)
@receiver(post_save, sender=Submission)
@receiver(post_save, sender=Notification)
def sync_other_models_to_mongodb(sender, instance, **kwargs):
    db = get_mongo_db()
    collection_name = sender.__name__.lower() + 's'
    data = model_to_dict(instance)
    data['django_id'] = instance.pk
    existing_document = db[collection_name].find_one({"django_id": instance.pk})
    if existing_document:
        db[collection_name].update_one({"_id": existing_document['_id']}, {"$set": data})
    else:
        db[collection_name].insert_one(data)

@receiver(post_delete, sender=TeacherProfile)
@receiver(post_delete, sender=Submission)
@receiver(post_delete, sender=Notification)
def delete_other_models_from_mongodb(sender, instance, **kwargs):
    db = get_mongo_db()
    collection_name = sender.__name__.lower() + 's'
    db[collection_name].delete_one({"django_id": instance.pk})



# Brevo SDK imports
import brevo_python as sib_api_v3_sdk
from brevo_python.rest import ApiException

from django_rest_passwordreset.signals import reset_password_token_created

logger = logging.getLogger(__name__)

# --- IMPORTANT ---
# Get this from your Brevo account under Transactional > Templates
BREVO_PASSWORD_RESET_TEMPLATE_ID = 2 # <--- REPLACE WITH YOUR ACTUAL BREVO TEMPLATE ID
# --- ---

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens by fetching user data from MongoDB
    and sending an email using a Brevo template.
    """
    django_user = reset_password_token.user
    user_email = django_user.email  # Fallback: Django user's email
    user_username = django_user.username # Fallback: Django user's username

    logger.info(f"Django User PK: {django_user.pk} (Type: {type(django_user.pk)})")
    logger.info(f"Django User Email (fallback): {django_user.email}")

    # --- Fetch MongoDB User ---
    db = get_mongo_db()
    if db is not None:
        try:
            users_collection = db.customusers # Your custom user collection name

            mongo_query_value = None 

            if isinstance(django_user.pk, ObjectId):
                mongo_query_value = django_user.pk
                logger.info("Querying MongoDB with ObjectId directly from django_user.pk")
            elif isinstance(django_user.pk, str) and len(django_user.pk) == 24: # ObjectId hex strings are 24 chars
                try:
                    mongo_query_value = ObjectId(django_user.pk)
                    logger.info("Querying MongoDB by converting string django_user.pk to ObjectId")
                except Exception:
                    logger.warning(f"django_user.pk '{django_user.pk}' is a string but not a valid ObjectId hex string. Trying as direct string.")
                    mongo_query_value = django_user.pk # Fallback to query as string if not ObjectId
            elif isinstance(django_user.pk, int):
                mongo_query_value = django_user.pk
                logger.info("Querying MongoDB with integer django_user.pk")
            
            mongo_user = None
            if mongo_query_value is not None:
                # Prioritize _id query
                mongo_user = users_collection.find_one({"_id": mongo_query_value})
                if mongo_user:
                    logger.info(f"MongoDB User found by _id: {mongo_user.get('username')} (ID: {mongo_user.get('_id')})")
                else:
                    logger.warning(f"MongoDB user not found by _id '{mongo_query_value}'. Attempting by email as fallback.")
                    # Fallback to email query if _id didn't work
                    mongo_user = users_collection.find_one({"email": django_user.email})
                    if mongo_user:
                        logger.info(f"MongoDB User found by email (fallback): {mongo_user.get('username')} (ID: {mongo_user.get('_id')})")

            else:
                logger.warning("Could not determine appropriate query value for MongoDB based on django_user.pk type. Attempting by email.")
                # If PK type is unknown, try by email
                mongo_user = users_collection.find_one({"email": django_user.email})
                if mongo_user:
                    logger.info(f"MongoDB User found by email (initial attempt): {mongo_user.get('username')} (ID: {mongo_user.get('_id')})")


            if mongo_user:
                # Update email and username from MongoDB if found
                user_email = mongo_user.get('email', django_user.email)
                user_username = mongo_user.get('username', django_user.username)
                logger.info(f"Using MongoDB user data: Email='{user_email}', Username='{user_username}'")
            else:
                logger.warning("MongoDB user not found. Falling back to Django user email and username.")

        except PyMongoError as e: # Catch specific PyMongo errors
            logger.error(f"MongoDB operation error while fetching user for password reset email: {e}", exc_info=True)
            # user_email and user_username retain their django_user fallbacks
        except Exception as e:
            logger.error(f"General error fetching MongoDB user for password reset email: {e}", exc_info=True)
            # user_email and user_username retain their django_user fallbacks

    else:
        logger.warning("MongoDB client not available. Using Django user email and username for password reset.")

    # --- Construct Password Reset URL ---
    current_site = get_current_site(instance.request)
    protocol = 'https' if instance.request.is_secure() else 'http'
    
    # Get frontend base URL from settings (or provide a default)
    # Ensure you have FRONTEND_RESET_PASSWORD_URL and FRONTEND_DOMAIN defined in settings.py
    # Example in settings.py: FRONTEND_RESET_PASSWORD_URL = 'http://localhost:3000/reset-password/'
    # Example in settings.py: FRONTEND_DOMAIN = 'localhost:3000'
    frontend_base_url = getattr(settings, 'FRONTEND_RESET_PASSWORD_URL', f'{protocol}://{current_site.domain}/reset-password/')
    
    # THIS IS CRITICAL: Adjust this URL to match your frontend's routing.
    # It should be the URL where your frontend expects the reset token.
    # Example for a React/Vue SPA: `http://localhost:3000/reset-password/?token={token}`
    reset_password_url = f"{frontend_base_url}?token={reset_password_token.key}"
    
    logger.info(f"Generated password reset URL: {reset_password_url}")

    # --- Configure Brevo API ---
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    # --- Prepare parameters for the Brevo template ---
    # These keys (e.g., 'username', 'reset_password_url', 'site_name')
    # MUST match the placeholders you've defined in your Brevo template.
    # In your Brevo template, you'd typically access these as {{ params.username }}, {{ params.reset_password_url }}, etc.
    template_params = {
        'username': user_username, # Use the username derived from MongoDB or Django fallback
        'email': user_email,       # Use the email derived from MongoDB or Django fallback
        'reset_password_url': reset_password_url,
        'site_name': getattr(settings, 'SITE_NAME', current_site.name), # Use SITE_NAME from settings or current site
        'domain': getattr(settings, 'FRONTEND_DOMAIN', current_site.domain), # Use FRONTEND_DOMAIN from settings or current site
        # Add any other variables your Brevo template expects
    }

    # Use DEFAULT_FROM_EMAIL from settings.py for the sender
    sender_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
    sender_name = getattr(settings, 'SITE_NAME', current_site.name)

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": user_email}], # Send to the email derived from MongoDB or Django fallback
        template_id=BREVO_PASSWORD_RESET_TEMPLATE_ID,
        params=template_params,
        sender={"email": sender_email, "name": sender_name}
    )

    # --- Send the email via Brevo API ---
    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Brevo transactional email sent successfully to {user_email} via template ID {BREVO_PASSWORD_RESET_TEMPLATE_ID}: {api_response}")
    except ApiException as e:
        logger.error(f"Brevo API Exception when sending password reset email to {user_email}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending Brevo password reset email to {user_email}: {e}", exc_info=True)
