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