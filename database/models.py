"""
Database models and CRUD operations
Provides functions to interact with the database
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from database.db import get_connection


logger = logging.getLogger(__name__)


class Classes:
    """CRUD operations for classes table"""

    @staticmethod
    def create(conn, name: str, code: Optional[str] = None) -> int:
        """
        Create a new class

        Args:
            conn: Database connection
            name: Class name (e.g., "Data Mining")
            code: Class code (e.g., "CS 101")

        Returns:
            ID of created class
        """
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO classes (name, code) VALUES (?, ?)',
                (name, code)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Class already exists, return existing ID
            cursor.execute('SELECT id FROM classes WHERE name = ?', (name,))
            result = cursor.fetchone()
            return result[0] if result else None

    @staticmethod
    def get(conn, class_id: int) -> Optional[Dict]:
        """Get class by ID"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM classes WHERE id = ?', (class_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def find_by_name(conn, name: str) -> Optional[Dict]:
        """Find class by name (case-insensitive)"""
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM classes WHERE LOWER(name) = LOWER(?)',
            (name,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_or_create(conn, name: str, code: Optional[str] = None) -> int:
        """Get existing class ID or create new one"""
        existing = Classes.find_by_name(conn, name)
        if existing:
            return existing['id']
        return Classes.create(conn, name, code)

    @staticmethod
    def get_all(conn) -> List[Dict]:
        """Get all classes"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM classes ORDER BY name')
        return [dict(row) for row in cursor.fetchall()]


class Notes:
    """CRUD operations for notes table"""

    @staticmethod
    def create(conn, class_id: int, content: str,
               note_type: str = 'text', metadata: Optional[Dict] = None,
               formatted_file_path: Optional[str] = None) -> int:
        """
        Create a new note

        Args:
            conn: Database connection
            class_id: ID of the class this note belongs to
            content: Note content
            note_type: Type of note ('text', 'image', 'email')
            metadata: Additional metadata as dictionary
            formatted_file_path: Optional path to the saved formatted note

        Returns:
            ID of created note
        """
        cursor = conn.cursor()
        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute(
            'INSERT INTO notes (class_id, content, note_type, metadata, formatted_file_path) VALUES (?, ?, ?, ?, ?)',
            (class_id, content, note_type, metadata_json, formatted_file_path)
        )
        conn.commit()
        return cursor.lastrowid

    @staticmethod
    def get(conn, note_id: int) -> Optional[Dict]:
        """Get note by ID"""
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM notes WHERE id = ?', (note_id,))
        row = cursor.fetchone()
        if row:
            note = dict(row)
            if note['metadata']:
                note['metadata'] = json.loads(note['metadata'])
            return note
        return None

    @staticmethod
    def get_by_class(conn, class_id: int, limit: int = 50) -> List[Dict]:
        """Get all notes for a specific class"""
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM notes WHERE class_id = ? ORDER BY created_at DESC LIMIT ?',
            (class_id, limit)
        )
        notes = []
        for row in cursor.fetchall():
            note = dict(row)
            if note['metadata']:
                note['metadata'] = json.loads(note['metadata'])
            notes.append(note)
        return notes

    @staticmethod
    def set_formatted_path(conn, note_id: int, formatted_file_path: Optional[str]) -> bool:
        """Update the formatted file path for a note."""
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE notes SET formatted_file_path = ? WHERE id = ?',
                (formatted_file_path, note_id)
            )
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning("No note found to update formatted file path for id=%s", note_id)
                return False
            return True
        except sqlite3.Error as exc:
            logger.error("Failed to update formatted path for note id=%s: %s", note_id, exc, exc_info=True)
            raise

    @staticmethod
    def search(conn, query: str, limit: int = 20) -> List[Dict]:
        """Search notes by content"""
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT n.*, c.name as class_name
               FROM notes n
               LEFT JOIN classes c ON n.class_id = c.id
               WHERE n.content LIKE ?
               ORDER BY n.created_at DESC
               LIMIT ?''',
            (f'%{query}%', limit)
        )
        notes = []
        for row in cursor.fetchall():
            note = dict(row)
            if note['metadata']:
                note['metadata'] = json.loads(note['metadata'])
            notes.append(note)
        return notes


class Assignments:
    """CRUD operations for assignments table"""

    @staticmethod
    def create(conn, class_id: int, title: str, due_date: datetime,
               description: Optional[str] = None, reminder_hours: int = 24) -> int:
        """
        Create a new assignment

        Args:
            conn: Database connection
            class_id: ID of the class
            title: Assignment title
            due_date: Due date as datetime object
            description: Optional description
            reminder_hours: Hours before due date to send reminder

        Returns:
            ID of created assignment
        """
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO assignments
               (class_id, title, description, due_date, reminder_hours)
               VALUES (?, ?, ?, ?, ?)''',
            (class_id, title, description, due_date, reminder_hours)
        )
        conn.commit()
        return cursor.lastrowid

    @staticmethod
    def get(conn, assignment_id: int) -> Optional[Dict]:
        """Get assignment by ID"""
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT a.*, c.name as class_name
               FROM assignments a
               LEFT JOIN classes c ON a.class_id = c.id
               WHERE a.id = ?''',
            (assignment_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_upcoming(conn, days: int = 7, status: str = 'pending') -> List[Dict]:
        """
        Get upcoming assignments within specified days

        Args:
            conn: Database connection
            days: Number of days to look ahead
            status: Filter by status ('pending', 'completed', or None for all)

        Returns:
            List of assignment dictionaries
        """
        cursor = conn.cursor()
        end_date = datetime.now() + timedelta(days=days)

        query = '''SELECT a.*, c.name as class_name
                   FROM assignments a
                   LEFT JOIN classes c ON a.class_id = c.id
                   WHERE a.due_date <= ?'''

        params = [end_date]

        if status:
            query += ' AND a.status = ?'
            params.append(status)

        query += ' ORDER BY a.due_date ASC'

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_due_soon(conn, hours: int = 24) -> List[Dict]:
        """
        Get assignments that need reminders (due within specified hours and not yet reminded)

        Args:
            conn: Database connection
            hours: Hours threshold for reminders

        Returns:
            List of assignments needing reminders
        """
        cursor = conn.cursor()
        reminder_threshold = datetime.now() + timedelta(hours=hours)

        cursor.execute(
            '''SELECT a.*, c.name as class_name
               FROM assignments a
               LEFT JOIN classes c ON a.class_id = c.id
               WHERE a.due_date <= ?
               AND a.status = 'pending'
               AND a.reminded_at IS NULL
               ORDER BY a.due_date ASC''',
            (reminder_threshold,)
        )
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def update_status(conn, assignment_id: int, status: str):
        """Update assignment status"""
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE assignments SET status = ? WHERE id = ?',
            (status, assignment_id)
        )
        conn.commit()

    @staticmethod
    def mark_reminded(conn, assignment_id: int):
        """Mark assignment as reminded"""
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE assignments SET reminded_at = ? WHERE id = ?',
            (datetime.now(), assignment_id)
        )
        conn.commit()

    @staticmethod
    def get_by_class(conn, class_id: int) -> List[Dict]:
        """Get all assignments for a specific class"""
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT a.*, c.name as class_name
               FROM assignments a
               LEFT JOIN classes c ON a.class_id = c.id
               WHERE a.class_id = ?
               ORDER BY a.due_date DESC''',
            (class_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


class ProcessedEmails:
    """CRUD operations for processed_emails table"""

    @staticmethod
    def create(conn, email_id: str, subject: Optional[str] = None) -> int:
        """
        Mark an email as processed

        Args:
            conn: Database connection
            email_id: Unique email ID from IMAP
            subject: Email subject for reference

        Returns:
            ID of created record
        """
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO processed_emails (email_id, subject) VALUES (?, ?)',
                (email_id, subject)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Email already processed
            return None

    @staticmethod
    def is_processed(conn, email_id: str) -> bool:
        """Check if an email has been processed"""
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM processed_emails WHERE email_id = ?',
            (email_id,)
        )
        return cursor.fetchone() is not None

    @staticmethod
    def get_recent(conn, limit: int = 50) -> List[Dict]:
        """Get recently processed emails"""
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM processed_emails ORDER BY processed_at DESC LIMIT ?',
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]


class Attachments:
    """CRUD operations for attachments table"""

    @staticmethod
    def create(conn,
               email_id: str,
               filename: str,
               filepath: str,
               ocr_text: Optional[str] = None,
               note_id: Optional[int] = None,
               assignment_id: Optional[int] = None) -> int:
        """
        Insert a new attachment record.

        Args:
            conn: Database connection.
            email_id: Email ID the attachment came from.
            filename: Original filename.
            filepath: Saved filepath.
            ocr_text: Extracted text from OCR (optional).
            note_id: Optional linked note ID.
            assignment_id: Optional linked assignment ID.

        Returns:
            ID of created attachment.
        """
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT INTO attachments
                   (email_id, filename, filepath, ocr_text, note_id, assignment_id)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (email_id, filename, filepath, ocr_text, note_id, assignment_id)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as exc:
            logger.error(
                "Failed to create attachment %s for email %s: %s",
                filename,
                email_id,
                exc,
                exc_info=True
            )
            raise

    @staticmethod
    def get_by_id(conn, attachment_id: int) -> Optional[Dict[str, Any]]:
        """Get a single attachment by ID (None if not found)."""
        cursor = conn.cursor()
        try:
            cursor.execute(
                'SELECT * FROM attachments WHERE id = ?',
                (attachment_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as exc:
            logger.error("Failed to fetch attachment id=%s: %s", attachment_id, exc, exc_info=True)
            raise

    @staticmethod
    def get_by_email(conn, email_id: str) -> List[Dict[str, Any]]:
        """Get all attachments for an email."""
        return Attachments._get_by_field(conn, 'email_id', email_id)

    @staticmethod
    def get_by_note(conn, note_id: int) -> List[Dict[str, Any]]:
        """Get all attachments linked to a note."""
        return Attachments._get_by_field(conn, 'note_id', note_id)

    @staticmethod
    def get_by_assignment(conn, assignment_id: int) -> List[Dict[str, Any]]:
        """Get all attachments linked to an assignment."""
        return Attachments._get_by_field(conn, 'assignment_id', assignment_id)

    @staticmethod
    def update_ocr_text(conn, attachment_id: int, ocr_text: str) -> bool:
        """Update OCR text for an attachment."""
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE attachments SET ocr_text = ? WHERE id = ?',
                (ocr_text, attachment_id)
            )
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning("No attachment found to update OCR text for id=%s", attachment_id)
                return False
            return True
        except sqlite3.Error as exc:
            logger.error("Failed to update OCR text for attachment id=%s: %s", attachment_id, exc, exc_info=True)
            raise

    @staticmethod
    def link_to_note(conn, attachment_id: int, note_id: int) -> bool:
        """Link an attachment to a note."""
        return Attachments._update_link(conn, 'note_id', note_id, attachment_id)

    @staticmethod
    def link_to_assignment(conn, attachment_id: int, assignment_id: int) -> bool:
        """Link an attachment to an assignment."""
        return Attachments._update_link(conn, 'assignment_id', assignment_id, attachment_id)

    @staticmethod
    def delete(conn, attachment_id: int) -> bool:
        """Delete an attachment record."""
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM attachments WHERE id = ?', (attachment_id,))
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning("No attachment found to delete for id=%s", attachment_id)
                return False
            return True
        except sqlite3.Error as exc:
            logger.error("Failed to delete attachment id=%s: %s", attachment_id, exc, exc_info=True)
            raise

    @staticmethod
    def _get_by_field(conn, field: str, value: Any) -> List[Dict[str, Any]]:
        """Helper to fetch attachments filtered by a column."""
        allowed_fields = {"email_id", "note_id", "assignment_id"}
        if field not in allowed_fields:
            logger.error("Unsupported filter field for attachments: %s", field)
            raise ValueError(f"Unsupported field: {field}")

        cursor = conn.cursor()
        try:
            cursor.execute(
                f'''SELECT * FROM attachments
                   WHERE {field} = ?
                   ORDER BY created_at DESC''',
                (value,)
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as exc:
            logger.error("Failed to fetch attachments by %s=%s: %s", field, value, exc, exc_info=True)
            raise

    @staticmethod
    def _update_link(conn, field: str, value: int, attachment_id: int) -> bool:
        """Helper to set a foreign key field."""
        allowed_fields = {"note_id", "assignment_id"}
        if field not in allowed_fields:
            logger.error("Unsupported link field for attachments: %s", field)
            raise ValueError(f"Unsupported field: {field}")

        cursor = conn.cursor()
        try:
            cursor.execute(
                f'UPDATE attachments SET {field} = ? WHERE id = ?',
                (value, attachment_id)
            )
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning("No attachment found to update %s for id=%s", field, attachment_id)
                return False
            return True
        except sqlite3.Error as exc:
            logger.error("Failed to update %s for attachment id=%s: %s", field, attachment_id, exc, exc_info=True)
            raise


if __name__ == "__main__":
    # Test database models
    from config import Config
    from database.db import initialize_database

    print("Testing database models...")

    # Initialize database
    db_path = "./data/test.db"
    initialize_database(db_path)
    conn = get_connection(db_path)

    # Test Classes
    print("\n--- Testing Classes ---")
    class_id = Classes.create(conn, "Data Mining", "CS 101")
    print(f"Created class with ID: {class_id}")
    class_obj = Classes.get(conn, class_id)
    print(f"Retrieved class: {class_obj}")

    # Test Notes
    print("\n--- Testing Notes ---")
    note_id = Notes.create(
        conn, class_id,
        "Central Limit Theorem: sampling distribution approaches normal",
        metadata={"source": "lecture", "chapter": 5}
    )
    print(f"Created note with ID: {note_id}")
    note = Notes.get(conn, note_id)
    print(f"Retrieved note: {note}")

    # Test Assignments
    print("\n--- Testing Assignments ---")
    due_date = datetime.now() + timedelta(days=2)
    assignment_id = Assignments.create(
        conn, class_id,
        "Classification Project",
        due_date,
        "Implement decision trees and random forests"
    )
    print(f"Created assignment with ID: {assignment_id}")
    assignment = Assignments.get(conn, assignment_id)
    print(f"Retrieved assignment: {assignment}")

    # Test upcoming assignments
    upcoming = Assignments.get_upcoming(conn, days=7)
    print(f"Upcoming assignments: {len(upcoming)}")

    # Test ProcessedEmails
    print("\n--- Testing ProcessedEmails ---")
    email_record_id = ProcessedEmails.create(conn, "test-email-123", "Test Subject")
    print(f"Marked email as processed: {email_record_id}")
    is_proc = ProcessedEmails.is_processed(conn, "test-email-123")
    print(f"Email processed check: {is_proc}")

    conn.close()
    print("\n✓ All tests completed!")


__all__ = [
    "Classes",
    "Notes",
    "Assignments",
    "ProcessedEmails",
    "Attachments",
]
