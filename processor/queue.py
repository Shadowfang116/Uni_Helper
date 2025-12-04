"""
Email processing queue with background worker thread
Handles async processing of emails to prevent blocking the polling loop
"""

import queue
import threading
import time
import logging
from typing import Dict, Any, Callable, Optional

# Setup logging
logger = logging.getLogger(__name__)


class ProcessingQueue:
    """Manages async email processing with background worker thread"""

    def __init__(self):
        """
        Initialize processing queue

        Creates queue and worker thread but does not start it.
        Call start() to begin processing.
        """
        self.queue = queue.Queue()
        self.worker_thread: Optional[threading.Thread] = None
        self.running = False

        # Statistics tracking
        self.total_processed = 0
        self.total_errors = 0
        self.start_time: Optional[float] = None

        logger.info("ProcessingQueue initialized")

    def start(self):
        """Start the background worker thread"""
        if self.running:
            logger.warning("ProcessingQueue already running")
            return

        self.running = True
        self.start_time = time.time()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

        print("✓ Processing queue started")
        logger.info("Processing queue worker thread started")

    def stop(self, timeout: int = 30):
        """
        Stop the worker thread gracefully

        Args:
            timeout: Maximum seconds to wait for worker to finish (default: 30)
        """
        if not self.running:
            logger.warning("ProcessingQueue not running")
            return

        print("⏹️  Stopping processing queue...")
        logger.info("Stopping processing queue")

        self.running = False

        # Wait for worker to finish current item
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=timeout)

            if self.worker_thread.is_alive():
                logger.warning(f"Worker thread did not stop within {timeout}s timeout")
                print(f"⚠️  Worker thread did not stop within {timeout}s")
            else:
                logger.info("Worker thread stopped successfully")
                print("✓ Processing queue stopped")

    def submit(self, email_data: Dict[str, Any], callback: Callable):
        """
        Submit email for processing

        Args:
            email_data: Parsed email data dictionary
            callback: Function to process the email (receives email_data as argument)
        """
        if not self.running:
            logger.error("Cannot submit - ProcessingQueue not running")
            raise RuntimeError("ProcessingQueue not started. Call start() first.")

        queue_item = {
            'email_data': email_data,
            'callback': callback,
            'submitted_at': time.time()
        }

        self.queue.put(queue_item)

        subject = email_data.get('subject', 'No subject')
        logger.info(f"Email submitted to queue: '{subject}' (queue size: {self.queue.qsize()})")
        print(f"📬 Email queued for processing: {subject}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current queue status and statistics

        Returns:
            Dictionary with queue metrics:
                - queue_size: Number of emails waiting
                - total_processed: Total emails processed successfully
                - total_errors: Total processing errors
                - running: Whether worker is running
                - uptime_seconds: Time since start() was called
        """
        uptime = time.time() - self.start_time if self.start_time else 0

        return {
            'queue_size': self.queue.qsize(),
            'total_processed': self.total_processed,
            'total_errors': self.total_errors,
            'running': self.running,
            'uptime_seconds': uptime
        }

    def _worker(self):
        """
        Background worker thread that processes queue items

        Runs continuously while self.running is True.
        Handles errors gracefully so one failure doesn't crash the worker.
        """
        logger.info("Worker thread started")

        while self.running:
            try:
                # Get item from queue with timeout to check self.running periodically
                try:
                    queue_item = self.queue.get(timeout=1)
                except queue.Empty:
                    continue

                email_data = queue_item['email_data']
                callback = queue_item['callback']
                submitted_at = queue_item['submitted_at']

                wait_time = time.time() - submitted_at
                subject = email_data.get('subject', 'No subject')

                logger.info(f"Processing email: '{subject}' (waited {wait_time:.1f}s in queue)")
                print(f"⚙️  Processing: {subject}")

                try:
                    # Process the email
                    start_time = time.time()
                    callback(email_data)
                    processing_time = time.time() - start_time

                    self.total_processed += 1

                    logger.info(f"✓ Email processed successfully in {processing_time:.1f}s: '{subject}'")
                    print(f"✓ Completed: {subject} ({processing_time:.1f}s)")

                except Exception as e:
                    # Log error but continue processing other emails
                    self.total_errors += 1

                    logger.error(f"✗ Error processing email '{subject}': {e}", exc_info=True)
                    print(f"✗ Error processing '{subject}': {e}")

                finally:
                    # Mark task as done
                    self.queue.task_done()

            except Exception as e:
                # Catch any unexpected errors in worker loop
                logger.error(f"Unexpected error in worker thread: {e}", exc_info=True)
                time.sleep(1)  # Brief pause before continuing

        logger.info("Worker thread shutting down")


# Test function
def test_queue():
    """Test ProcessingQueue functionality"""
    import time

    print("Testing ProcessingQueue...\n")

    def mock_callback(email_data):
        """Mock email processing callback"""
        subject = email_data.get('subject', 'No subject')
        print(f"  [Callback] Processing: {subject}")
        time.sleep(2)  # Simulate processing time
        print(f"  [Callback] Done: {subject}")

    # Create and start queue
    pq = ProcessingQueue()
    pq.start()

    # Submit test emails
    for i in range(3):
        email_data = {
            'subject': f'Test Email {i+1}',
            'body': f'This is test email number {i+1}'
        }
        pq.submit(email_data, mock_callback)

    print(f"\nStatus: {pq.get_status()}\n")

    # Wait for processing
    print("Waiting for processing to complete...")
    time.sleep(8)

    print(f"\nFinal status: {pq.get_status()}\n")

    # Stop queue
    pq.stop()

    print("✓ Queue test complete!")


if __name__ == "__main__":
    # Configure logging for test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    test_queue()
