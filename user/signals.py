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

# Get this from your Brevo account under Transactional > Templates
BREVO_PASSWORD_RESET_TEMPLATE_ID = 2  # Replace with your actual Brevo template ID

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens by fetching user data from MongoDB
    and sending an email using a Brevo template.
    """
    # Get the email from the reset token (this comes from Django's user model)
    django_user_email = reset_password_token.user.email
    
    logger.info(f"Django User Email from token: {django_user_email}")
    
    # Fetch user from MongoDB using email
    db = get_mongo_db()
    if db is None:
        logger.error("MongoDB client not available. Cannot send password reset email.")
        return
    
    try:
        users_collection = db.customusers  # Your custom user collection name
        
        # Query MongoDB user by email
        mongo_user = users_collection.find_one({"email": django_user_email})
        
        if not mongo_user:
            logger.error(f"MongoDB user not found with email: {django_user_email}")
            return
            
        # Get user data from MongoDB
        user_email = mongo_user.get('email')
        user_username = mongo_user.get('username', 'User')  # Default to 'User' if username not found
        
        logger.info(f"Found MongoDB user: {user_username} ({user_email})")

        # Construct Password Reset URL
        current_site = get_current_site(instance.request)
        protocol = 'https' if instance.request.is_secure() else 'http'
        
        # Get frontend base URL from settings
        frontend_base_url = getattr(settings, 'FRONTEND_RESET_PASSWORD_URL', 
                                   f'{protocol}://{current_site.domain}/reset-password/')
        
        reset_password_url = f"{frontend_base_url}?token={reset_password_token.key}"
        logger.info(f"Generated password reset URL: {reset_password_url}")

        # Configure Brevo API
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.BREVO_API_KEY

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        # Prepare parameters for the Brevo template
        template_params = {
            'username': user_username,
            'email': user_email,
            'reset_password_url': reset_password_url,
            'site_name': getattr(settings, 'SITE_NAME', current_site.name),
            'domain': getattr(settings, 'FRONTEND_DOMAIN', current_site.domain),
            'logo_url': getattr(settings, 'BREVO_EMAIL_LOGO_URL', 'staticfiles/logo/logo.jpg'), 
            'contact_url': getattr(settings, 'BREVO_EMAIL_CONTACT_URL', 'https://your-site.com/contact'),
            'privacy_url': getattr(settings, 'BREVO_EMAIL_PRIVACY_URL', 'https://your-site.com/privacy-policy'),
        }

        # Use DEFAULT_FROM_EMAIL from settings.py for the sender
        sender_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com')
        sender_name = getattr(settings, 'SITE_NAME', current_site.name)

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": user_email}],
            template_id=BREVO_PASSWORD_RESET_TEMPLATE_ID,
            params=template_params,
            sender={"email": sender_email, "name": sender_name}
        )

        # Send the email via Brevo API
        try:
            api_response = api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Brevo transactional email sent successfully to {user_email} via template ID {BREVO_PASSWORD_RESET_TEMPLATE_ID}: {api_response}")
        except ApiException as e:
            logger.error(f"Brevo API Exception when sending password reset email to {user_email}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred while sending Brevo password reset email to {user_email}: {e}", exc_info=True)

    except PyMongoError as e:
        logger.error(f"MongoDB operation error while fetching user for password reset email: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"General error in password reset process: {e}", exc_info=True)

