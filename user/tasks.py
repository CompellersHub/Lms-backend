from celery import shared_task
from django.conf import settings
from .utils.email_service import send_brevo_email
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def send_welcome_otp(self, to_email, otp_code, first_name=None):
    """
    Celery task to send welcome email with OTP
    Note the changed parameter name from 'email' to 'to_email'
    """
    try:
        logger.info(f"Attempting to send OTP email to {to_email}")
        
        # Call email service with EXACTLY matching parameters
        success = send_brevo_email(
            to_email=to_email,      # Must match parameter name in send_brevo_email
            otp_code=otp_code,      # Must match
            first_name=first_name   # Must match
        )
        
        if not success:
            raise Exception("Brevo API returned no response")
            
        return {
            'status': 'success',
            'email': to_email,
            'message': "OTP email sent successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to send to {to_email}: {str(e)}")
        raise self.retry(exc=e, countdown=60)
    
@shared_task
def send_teacher_approval_email(to_email, first_name):
    login_url = 'https://facilitatorshub.titanscareers.com/login'
    send_brevo_email(
        to_email=to_email,
        template_id=5,  # Approval template ID
        params={
            'FIRST_NAME': first_name,
            'LOGIN_LINK': login_url
        }
    )

@shared_task
def send_teacher_rejection_email(to_email, first_name, feedback):
    send_brevo_email(
        to_email=to_email,
        template_id=6,  # Rejection template ID
        params={
            'FIRST_NAME': first_name,
            'FEEDBACK': feedback
        }
    )

@shared_task(bind=True)
def send_application_received_email(self, to_email, first_name):
    try:
        logger.info(f"Sending application received email to {to_email}")
        result = send_brevo_email(
            to_email=to_email,
            template_id=7,  # Your template ID for application received
            params={
                'FIRST_NAME': first_name
            }
        )
        logger.info(f"Email sent to {to_email}: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to send application email: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=3)