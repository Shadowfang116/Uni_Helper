"""
Background task scheduler
Handles automated reminders using APScheduler
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from typing import Optional
import pytz

from config import Config
from database.db import get_connection
from database.models import Assignments
from email_handler.sender import EmailSender


class ReminderScheduler:
    """Manages automated assignment reminders"""

    def __init__(self, db_path: str, email_sender: EmailSender):
        """
        Initialize reminder scheduler

        Args:
            db_path: Path to SQLite database
            email_sender: EmailSender instance for sending reminders
        """
        self.db_path = db_path
        self.email_sender = email_sender
        self.scheduler = BackgroundScheduler(timezone=pytz.UTC)

    def check_and_send_reminders(self):
        """
        Check for assignments that need reminders and send emails
        This runs on schedule (e.g., daily at 9 AM)
        """
        try:
            print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running reminder check...")

            conn = get_connection(self.db_path)

            # Get assignments that need reminders
            # (due within reminder_hours and not yet reminded)
            assignments_to_remind = Assignments.get_due_soon(
                conn,
                hours=Config.REMINDER_HOURS_BEFORE
            )

            if not assignments_to_remind:
                print("   No reminders to send")
                conn.close()
                return

            print(f"   Found {len(assignments_to_remind)} assignment(s) needing reminders")

            # Send reminders
            for assignment in assignments_to_remind:
                try:
                    # Parse due date
                    due_date = assignment['due_date']
                    if isinstance(due_date, str):
                        due_date = datetime.fromisoformat(due_date)

                    # Send reminder email
                    success = self.email_sender.send_reminder(
                        to_address=Config.GMAIL_EMAIL,  # Send to user
                        assignment_title=assignment['title'],
                        class_name=assignment['class_name'],
                        due_date=due_date,
                        description=assignment.get('description')
                    )

                    if success:
                        # Mark as reminded
                        Assignments.mark_reminded(conn, assignment['id'])
                        print(f"   ✓ Sent reminder: {assignment['title']}")
                    else:
                        print(f"   ✗ Failed to send reminder: {assignment['title']}")

                except Exception as e:
                    print(f"   ✗ Error sending reminder for {assignment['title']}: {e}")

            conn.close()
            print("   Reminder check complete\n")

        except Exception as e:
            print(f"   ✗ Reminder check failed: {e}")
            import traceback
            traceback.print_exc()

    def start(self, reminder_time: Optional[str] = None):
        """
        Start the scheduler

        Args:
            reminder_time: Time to send reminders in HH:MM format (e.g., "09:00")
                          Defaults to Config.REMINDER_TIME
        """
        reminder_time = reminder_time or Config.REMINDER_TIME

        # Parse reminder time
        try:
            hour, minute = map(int, reminder_time.split(':'))
        except:
            print(f"✗ Invalid reminder time format: {reminder_time}")
            print("  Using default: 09:00")
            hour, minute = 9, 0

        # Schedule daily reminder check
        self.scheduler.add_job(
            self.check_and_send_reminders,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_reminder_check',
            name='Daily Assignment Reminder Check',
            replace_existing=True
        )

        # Start scheduler
        self.scheduler.start()
        print(f"✓ Reminder scheduler started (daily at {hour:02d}:{minute:02d} UTC)")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("⏹️  Reminder scheduler stopped")

    def run_check_now(self):
        """Manually trigger a reminder check (for testing)"""
        print("🔔 Running manual reminder check...")
        self.check_and_send_reminders()


class TaskScheduler:
    """Main task scheduler managing all background jobs"""

    def __init__(self, db_path: str):
        """
        Initialize task scheduler

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path

        # Initialize email sender
        self.email_sender = EmailSender(
            Config.GMAIL_EMAIL,
            Config.GMAIL_APP_PASSWORD
        )

        # Initialize reminder scheduler
        self.reminder_scheduler = ReminderScheduler(db_path, self.email_sender)

    def start(self):
        """Start all scheduled tasks"""
        print("\n" + "=" * 60)
        print("Starting Task Scheduler")
        print("=" * 60)

        # Start reminder scheduler
        self.reminder_scheduler.start()

        print("=" * 60 + "\n")

    def stop(self):
        """Stop all scheduled tasks"""
        self.reminder_scheduler.stop()

    def run_reminders_now(self):
        """Manually trigger reminder check (for testing)"""
        self.reminder_scheduler.run_check_now()


def test_scheduler():
    """Test the scheduler"""
    from config import Config
    from database.db import initialize_database
    from database.models import Classes, Assignments
    from datetime import datetime, timedelta

    print("Testing Scheduler...")

    if not Config.is_configured():
        print("✗ Configuration not complete")
        Config.print_status()
        return

    # Initialize test database
    db_path = "./data/test.db"
    initialize_database(db_path)

    # Add test assignment due tomorrow
    conn = get_connection(db_path)
    class_id = Classes.get_or_create(conn, "Test Class")

    due_date = datetime.now() + timedelta(hours=23)  # Due in 23 hours
    assignment_id = Assignments.create(
        conn,
        class_id=class_id,
        title="Test Assignment",
        due_date=due_date,
        description="This is a test assignment for reminder testing",
        reminder_hours=24
    )

    print(f"\n✓ Created test assignment (ID: {assignment_id})")
    print(f"  Due: {due_date.strftime('%Y-%m-%d %H:%M:%S')}")

    conn.close()

    # Create scheduler
    scheduler = TaskScheduler(db_path)

    # Test immediate reminder check
    print("\n--- Testing Immediate Reminder ---")
    scheduler.run_reminders_now()

    print("\n✓ Scheduler test complete!")
    print("  Check your email for the test reminder")


if __name__ == "__main__":
    test_scheduler()
