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



@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    """
    Handles password reset tokens
    When a token is created, an e-mail needs to be sent to the user
    """
    # Get the Django User instance from the token
    django_user = reset_password_token.user

    # Fetch the corresponding MongoDB user to get the actual email
    # Assuming django_user.pk stores the _id from MongoDB
    client = None
    try:
        client = MongoClient(settings.MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
        db = client.get_database() # Get the database instance
        users_collection = db.customusers # Your custom user collection name
        mongo_user = users_collection.find_one({"_id": django_user.pk})

        if mongo_user:
            user_email = mongo_user.get('email', django_user.email) # Prefer MongoDB email, fallback to Django user email
            user_username = mongo_user.get('username', django_user.username) # Prefer MongoDB username, fallback to Django user username
        else:
            # Fallback if MongoDB user not found (e.g., if it's a standard Django user)
            user_email = django_user.email
            user_username = django_user.username
    except Exception as e:
        print(f"Error fetching MongoDB user for password reset email: {e}")
        # Log the error more verbosely if needed
        # logging.error(f"Error fetching MongoDB user for password reset email: {e}", exc_info=True)
        user_email = django_user.email # Critical fallback
        user_username = django_user.username
    finally:
        if client: # Only close if client was successfully assigned
            client.close()

    # Build the reset password URL for the frontend
    # This is where your frontend will handle the token for password reset
    frontend_base_url = getattr(settings, 'FRONTEND_RESET_PASSWORD_URL', 'http://localhost:5173/reset-password/')
    # Ensure the frontend URL has a trailing slash if it expects one, or adjust here
    # The package gives you the token itself (.key)
    reset_password_url = f"{frontend_base_url}?token={reset_password_token.key}"

    context = {
        'username': user_username,
        'email': user_email,
        'reset_password_url': reset_password_url,
        'site_name': getattr(settings, 'SITE_NAME', 'Your LMS'), # Define SITE_NAME in settings.py
        'domain': getattr(settings, 'FRONTEND_DOMAIN', 'localhost:3000'), # Define FRONTEND_DOMAIN in settings.py
    }

    # email_html_message = render_to_string('email/user_reset_password.html', context)
    email_plaintext_message = render_to_string('email/user_reset.txt', context)

    msg = EmailMultiAlternatives(
        subject=f"Password Reset for {context['site_name']}",
        body=email_plaintext_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user_email]
    )
    msg.attach_alternative(email_plaintext_message, "text/html")
    msg.send()


# your_app_name/signals.py


# If you're using Celery, import your task here
# from .tasks import send_welcome_email_task # Example Celery task

@receiver(user_logged_in)
def send_welcome_email_on_login(sender, request, user, **kwargs):
    """
    Signal receiver to send a welcome email when a user logs in.
    """
    if user.email: # Ensure the user has an email address
        print(f"User {user.username} logged in. Attempting to send welcome email to {user.email}")

        # IMPORTANT: Do NOT send emails synchronously in a signal handler in production.
        # This will block the login request and make it slow.
        # Use an asynchronous task queue like Celery.

        # Option 1: Synchronous (NOT RECOMMENDED for production)
        # try:
        #     AnymailMessage(
        #         to=[user.email],
        #         from_email=settings.DEFAULT_FROM_EMAIL,
        #         subject="Welcome Back! (or Just Welcome!)",
        #         html_content=f"<h1>Hello {user.username}!</h1><p>Thanks for logging in.</p>"
        #     ).send()
        #     print(f"Synchronous welcome email sent to {user.email}")
        # except Exception as e:
        #     print(f"Error sending synchronous welcome email to {user.email}: {e}")

        # Option 2: Asynchronous (RECOMMENDED for production using Celery)
        # Make sure you have Celery configured and 'send_welcome_email_task' defined in your_app_name/tasks.py
        # You would typically pass the user ID or email to the task.
        # send_welcome_email_task.delay(user.id) # Pass user ID if task fetches user details
        # Or:
        # send_welcome_email_task.delay(user.email, user.username) # Pass email and username directly
        print(f"Asynchronous welcome email task triggered for {user.email}")

        # Example of the actual email sending logic that would go into a Celery task:
        try:
            # You would put this logic inside your Celery task function
            email_subject = "Welcome to Our Platform!"
            email_html_content = f"""
            <h1>Hello {user.username},</h1>
            <p>Welcome to our platform! We're thrilled to have you here.</p>
            <p>If you have any questions, feel free to contact our support team.</p>
            <p>Best regards,<br>Your Team</p>
            """
            # Using a Brevo template is highly recommended for transactional emails
            # brevo_template_id = 12345 # Replace with your actual Brevo template ID
            # if brevo_template_id:
            #     message = AnymailMessage(
            #         to=[user.email],
            #         from_email=settings.DEFAULT_FROM_EMAIL,
            #         template_id=brevo_template_id,
            #         merge_global_data={
            #             "user_name": user.get_full_name() or user.username,
            #             "platform_name": "My DRF App",
            #         }
            #     )
            # else:
            message = AnymailMessage(
                to=[user.email],
                from_email=settings.DEFAULT_FROM_EMAIL,
                subject=email_subject,
                html_content=email_html_content,
            )
            message.send()
            print(f"Welcome email successfully sent to {user.email}")
        except Exception as e:
            print(f"Failed to send welcome email to {user.email}: {e}")


# your_app_name/signals.py (updated)
# ...
from .tasks import send_welcome_email_task # Import your Celery task

@receiver(user_logged_in)
def trigger_welcome_email_on_login(sender, request, user, **kwargs):
    if user.email:
        # Trigger the Celery task
        send_welcome_email_task.delay(user.id) # Pass user.id, task will fetch user object
        print(f"Welcome email task for {user.email} queued.")