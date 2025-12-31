import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str):
    """
    Sends an email using SMTP settings from config.
    This function is blocking, so it should be run in a background task.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(f"⚠️ SMTP credentials not set. Email to {to_email} would have been: {subject}\n{body}")
        print(f"📧 [MOCK EMAIL] To: {to_email}\nSubject: {subject}\nBody: {body}\n")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = settings.FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(settings.FROM_EMAIL, to_email, text)
        server.quit()
        
        logger.info(f"✅ Email sent to {to_email}")
        print(f"✅ Email sent to {to_email}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        print(f"❌ Failed to send email: {e}")
