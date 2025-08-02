# utils/email_service.py
from sib_api_v3_sdk import Configuration, ApiClient, TransactionalEmailsApi
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_brevo_email(to_email, template_id, params=None, subject=None):
    """
    Universal email sending function for Brevo API
    Args:
        to_email: Recipient email address
        template_id: Brevo template ID
        params: Dictionary of template parameters
        subject: Email subject (optional, may be defined in template)
    """
    config = Configuration()
    config.api_key['api-key'] = settings.BREVO_API_KEY
    
    try:
        api_instance = TransactionalEmailsApi(ApiClient(config))
        
        send_smtp_email = {
            'sender': {
                'email': 'marketing@titanscareers.com',
                'name': settings.DEFAULT_FROM_NAME
            },
            'to': [{'email': to_email}],
            'templateId': int(template_id),
            'params': params or {},
        }
        
        if subject:
            send_smtp_email['subject'] = subject
            
        response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent to {to_email}, Brevo ID: {response.message_id}")
        return True
        
    except Exception as e:
        logger.error(f"Email sending failed to {to_email}: {str(e)}")
        return False