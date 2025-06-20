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
from django.contrib.auth import get_user_model
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



User = get_user_model()
logger = logging.getLogger(__name__)

@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    """
    django_user = reset_password_token.user
    user_email = django_user.email  # Fallback: Django user's email
    user_username = django_user.username # Fallback: Django user's username

    # --- DEBUGGING BEGINS ---
    logger.info(f"Django User PK: {django_user.pk} (Type: {type(django_user.pk)})")
    # You might want to log the email that django_user currently has as a fallback
    logger.info(f"Django User Email (fallback): {django_user.email}")
    # --- DEBUGGING ENDS ---

    # --- Fetch MongoDB User ---
    db = get_mongo_db()
    if db is not None:
        try:
            users_collection = db.customusers # Your custom user collection name

            # --- Critical part: How do you map django_user.pk to MongoDB's _id? ---

            mongo_query_value = None # Initialize to None

            # Case 1: If django_user.pk is already a bson.ObjectId
            # (This happens if your custom Django User model uses an ObjectId field directly)
            if isinstance(django_user.pk, ObjectId):
                mongo_query_value = django_user.pk
                logger.info("Querying MongoDB with ObjectId directly from django_user.pk")

            # Case 2: If django_user.pk is a string that represents an ObjectId
            # (Common if you store MongoDB _id as a string in Django's PK)
            elif isinstance(django_user.pk, str) and len(django_user.pk) == 24: # ObjectId hex strings are 24 chars
                try:
                    mongo_query_value = ObjectId(django_user.pk)
                    logger.info("Querying MongoDB by converting string django_user.pk to ObjectId")
                except Exception: # Handle cases where string is not a valid ObjectId
                    logger.warning(f"django_user.pk '{django_user.pk}' is a string but not a valid ObjectId hex string.")

            # Case 3: If django_user.pk is an integer and your MongoDB _id is also an integer
            # (This means you explicitly set _id to an integer when creating users in Mongo)
            elif isinstance(django_user.pk, int):
                mongo_query_value = django_user.pk
                logger.info("Querying MongoDB with integer django_user.pk")
            
            # Case 4: If django_user.pk is an integer, but your MongoDB _id is a string of that integer
            # (Less common, but possible if _id was stringified int)
            # elif isinstance(django_user.pk, int):
            #     mongo_query_value = str(django_user.pk)
            #     logger.info("Querying MongoDB by converting integer django_user.pk to string")

            # Case 5: If you use a *separate field* in MongoDB to link to Django's PK
            # (e.g., you have a field named 'django_id' in MongoDB that stores django_user.pk)
            # This is often the most robust way if _id is ObjectId and Django PK is int.
            # You would need to ensure this 'django_id' field exists in your MongoDB documents.
            # mongo_query = {"django_id": django_user.pk}
            # mongo_user = users_collection.find_one(mongo_query)
            # logger.info(f"Querying MongoDB with separate field 'django_id'={django_user.pk}")


            mongo_user = None
            if mongo_query_value is not None:
                mongo_user = users_collection.find_one({"_id": mongo_query_value})
            else:
                logger.warning("Could not determine appropriate query value for MongoDB based on django_user.pk type.")
            
            # --- DEBUGGING BEGINS ---
            if mongo_user:
                logger.info(f"MongoDB User found: {mongo_user.get('username')} (ID: {mongo_user.get('_id')})")
            else:
                logger.warning(f"MongoDB user not found using query value '{mongo_query_value}' (Type: {type(mongo_query_value)}).")
                # Add more detailed logging here if needed:
                # logger.warning(f"Attempted query: {{'_id': {mongo_query_value}}}")
                # You could also try to find by email as a last resort for debugging:
                # found_by_email = users_collection.find_one({"email": django_user.email})
                # if found_by_email:
                #     logger.info(f"User found by email in MongoDB: {found_by_email.get('username')}")
                # else:
                #     logger.warning("User not found by email in MongoDB either.")
            # --- DEBUGGING ENDS ---


            if mongo_user:
                user_email = mongo_user.get('email', django_user.email)
                user_username = mongo_user.get('username', django_user.username)
            else:
                logger.warning("Falling back to Django user email as MongoDB user not found.")

        except Exception as e:
            logger.error(f"Error fetching MongoDB user for password reset email: {e}", exc_info=True)
            # user_email and user_username retain their django_user fallbacks

    else:
        logger.warning("MongoDB client not available. Using Django user email for password reset.")

    # --- Rest of your signal handler (unchanged) ---
    frontend_base_url = getattr(settings, 'FRONTEND_RESET_PASSWORD_URL', 'http://localhost:5173/reset-password/')
    reset_password_url = f"{frontend_base_url}?token={reset_password_token.key}"

    context = {
        'username': user_username,
        'email': user_email,
        'reset_password_url': reset_password_url,
        'site_name': getattr(settings, 'SITE_NAME', 'Your LMS'),
        'domain': getattr(settings, 'FRONTEND_DOMAIN', 'localhost:3000'),
    }

    # email_html_message = render_to_string('email/user_reset.html', context)
    email_plaintext_message = render_to_string('email/user_reset.txt', context)

    msg = EmailMultiAlternatives(
        subject=f"Password Reset for {context['site_name']}",
        body=email_plaintext_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email]
    )
    msg.attach_alternative(email_plaintext_message, "text/html")
    try:
        msg.send()
    except Exception as e:
        logger.error(f"Failed to send password reset email to {user_email}: {e}", exc_info=True)



# User = get_user_model()
# logger = logging.getLogger(__name__)

# # --- Asynchronous Email Thread Class (for simple async without Celery) ---
# @receiver(post_save, sender=User)
# def trigger_welcome_email_on_signup(sender, instance, created, **kwargs):
#     """
#     Signal receiver to trigger a welcome email when a new user is created (signs up).
#     """
#     if created: # This condition ensures the email is sent ONLY on user creation
#         user_email = instance.email
#         user_name = instance.get_full_name() or instance.username

#         if user_email:
#             logger.info(f"New user {instance.username} signed up. Queuing welcome email to {user_email}.")

#             # --- Trigger the Celery task ---
#             send_welcome_email_task.delay(instance.id) # Pass the user ID to the task
#         else:
#             logger.warning(f"New user {instance.username} created but has no email address. Skipping welcome email trigger.")