"""
Email sending via SMTP
Sends confirmation emails and reminders using Gmail SMTP
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime


class EmailSender:
    """Send emails via Gmail SMTP"""

    def __init__(self, email_address: str, app_password: str):
        """
        Initialize email sender

        Args:
            email_address: Gmail address
            app_password: Gmail app password
        """
        self.email_address = email_address
        self.app_password = app_password

    def send_email(self, to_address: str, subject: str, body: str,
                   reply_to: Optional[str] = None) -> bool:
        """
        Send an email via Gmail SMTP

        Args:
            to_address: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            reply_to: Optional reply-to email ID

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to_address
            msg['Subject'] = subject

            # Add reply-to header if provided
            if reply_to:
                msg['In-Reply-To'] = reply_to
                msg['References'] = reply_to

            # Attach body
            msg.attach(MIMEText(body, 'plain'))

            # Connect to Gmail SMTP
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.email_address, self.app_password)
                server.send_message(msg)

            print(f"  ✓ Email sent to {to_address}")
            return True

        except Exception as e:
            print(f"  ✗ Failed to send email: {e}")
            return False

    def send_confirmation(self, to_address: str, confirmation_message: str,
                         original_subject: str = None,
                         reply_to: Optional[str] = None) -> bool:
        """
        Send a confirmation email (Jarvis response)

        Args:
            to_address: Recipient email address
            confirmation_message: Jarvis response message
            original_subject: Original email subject (for Re: prefix)
            reply_to: Optional reply-to email ID

        Returns:
            True if sent successfully
        """
        subject = f"Re: {original_subject}" if original_subject else "Jarvis Response"
        return self.send_email(to_address, subject, confirmation_message, reply_to)

    def send_reminder(self, to_address: str, assignment_title: str,
                     class_name: str, due_date: datetime,
                     description: Optional[str] = None) -> bool:
        """
        Send an assignment reminder email

        Args:
            to_address: Recipient email address
            assignment_title: Assignment title
            class_name: Class name
            due_date: Due date
            description: Optional assignment description

        Returns:
            True if sent successfully
        """
        # Format due date
        due_str = due_date.strftime("%B %d, %Y at %I:%M %p")

        # Calculate time remaining
        time_remaining = due_date - datetime.now()
        hours_remaining = int(time_remaining.total_seconds() / 3600)

        # Create reminder message
        body = f"""Good morning, sir.

⚠️  Assignment Reminder

📚 Class: {class_name}
📝 Assignment: {assignment_title}
📅 Due: {due_str}
⏰ Time Remaining: {hours_remaining} hours
"""

        if description:
            body += f"\n📋 Details: {description}\n"

        body += """
I recommend you start working on this if you haven't already.

Would you like me to send any additional reminders today?

- Jarvis
"""

        subject = f"⚠️  Reminder: {assignment_title} Due Soon"
        return self.send_email(to_address, subject, body)


def format_jarvis_response(response_type: str, data: dict) -> str:
    """
    Format a Jarvis-style response based on response type

    Args:
        response_type: Type of response ('assignment', 'note', 'query', 'general')
        data: Data for the response

    Returns:
        Formatted Jarvis response string
    """
    if response_type == 'assignment':
        # Assignment confirmation
        due_str = data['due_date'].strftime("%B %d, %Y at %I:%M %p")
        reminder_str = data['due_date'].strftime("%B %d at %I:%M %p")

        return f"""Assignment logged, sir.

📚 {data['class_name']} - {data['title']}
📅 Due: {due_str}
⏰ Reminder set for {reminder_str} (24 hours before)

I'll notify you when the deadline approaches.

- Jarvis
"""

    elif response_type == 'note':
        # Note confirmation
        return f"""Noted under {data['class_name']}, sir.

📝 {data['content'][:100]}{'...' if len(data['content']) > 100 else ''}

Filed in your knowledge base for future reference.

- Jarvis
"""

    elif response_type == 'query':
        # Query response
        return data.get('response', 'I processed your query, sir.\n\n- Jarvis')

    elif response_type == 'error':
        # Error response
        return f"""I encountered an issue processing your request, sir.

❌ Error: {data.get('error', 'Unknown error')}

{data.get('suggestion', 'Please try again or rephrase your request.')}

- Jarvis
"""

    else:
        # General response
        return f"""{data.get('message', 'Request processed, sir.')}

- Jarvis
"""


def test_sender():
    """Test email sender"""
    from config import Config

    if not Config.GMAIL_EMAIL or not Config.GMAIL_APP_PASSWORD:
        print("✗ Gmail credentials not configured")
        return

    sender = EmailSender(Config.GMAIL_EMAIL, Config.GMAIL_APP_PASSWORD)

    # Test sending to self
    test_body = """This is a test email from Jarvis.

If you're reading this, the email sender is working correctly, sir.

- Jarvis
"""

    print(f"Sending test email to {Config.GMAIL_EMAIL}...")
    success = sender.send_email(
        Config.GMAIL_EMAIL,
        "Jarvis Test Email",
        test_body
    )

    if success:
        print("✓ Test email sent successfully!")
        print("  Check your inbox to confirm delivery")
    else:
        print("✗ Failed to send test email")


if __name__ == "__main__":
    test_sender()
