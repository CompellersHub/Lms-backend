from celery import shared_task
from django.conf import settings

from courses.mongo_utils import get_mongo_db
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


@shared_task(bind=True)
def send_course_registration_email(self, to_email, first_name, course_name, course_date, zoom_link, template_id):
    """
    Celery task to send course registration confirmation email
    """
    try:
        logger.info(f"Sending course registration email to {to_email} for {course_name}")
        
        # Prepare template parameters
        params = {
            'FIRST_NAME': first_name,
            
        }
        
        # Call email service with the specific template ID
        success = send_brevo_email(
            to_email=to_email,
            template_id=template_id,  # Use the template_id passed from the view
            params=params
        )
        
        if not success:
            raise Exception("Brevo API returned no response")
            
        return {
            'status': 'success',
            'email': to_email,
            'message': "Course registration email sent successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to send to {to_email}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)
    


@shared_task(bind=True)
def send_receipt_upload_confirmation(self, user_id, receipt_data):
    """
    Enhanced Celery task that accepts user_id and fetches user data
    """
    try:
        logger.info(f"Sending receipt upload confirmation for user {user_id}")
        
        # Get MongoDB connection
        
        db = get_mongo_db()
        
        # Find user in MongoDB
        user = db.customusers.find_one({'_id': user_id})
        
        if not user:
            logger.error(f"User not found with ID: {user_id}")
            return {'status': 'error', 'message': 'User not found'}
        
        user_email = user.get('email')
        if not user_email:
            logger.error(f"User {user_id} has no email address")
            return {'status': 'error', 'message': 'User has no email'}
        
        # Prepare template parameters
        params = {
            'FIRST_NAME': user.get('first_name', 'there'),
            'RECEIPT_DETAILS': receipt_data
        }
        
        # Call email service
        success = send_brevo_email(
            to_email=user_email,
            template_id=8,  # Your receipt template ID
            params=params
        )
        
        if not success:
            raise Exception("Brevo API returned no response")
            
        return {
            'status': 'success',
            'email': user_email,
            'message': "Receipt upload confirmation email sent successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to send receipt email for user {user_id}: {str(e)}")
        raise self.retry(exc=e, countdown=60, max_retries=3)