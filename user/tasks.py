# your_app_name/tasks.py

from celery import shared_task
from django.conf import settings
from anymail.message import AnymailMessage
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task
def send_welcome_email_task(user_id):
    """
    Celery task to send a welcome email asynchronously.
    """
    try:
        user = User.objects.get(id=user_id)
        if not user.email:
            print(f"User {user.username} (ID: {user_id}) has no email, skipping welcome email.")
            return

        email_subject = "Welcome to Our Platform!"
        email_html_content = f"""
        <h1>Hello {user.username},</h1>
        <p>Welcome to our platform! We're thrilled to have you here.</p>
        <p>If you have any questions, feel free to contact our support team.</p>
        <p>Best regards,<br>Your Team</p>
        """

        # Using a Brevo template is highly recommended for transactional emails
        # brevo_template_id = 12345 # Replace with your actual Brevo template ID if you have one
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
        print(f"Welcome email successfully sent to {user.email} asynchronously.")

    except User.DoesNotExist:
        print(f"User with ID {user_id} not found for welcome email task.")
    except Exception as e:
        print(f"Failed to send welcome email asynchronously to user ID {user_id}: {e}")