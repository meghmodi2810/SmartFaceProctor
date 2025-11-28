"""
Brevo (Sendinblue) HTTP API Email Backend for Django
This backend uses Brevo's API instead of SMTP to avoid port blocking issues on cloud platforms like Render.
"""
import os
import logging
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException
    BREVO_AVAILABLE = True
except ImportError:
    BREVO_AVAILABLE = False
    logger.warning("Brevo SDK not installed. Install with: pip install sib-api-v3-sdk")


class BrevoEmailBackend(BaseEmailBackend):
    """
    Django email backend that uses Brevo's HTTP API instead of SMTP.
    This is more reliable on cloud platforms that block SMTP ports.
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = os.environ.get('BREVO_API_KEY', '')
        
        if not BREVO_AVAILABLE:
            if not self.fail_silently:
                raise ImportError("Brevo SDK is not installed. Run: pip install sib-api-v3-sdk")
            logger.error("Brevo SDK not available")
            return
        
        if not self.api_key:
            if not self.fail_silently:
                raise ValueError("BREVO_API_KEY environment variable is not set")
            logger.error("BREVO_API_KEY not configured")
            return
        
        # Configure Brevo API
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = self.api_key
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email messages sent.
        """
        if not BREVO_AVAILABLE or not self.api_key:
            logger.error("Cannot send emails - Brevo not configured properly")
            return 0
        
        num_sent = 0
        for message in email_messages:
            try:
                sent = self._send_message(message)
                if sent:
                    num_sent += 1
            except Exception as e:
                logger.error(f"Failed to send email: {e}")
                if not self.fail_silently:
                    raise
        
        return num_sent
    
    def _send_message(self, message):
        """Send a single email message using Brevo API."""
        try:
            # Prepare recipient list
            to_recipients = [{"email": recipient} for recipient in message.to]
            
            # Prepare email data
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to_recipients,
                sender={"email": message.from_email or settings.DEFAULT_FROM_EMAIL},
                subject=message.subject,
                html_content=message.body if message.content_subtype == 'html' else None,
                text_content=message.body if message.content_subtype != 'html' else None,
            )
            
            # Add CC if present
            if message.cc:
                send_smtp_email.cc = [{"email": recipient} for recipient in message.cc]
            
            # Add BCC if present
            if message.bcc:
                send_smtp_email.bcc = [{"email": recipient} for recipient in message.bcc]
            
            # Add reply-to if present
            if message.reply_to:
                send_smtp_email.reply_to = {"email": message.reply_to[0]}
            
            # Send email via Brevo API
            api_response = self.api_instance.send_transac_email(send_smtp_email)
            
            logger.info(f"✅ Email sent successfully via Brevo API: {api_response.message_id}")
            return True
            
        except ApiException as e:
            logger.error(f"❌ Brevo API error: {e}")
            if not self.fail_silently:
                raise
            return False
        except Exception as e:
            logger.error(f"❌ Error sending email: {e}")
            if not self.fail_silently:
                raise
            return False
