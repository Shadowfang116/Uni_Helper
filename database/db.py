"""
Database initialization and schema setup
Creates SQLite database with all required tables
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime


def _ensure_column(cursor: sqlite3.Cursor, table: str, column_name: str, column_def: str) -> None:
    """Add a column to a table if it doesn't already exist."""
    cursor.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cursor.fetchall()]
    if column_name not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def get_connection(db_path):
    """
    Get a connection to the SQLite database

    Args:
        db_path: Path to the database file

    Returns:
        sqlite3.Connection object
    """
    # Ensure the directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # Connect to database (creates if doesn't exist)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


def initialize_database(db_path):
    """
    Initialize the database with all required tables

    Args:
        db_path: Path to the database file
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Table 1: Classes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table 2: Notes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER,
            content TEXT NOT NULL,
            note_type TEXT DEFAULT 'text',
            metadata TEXT,
            formatted_file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    ''')

    # Table 3: Assignments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            due_date TIMESTAMP NOT NULL,
            reminder_hours INTEGER DEFAULT 24,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reminded_at TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    ''')

    # Table 4: Attachments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            ocr_text TEXT,
            note_id INTEGER,
            assignment_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE
        )
    ''')

    # Table 5: Processed Emails
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id TEXT UNIQUE NOT NULL,
            subject TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes for better performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_assignments_due_date
        ON assignments(due_date)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_assignments_status
        ON assignments(status)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_attachments_email_id
        ON attachments(email_id)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_attachments_note_id
        ON attachments(note_id)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_attachments_assignment_id
        ON attachments(assignment_id)
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_notes_class_id
        ON notes(class_id)
    ''')

    # Ensure newer columns exist on older databases
    _ensure_column(cursor, "notes", "formatted_file_path", "formatted_file_path TEXT")

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_processed_emails_email_id
        ON processed_emails(email_id)
    ''')

    conn.commit()
    conn.close()

    print(f"✓ Database initialized at {db_path}")


def reset_database(db_path):
    """
    Delete and recreate the database (USE WITH CAUTION)

    Args:
        db_path: Path to the database file
    """
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✓ Database deleted: {db_path}")

    initialize_database(db_path)
    print(f"✓ Database reset complete")


def test_connection(db_path):
    """
    Test database connection and print table information

    Args:
        db_path: Path to the database file
    """
    try:
        conn = get_connection(db_path)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"\n✓ Database connection successful: {db_path}")
        print(f"✓ Tables found: {len(tables)}")

        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count} rows")

        conn.close()
        return True

    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test database setup
    test_db_path = "./data/test.db"
    print("Testing database setup...")
    initialize_database(test_db_path)
    test_connection(test_db_path)
