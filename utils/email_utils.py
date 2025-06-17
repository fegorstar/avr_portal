from decouple import config
import base64
import mimetypes
import random
import threading
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.conf import settings

class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send()

class Util:
    @staticmethod
    def send_email(data, use_html_content=True, use_resend=False):
        from_email = f"{settings.DEFAULT_FROM_NAME} <{settings.FROM_EMAIL_ADDRESS}>"

        if use_resend:
            # Use Resend SMTP #
            with get_connection(
                host=settings.RESEND_SMTP_HOST,
                port=settings.RESEND_SMTP_PORT,
                username=settings.RESEND_SMTP_USERNAME,
                password=config("RESEND_API_KEY"),
                use_tls=True,
            ) as connection:
                email = EmailMessage(
                    subject=data['email_subject'],
                    body=data['email_body'],
                    to=[data['to_email']],
                    from_email=from_email,
                    connection=connection,
                )

                if use_html_content:
                    email.content_subtype = 'html'

                if 'file_name' in data and 'file_content' in data:
                    file_content = base64.b64decode(data['file_content'])
                    content_type, encoding = mimetypes.guess_type(data['file_name'])
                    content_type = content_type or 'application/octet-stream'
                    email.attach(data['file_name'], file_content, content_type)

                email.send()
        else:
            # Use Django's default email backend
            from_email = settings.FROM_EMAIL_ADDRESS

            # Create an EmailMessage
            email = EmailMessage(
                subject=data['email_subject'],
                body=data['email_body'],
                to=[data['to_email']],
                from_email=from_email,
            )

            # Set the email body content
            if use_html_content:
                email.content_subtype = 'html'

            # Attach the file if provided
            if 'file_name' in data and 'file_content' in data:
                file_content = base64.b64decode(data['file_content'])
                content_type, encoding = mimetypes.guess_type(data['file_name'])
                content_type = content_type or 'application/octet-stream'
                email.attach(data['file_name'], file_content, content_type)

            # Create an instance of EmailThread with the email
            email_thread = EmailThread(email)

            # Start the email thread to send the email asynchronously
            email_thread.start()

def generate_verification_code():
    return str(random.randint(10000, 99999))
