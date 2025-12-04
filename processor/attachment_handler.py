"""
Attachment handling utilities
Saves email attachments, runs OCR, and stores metadata in the database.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from database.db import get_connection
from database.models import Attachments
from processor.ocr import OCRProcessor

logger = logging.getLogger(__name__)


class AttachmentHandler:
    """Manage saving and processing email attachments"""

    def __init__(self, database_path: str, attachments_dir: str = "./data/attachments",
                 ocr_processor: Optional[OCRProcessor] = None):
        """
        Initialize the handler.

        Args:
            database_path: Path to SQLite database.
            attachments_dir: Base directory for saved attachments.
            ocr_processor: Optional OCRProcessor instance (for testing or customization).
        """
        self.db_path = database_path
        self.attachments_dir = attachments_dir
        self.ocr_processor = ocr_processor or OCRProcessor()

        try:
            os.makedirs(self.attachments_dir, exist_ok=True)
            logger.info("Attachment directory ready: %s", self.attachments_dir)
        except Exception as exc:
            logger.error("Failed to create attachments directory %s: %s", attachments_dir, exc, exc_info=True)
            raise

    def save_attachment(self, email_id: str, filename: str, file_data: bytes) -> str:
        """
        Save an attachment to disk, ensuring unique filenames.

        Args:
            email_id: ID of the source email (used for subdirectory).
            filename: Original filename from the email.
            file_data: Raw file bytes.

        Returns:
            Filepath where the attachment was saved.
        """
        if not filename:
            logger.error("Missing filename for attachment on email %s", email_id)
            raise ValueError("Filename is required")

        if file_data is None:
            logger.error("No data provided for attachment %s on email %s", filename, email_id)
            raise ValueError("Attachment data is required")

        try:
            email_dir = self._get_email_dir(email_id)
            filepath, final_name = self._build_unique_path(email_dir, filename)

            with open(filepath, "wb") as file_handle:
                file_handle.write(file_data)

            logger.info("Saved attachment %s for email %s at %s", final_name, email_id, filepath)
            return filepath
        except Exception as exc:
            logger.error("Failed to save attachment %s for email %s: %s", filename, email_id, exc, exc_info=True)
            raise

    def process_and_store(self, email_id: str, filename: str, filepath: str,
                          note_id: Optional[int] = None,
                          assignment_id: Optional[int] = None) -> Dict[str, Optional[Any]]:
        """
        Run OCR on an attachment and store metadata/results in the database.

        Args:
            email_id: Email the attachment belongs to.
            filename: Original filename.
            filepath: Local path to the saved attachment.
            note_id: Optional related note ID.
            assignment_id: Optional related assignment ID.

        Returns:
            Dictionary with attachment_id, ocr_status, ocr_text, and error keys.
        """
        if not filepath or not os.path.exists(filepath):
            logger.error("Attachment file not found for processing: %s", filepath)
            raise FileNotFoundError(f"Attachment not found at {filepath}")

        ocr_result = {"success": False, "text": "", "error": None}
        try:
            ocr_result = self.ocr_processor.process_attachment(filepath)
        except Exception as exc:
            ocr_result["error"] = str(exc)
            logger.error("OCR processing failed for %s: %s", filepath, exc, exc_info=True)

        ocr_status = "success" if ocr_result.get("success") else "failed"
        ocr_text = ocr_result.get("text") or None
        error_message = ocr_result.get("error")

        conn = None
        attachment_id = None
        try:
            conn = get_connection(self.db_path)
            attachment_id = Attachments.create(
                conn,
                email_id=email_id,
                filename=os.path.basename(filename),
                filepath=filepath,
                ocr_text=ocr_text,
                note_id=note_id,
                assignment_id=assignment_id,
            )
            logger.info("Stored attachment metadata id=%s for email %s", attachment_id, email_id)
        except Exception as exc:
            logger.error("Failed to store attachment metadata for %s: %s", filepath, exc, exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

        return {
            "attachment_id": attachment_id,
            "ocr_status": ocr_status,
            "ocr_text": ocr_text,
            "error": error_message,
        }

    def link_to_note(self, attachment_id: int, note_id: int) -> None:
        """
        Link an existing attachment record to a note.
        """
        conn = None
        try:
            conn = get_connection(self.db_path)
            Attachments.link_to_note(conn, attachment_id, note_id)
            logger.info("Linked attachment %s to note %s", attachment_id, note_id)
        except Exception as exc:
            logger.error("Failed to link attachment %s to note %s: %s", attachment_id, note_id, exc, exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    def link_to_assignment(self, attachment_id: int, assignment_id: int) -> None:
        """
        Link an existing attachment record to an assignment.
        """
        conn = None
        try:
            conn = get_connection(self.db_path)
            Attachments.link_to_assignment(conn, attachment_id, assignment_id)
            logger.info("Linked attachment %s to assignment %s", attachment_id, assignment_id)
        except Exception as exc:
            logger.error(
                "Failed to link attachment %s to assignment %s: %s",
                attachment_id,
                assignment_id,
                exc,
                exc_info=True,
            )
            raise
        finally:
            if conn:
                conn.close()

    def get_attachments_for_email(self, email_id: str) -> List[Dict]:
        """
        Retrieve all attachments for a given email ID.
        """
        conn = None
        try:
            conn = get_connection(self.db_path)
            return Attachments.get_by_email(conn, email_id)
        except Exception as exc:
            logger.error("Failed to fetch attachments for email %s: %s", email_id, exc, exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    def _get_email_dir(self, email_id: str) -> str:
        """Ensure per-email directory exists and return its path."""
        email_dir = os.path.join(self.attachments_dir, str(email_id))
        os.makedirs(email_dir, exist_ok=True)
        return email_dir

    def _build_unique_path(self, directory: str, filename: str) -> Tuple[str, str]:
        """
        Build a unique filepath inside directory, appending timestamp/counter if needed.

        Returns:
            Tuple of (full_filepath, final_filename)
        """
        safe_name = os.path.basename(filename) or "attachment"
        name, ext = os.path.splitext(safe_name)
        candidate = os.path.join(directory, safe_name)

        counter = 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        while os.path.exists(candidate):
            candidate = os.path.join(directory, f"{name}_{timestamp}_{counter}{ext}")
            counter += 1

        return candidate, os.path.basename(candidate)
