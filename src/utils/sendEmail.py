import os
import smtplib
import ssl
from email.mime.text import MIMEText

from dotenv import load_dotenv
from flask_limiter import RateLimitExceeded
from src.types.error.AppError import AppError


def sendEmail(subject: str, sender: str, recipients: str | list[str], 
              body: str, requiresHTML: bool | None = False) -> None:
        """
                Send a simple text-only mail.

                :param subject: Email subject.
                :param sender: Sender's email.
                :param recipients: Recipient(s) email(s).
                :body body: Email body.
                :param requiresHTML: Optional. Whether HTML is needed to parse the email body. Default to `False`.
        """
        load_dotenv()
        context = ssl.create_default_context()

        if not requiresHTML:
                msg = MIMEText(body)
        else:
                msg = MIMEText(body, 'html')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipients

        with smtplib.SMTP(host="smtp.gmail.com", port=587) as server:
                # port 587 for TLS
                server.starttls(context=context)
                server.login(user=sender, password=os.getenv('DEV_ADMIN_GMAIL_APP_PASSWORD'))
                server.set_debuglevel(1)
                server.sendmail(from_addr=sender, 
                                to_addrs=recipients, 
                                msg=msg.as_string())
                server.quit()