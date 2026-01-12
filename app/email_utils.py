import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv


def send_email(to_email, subject, content):
    load_dotenv()
    gmail_user = os.environ["ACME_EMAIL"]  #'veidblock@gmail.com'
    app_password = os.environ[
        "ACME_EMAIL_SECRET"
    ]  #'dlwg kdgz nrty wmvx'  # 16-char app password
    smtp_server = os.environ[
        "ACME_EMAIL_SMTP"
    ]  #'dlwg kdgz nrty wmvx'  # 16-char app password
    smtp_port = os.environ[
        "ACME_EMAIL_SMTP_PORT"
    ]  #'dlwg kdgz nrty wmvx'  # 16-char app password

    msg = EmailMessage()
    msg.set_content(content)
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.starttls()  # Secure the connection
            smtp.login(gmail_user, app_password)
            smtp.send_message(msg)
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


def main():
    # Example usage
    recipient = "aghafoor77@gmail.com"
    subject = "Test Email from Python"
    body = "Hello!\n\nThis is a test email sent from a Python script using Gmail SMTP.\n\nRegards,\nPython App"

    send_email(recipient, subject, body)


if __name__ == "__main__":
    main()
