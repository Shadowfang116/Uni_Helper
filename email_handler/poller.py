"""
Email polling via IMAP
Monitors Gmail inbox for new emails and processes them
"""

import imaplib
import email
import time
import ssl
from email.header import decode_header
from typing import List, Dict, Optional, Callable
from config import Config


class EmailPoller:
    """Polls Gmail inbox for new emails using IMAP"""

    def __init__(self, email_address: str, app_password: str):
        """
        Initialize email poller

        Args:
            email_address: Gmail address
            app_password: Gmail app password (not regular password)
        """
        self.email_address = email_address
        self.app_password = app_password
        self.imap = None
        self.is_running = False
        self.ssl_context = ssl.create_default_context()
        self.max_retry_delay = 60  # Maximum retry delay in seconds

    def connect(self):
        """Connect to Gmail IMAP server with explicit SSL context"""
        try:
            self.imap = imaplib.IMAP4_SSL("imap.gmail.com", ssl_context=self.ssl_context)
            self.imap.login(self.email_address, self.app_password)
            print(f"✓ Connected to Gmail IMAP: {self.email_address}")
            return True
        except imaplib.IMAP4.error as e:
            print(f"✗ IMAP login failed: {e}")
            print("  Check your Gmail email and app password in .env")
            return False
        except ssl.SSLError as e:
            print(f"✗ SSL error during connection: {e}")
            return False
        except Exception as e:
            print(f"✗ IMAP connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
                print("✓ Disconnected from Gmail IMAP")
            except:
                pass

    def get_unread_emails(self) -> List[tuple]:
        """
        Fetch unread emails from inbox with SSL error handling

        Returns:
            List of tuples (email_id, email_message)
            Returns None on connection error (signals need to reconnect)
        """
        try:
            # Select inbox
            self.imap.select("INBOX")

            # Search for unread emails
            status, messages = self.imap.search(None, 'UNSEEN')

            if status != "OK":
                print("✗ Failed to search for emails")
                return []

            email_ids = messages[0].split()

            if not email_ids:
                return []

            emails = []
            for email_id in email_ids:
                # Fetch email by ID
                status, msg_data = self.imap.fetch(email_id, "(RFC822)")

                if status != "OK":
                    continue

                # Parse email
                raw_email = msg_data[0][1]
                email_message = email.message_from_bytes(raw_email)

                emails.append((email_id.decode(), email_message))

            return emails

        except (ssl.SSLError, imaplib.IMAP4.abort, ConnectionError, OSError) as e:
            # Connection-related errors - signal need to reconnect
            print(f"✗ Connection error fetching emails: {type(e).__name__}: {e}")
            print("  Connection lost - will attempt reconnect")
            return None  # Signal that reconnection is needed
        except Exception as e:
            print(f"✗ Error fetching emails: {e}")
            return []

    def mark_as_read(self, email_id: str):
        """
        Mark an email as read

        Args:
            email_id: Email ID to mark as read
        """
        try:
            self.imap.store(email_id, '+FLAGS', '\\Seen')
            print(f"  ✓ Marked email {email_id} as read")
        except Exception as e:
            print(f"  ✗ Failed to mark email as read: {e}")

    def poll(self, callback: Callable, is_processed_callback: Callable = None):
        """
        Poll for new emails once

        Args:
            callback: Function to call with each unread email
                      Should accept (email_id, email_message) as arguments
            is_processed_callback: Optional function to check if email was already processed
                                   Should accept email_id and return True if processed

        Returns:
            True if successful, False if connection error occurred
        """
        try:
            emails = self.get_unread_emails()

            # Check if connection error occurred (None signals reconnection needed)
            if emails is None:
                return False

            if not emails:
                return True

            print(f"\n📧 Found {len(emails)} unread email(s)")

            for email_id, email_message in emails:
                # Check if already processed (from database)
                if is_processed_callback and is_processed_callback(email_id):
                    print(f"  ⏭️  Skipping already processed email: {email_id}")
                    continue

                # Get subject for logging
                subject = email_message.get("Subject", "No Subject")
                if subject:
                    decoded_subject = decode_header(subject)[0]
                    if isinstance(decoded_subject[0], bytes):
                        subject = decoded_subject[0].decode(decoded_subject[1] or 'utf-8')
                    else:
                        subject = decoded_subject[0]

                print(f"  📨 Processing: {subject}")

                # Call the callback function to process the email
                try:
                    callback(email_id, email_message)
                except Exception as e:
                    print(f"  ✗ Error processing email: {e}")
                    import traceback
                    traceback.print_exc()

            return True

        except Exception as e:
            print(f"✗ Polling error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def start_polling(self, callback: Callable,
                     is_processed_callback: Callable = None,
                     interval: int = 60):
        """
        Start polling loop with exponential backoff on connection failures

        Args:
            callback: Function to call with each unread email
            is_processed_callback: Optional function to check if email was processed
            interval: Polling interval in seconds (default: 60)
        """
        self.is_running = True
        print(f"🔄 Starting email polling (every {interval}s)")
        print(f"   Monitoring: {self.email_address}")
        print("   Press Ctrl+C to stop\n")

        poll_count = 0
        consecutive_failures = 0
        retry_delay = 5  # Start with 5 seconds

        while self.is_running:
            try:
                poll_count += 1
                print(f"[Poll #{poll_count}] Checking for new emails...")

                # Poll and check for connection errors
                poll_success = self.poll(callback, is_processed_callback)

                if not poll_success:
                    # Connection error occurred - attempt reconnect with backoff
                    consecutive_failures += 1
                    print(f"  ⚠️  Connection error (failure #{consecutive_failures})")
                    print(f"  Attempting to reconnect in {retry_delay}s...")

                    self.disconnect()
                    time.sleep(retry_delay)

                    if self.connect():
                        print("  ✓ Reconnection successful")
                        consecutive_failures = 0
                        retry_delay = 5  # Reset delay
                    else:
                        print("  ✗ Reconnection failed")
                        # Exponential backoff (cap at max_retry_delay)
                        retry_delay = min(retry_delay * 2, self.max_retry_delay)

                        if consecutive_failures >= 5:
                            print(f"  ✗ Too many consecutive failures ({consecutive_failures}). Stopping poller.")
                            self.is_running = False
                            break
                else:
                    # Successful poll - reset failure tracking
                    if consecutive_failures > 0:
                        consecutive_failures = 0
                        retry_delay = 5

                    # Wait for next poll
                    time.sleep(interval)

            except KeyboardInterrupt:
                print("\n⏹️  Polling stopped by user")
                self.is_running = False
                break
            except Exception as e:
                print(f"✗ Unexpected polling loop error: {e}")
                import traceback
                traceback.print_exc()
                # Treat as connection error - attempt reconnect
                consecutive_failures += 1
                self.disconnect()
                time.sleep(retry_delay)

                if not self.connect():
                    retry_delay = min(retry_delay * 2, self.max_retry_delay)
                    if consecutive_failures >= 5:
                        print("  ✗ Too many failures. Stopping poller.")
                        self.is_running = False
                        break

        self.disconnect()

    def stop_polling(self):
        """Stop the polling loop"""
        self.is_running = False


def test_poller():
    """Test the email poller"""
    from config import Config

    if not Config.GMAIL_EMAIL or not Config.GMAIL_APP_PASSWORD:
        print("✗ Gmail credentials not configured")
        print("  Please set GMAIL_EMAIL and GMAIL_APP_PASSWORD in .env")
        return

    poller = EmailPoller(Config.GMAIL_EMAIL, Config.GMAIL_APP_PASSWORD)

    if not poller.connect():
        return

    def test_callback(email_id, email_message):
        subject = email_message.get("Subject", "No Subject")
        from_addr = email_message.get("From", "Unknown")
        print(f"    From: {from_addr}")
        print(f"    Subject: {subject}")
        print(f"    ID: {email_id}")

    print("\nFetching unread emails (test mode)...")
    poller.poll(test_callback)

    poller.disconnect()


if __name__ == "__main__":
    test_poller()
