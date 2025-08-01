# utils/email_service.py
from sib_api_v3_sdk import Configuration, ApiClient, TransactionalEmailsApi
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_brevo_email(to_email, otp_code, first_name=None):
    """
    Email sending function - parameters MUST match task call exactly
    """
    config = Configuration()
    config.api_key['api-key'] = settings.BREVO_API_KEY
    
    try:
        api_instance = TransactionalEmailsApi(ApiClient(config))
        
        send_smtp_email = {
            'sender': {
                'email': settings.DEFAULT_FROM_EMAIL,
                'name': settings.DEFAULT_FROM_NAME
            },
            'to': [{'email': to_email}],
            'templateId': settings.OTP_TEMPLATE_ID,
            'params': {
                'OTP_CODE': otp_code,
                'FIRST_NAME': first_name or 'User',
                'EXPIRY_MINUTES': settings.OTP_EXPIRY_MINUTES
            },
            'subject': f"Your {settings.PROJECT_NAME} Verification Code"
        }
        
        response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent to {to_email}, Brevo ID: {response.message_id}")
        return True
        
    except Exception as e:
        logger.error(f"Email sending failed to {to_email}: {str(e)}")
        return False
    