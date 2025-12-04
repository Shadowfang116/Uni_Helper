"""
Uni Helper - Jarvis AI Academic Assistant
Main entry point for the application
"""

import signal
import sys
import time
from datetime import datetime

from config import Config
from database.db import initialize_database, get_connection, test_connection
from database.models import ProcessedEmails
from email_handler.poller import EmailPoller
from email_handler.parser import EmailParser
from email_handler.sender import EmailSender
from ai.client import AIClient
from ai.processor import AIProcessor
from scheduler.tasks import TaskScheduler
from processor.queue import ProcessingQueue


class UniHelper:
    """Main application class"""

    def __init__(self):
        """Initialize Uni Helper"""
        self.running = False
        self.poller = None
        self.email_parser = None
        self.email_sender = None
        self.ai_processor = None
        self.scheduler = None
        self.processing_queue = None

        # Handle graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\n⏹️  Shutdown signal received...")
        self.stop()
        sys.exit(0)

    def initialize(self):
        """Initialize all components"""
        print("\n" + "=" * 60)
        print("🤖 Uni Helper - Jarvis AI Academic Assistant")
        print("=" * 60)

        # Check configuration
        print("\n📋 Checking configuration...")
        Config.print_status()

        if not Config.is_configured():
            print("\n❌ Configuration incomplete!")
            print("\n📝 Setup Instructions:")
            print("1. Copy .env.template to .env")
            print("2. Fill in your credentials:")
            print("   - Gmail email and app password")
            print("   - AI API key (Claude or OpenAI)")
            print("3. Run this script again")
            print("\nFor detailed setup instructions, see README.md")
            return False

        # Initialize database
        print(f"\n🗄️  Initializing database...")
        try:
            initialize_database(Config.DATABASE_PATH)
            test_connection(Config.DATABASE_PATH)
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False

        # Initialize email components
        print("\n📧 Initializing email handlers...")
        try:
            self.poller = EmailPoller(
                Config.GMAIL_EMAIL,
                Config.GMAIL_APP_PASSWORD
            )

            if not self.poller.connect():
                return False

            self.email_parser = EmailParser()
            self.email_sender = EmailSender(
                Config.GMAIL_EMAIL,
                Config.GMAIL_APP_PASSWORD
            )

        except Exception as e:
            print(f"❌ Email initialization failed: {e}")
            return False

        # Initialize AI components
        print("\n🤖 Initializing AI processor...")
        try:
            ai_client = AIClient()
            self.ai_processor = AIProcessor(Config.DATABASE_PATH, ai_client)
        except Exception as e:
            print(f"❌ AI initialization failed: {e}")
            return False

        # Initialize scheduler
        print("\n⏰ Initializing task scheduler...")
        try:
            self.scheduler = TaskScheduler(Config.DATABASE_PATH)
            self.scheduler.start()
        except Exception as e:
            print(f"❌ Scheduler initialization failed: {e}")
            return False

        # Initialize processing queue
        print("\n⚙️  Initializing processing queue...")
        try:
            self.processing_queue = ProcessingQueue()
            self.processing_queue.start()
        except Exception as e:
            print(f"❌ Processing queue initialization failed: {e}")
            return False

        print("\n" + "=" * 60)
        print("✅ All systems initialized successfully!")
        print("=" * 60)

        return True

    def process_email_callback(self, email_id: str, email_message):
        """
        Callback function for processing emails
        Submits email to processing queue instead of processing directly

        Args:
            email_id: Email ID from IMAP
            email_message: Email message object
        """
        try:
            # Parse email
            parsed_email = self.email_parser.parse(email_id, email_message)

            print(f"\n📨 New Email Received")
            print(f"   From: {parsed_email['from']}")
            print(f"   Subject: {parsed_email['subject']}")

            # Get sender address for reply
            from_address = parsed_email['from']
            # Extract email from "Name <email@domain.com>" format
            if '<' in from_address:
                from_address = from_address.split('<')[1].split('>')[0]

            # Package email data for queue
            email_data = {
                'email_id': email_id,
                'parsed_email': parsed_email,
                'from_address': from_address
            }

            # Submit to processing queue
            if self.processing_queue and self.processing_queue.running:
                self.processing_queue.submit(email_data, self._process_email_worker)
            else:
                print(f"   ⚠️  Queue not running, processing directly")
                self._process_email_worker(email_data)

        except Exception as e:
            print(f"   ❌ Error submitting email to queue: {e}")
            import traceback
            traceback.print_exc()

    def _process_email_worker(self, email_data: dict):
        """
        Worker function that processes emails from the queue
        This runs in the background worker thread

        Args:
            email_data: Dictionary containing email_id, parsed_email, from_address
        """
        email_id = email_data['email_id']
        parsed_email = email_data['parsed_email']
        from_address = email_data['from_address']

        try:
            # Process with AI
            result = self.ai_processor.process_email(parsed_email)

            # Send response
            if result.get('success'):
                print(f"   ✓ Processing successful")

                # Send confirmation email
                self.email_sender.send_confirmation(
                    to_address=from_address,
                    confirmation_message=result['message'],
                    original_subject=parsed_email['subject']
                )

                # Mark email as processed
                conn = get_connection(Config.DATABASE_PATH)
                ProcessedEmails.create(conn, email_id, parsed_email['subject'])
                conn.close()

            else:
                print(f"   ⚠️  Processing completed with warnings")

                # Still send response (error message)
                self.email_sender.send_confirmation(
                    to_address=from_address,
                    confirmation_message=result.get('message', 'Processing failed'),
                    original_subject=parsed_email['subject']
                )

        except Exception as e:
            print(f"   ❌ Error processing email: {e}")
            import traceback
            traceback.print_exc()

    def is_email_processed(self, email_id: str) -> bool:
        """
        Check if email was already processed

        Args:
            email_id: Email ID to check

        Returns:
            True if already processed
        """
        conn = get_connection(Config.DATABASE_PATH)
        is_processed = ProcessedEmails.is_processed(conn, email_id)
        conn.close()
        return is_processed

    def start(self):
        """Start the application"""
        if not self.initialize():
            print("\n❌ Initialization failed. Exiting.")
            return

        self.running = True

        print("\n" + "=" * 60)
        print("🚀 Uni Helper is now running!")
        print("=" * 60)
        print(f"📧 Monitoring: {Config.GMAIL_EMAIL}")
        print(f"🔄 Polling interval: {Config.POLL_INTERVAL} seconds")
        print(f"⏰ Daily reminders: {Config.REMINDER_TIME} UTC")
        print("\nPress Ctrl+C to stop")
        print("=" * 60 + "\n")

        # Start polling loop
        try:
            self.poller.start_polling(
                callback=self.process_email_callback,
                is_processed_callback=self.is_email_processed,
                interval=Config.POLL_INTERVAL
            )
        except KeyboardInterrupt:
            print("\n⏹️  Stopped by user")
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()

    def stop(self):
        """Stop the application"""
        if not self.running:
            return

        print("\n🛑 Shutting down Uni Helper...")

        # Stop processing queue first (finish pending emails)
        if self.processing_queue:
            self.processing_queue.stop(timeout=30)

        # Stop poller
        if self.poller:
            self.poller.stop_polling()

        # Stop scheduler
        if self.scheduler:
            self.scheduler.stop()

        self.running = False
        print("✅ Shutdown complete")


def main():
    """Main entry point"""
    app = UniHelper()
    app.start()


if __name__ == "__main__":
    main()
