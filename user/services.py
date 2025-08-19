import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.configuration = sib_api_v3_sdk.Configuration()
        self.configuration.api_key['api-key'] = settings.BREVO_API_KEY
    
    def send_individual_email(self, to_email, subject, html_content, teacher_name, teacher_email):
        """Send individual email using Brevo"""
        try:
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(self.configuration))
            
            sender = sib_api_v3_sdk.SendSmtpEmailSender(
                name=teacher_name,
                email=teacher_email
            )
            
            to = [sib_api_v3_sdk.SendSmtpEmailTo(email=to_email)]
            
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                sender=sender,
                to=to,
                subject=subject,
                html_content=html_content
            )
            
            api_response = api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Email sent to {to_email}: {api_response}")
            return True
            
        except ApiException as e:
            logger.error(f"Brevo API Error: {e}")
            return False
    
    def send_mass_email(self, to_emails, subject, html_content, teacher_name, teacher_email):
        """Send mass email using Brevo"""
        try:
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(self.configuration))
            
            sender = sib_api_v3_sdk.SendSmtpEmailSender(
                name=teacher_name,
                email=teacher_email
            )
            
            # Send in batches to avoid rate limits
            success_count = 0
            batch_size = 50
            
            for i in range(0, len(to_emails), batch_size):
                batch = to_emails[i:i + batch_size]
                to = [sib_api_v3_sdk.SendSmtpEmailTo(email=email) for email in batch]
                
                send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                    sender=sender,
                    to=to,
                    subject=subject,
                    html_content=html_content
                )
                
                api_response = api_instance.send_transac_email(send_smtp_email)
                success_count += len(batch)
                logger.info(f"Batch email sent to {len(batch)} recipients")
            
            return success_count
            
        except ApiException as e:
            logger.error(f"Brevo API Error: {e}")
            return 0