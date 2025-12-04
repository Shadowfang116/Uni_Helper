"""
Email parsing utilities
Extracts subject, body, and attachments from email messages
"""

import email
import os
from email.header import decode_header
from email.message import Message
from typing import Dict, List, Optional
from datetime import datetime


class EmailParser:
    """Parse email messages and extract relevant information"""

    def __init__(self, attachments_dir: str = "./data/attachments"):
        """
        Initialize email parser

        Args:
            attachments_dir: Directory to save email attachments
        """
        self.attachments_dir = attachments_dir
        if not os.path.exists(attachments_dir):
            os.makedirs(attachments_dir)

    @staticmethod
    def decode_subject(subject: str) -> str:
        """
        Decode email subject

        Args:
            subject: Raw subject string

        Returns:
            Decoded subject string
        """
        if not subject:
            return "No Subject"

        decoded_parts = decode_header(subject)
        decoded_subject = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded_subject += part.decode(encoding or 'utf-8', errors='ignore')
                except:
                    decoded_subject += part.decode('utf-8', errors='ignore')
            else:
                decoded_subject += part

        return decoded_subject.strip()

    @staticmethod
    def get_body(email_message: Message) -> str:
        """
        Extract email body (text/plain preferred, HTML as fallback)

        Args:
            email_message: Email message object

        Returns:
            Email body as string
        """
        body = ""

        # Check if email is multipart
        if email_message.is_multipart():
            # Iterate through email parts
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                # Get text/plain parts
                if content_type == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='ignore')
                        break  # Prefer plain text
                    except:
                        pass

                # Fallback to HTML if no plain text
                elif content_type == "text/html" and not body:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        html_body = payload.decode(charset, errors='ignore')
                        # Simple HTML to text conversion (remove tags)
                        import re
                        body = re.sub('<[^<]+?>', '', html_body)
                    except:
                        pass
        else:
            # Not multipart, get payload directly
            try:
                payload = email_message.get_payload(decode=True)
                charset = email_message.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
            except:
                body = str(email_message.get_payload())

        return body.strip()

    def get_attachments(self, email_message: Message, email_id: str) -> List[Dict]:
        """
        Extract and save email attachments

        Args:
            email_message: Email message object
            email_id: Unique email ID (for organizing attachments)

        Returns:
            List of attachment info dictionaries
        """
        attachments = []

        if not email_message.is_multipart():
            return attachments

        # Create directory for this email's attachments
        email_dir = os.path.join(self.attachments_dir, email_id)
        if not os.path.exists(email_dir):
            os.makedirs(email_dir)

        for part in email_message.walk():
            # Check if part is an attachment
            content_disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in content_disposition:
                # Get filename
                filename = part.get_filename()

                if filename:
                    # Decode filename if needed
                    decoded_filename = decode_header(filename)[0]
                    if isinstance(decoded_filename[0], bytes):
                        filename = decoded_filename[0].decode(decoded_filename[1] or 'utf-8')
                    else:
                        filename = decoded_filename[0]

                    # Save attachment
                    filepath = os.path.join(email_dir, filename)

                    try:
                        with open(filepath, 'wb') as f:
                            f.write(part.get_payload(decode=True))

                        attachments.append({
                            'filename': filename,
                            'filepath': filepath,
                            'content_type': part.get_content_type(),
                            'size': os.path.getsize(filepath)
                        })

                        print(f"    📎 Saved attachment: {filename}")

                    except Exception as e:
                        print(f"    ✗ Failed to save attachment {filename}: {e}")

        return attachments

    def parse(self, email_id: str, email_message: Message) -> Dict:
        """
        Parse email and extract all information

        Args:
            email_id: Unique email ID
            email_message: Email message object

        Returns:
            Dictionary with parsed email data
        """
        # Extract basic info
        from_addr = email_message.get("From", "")
        to_addr = email_message.get("To", "")
        date_str = email_message.get("Date", "")
        subject_raw = email_message.get("Subject", "")

        # Decode subject
        subject = self.decode_subject(subject_raw)

        # Get body
        body = self.get_body(email_message)

        # Get attachments
        attachments = self.get_attachments(email_message, email_id)

        return {
            'email_id': email_id,
            'from': from_addr,
            'to': to_addr,
            'subject': subject,
            'date': date_str,
            'body': body,
            'attachments': attachments,
            'has_attachments': len(attachments) > 0
        }


def test_parser():
    """Test email parser with a sample email"""
    # Create a sample email
    sample_email = """From: student@gmail.com
To: jarvis@example.com
Subject: Data Mining Assignment
Date: Mon, 1 Jan 2024 10:00:00 +0000

Hi Jarvis,

We have a classification project due October 20th at 11:59 PM.
Need to implement decision trees and random forests.

Thanks!
"""

    msg = email.message_from_string(sample_email)
    parser = EmailParser()
    parsed = parser.parse("test-123", msg)

    print("Parsed Email:")
    print(f"  Subject: {parsed['subject']}")
    print(f"  From: {parsed['from']}")
    print(f"  Body: {parsed['body'][:100]}...")
    print(f"  Attachments: {len(parsed['attachments'])}")


if __name__ == "__main__":
    test_parser()
