"""
AI processing logic
Handles intent classification, entity extraction, and response generation
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from ai.client import AIClient
from ai.prompts import (
    JARVIS_SYSTEM_PROMPT,
    format_intent_prompt,
    format_entity_extraction_assignment,
    format_entity_extraction_note,
    format_query_understanding,
    format_query_response,
    ASSIGNMENT_CONFIRMATION_TEMPLATE,
    NOTE_CONFIRMATION_TEMPLATE,
    ERROR_RESPONSE_TEMPLATE
)
from database.db import get_connection
from database.models import Classes, Notes, Assignments
from processor.attachment_handler import AttachmentHandler
from processor.note_formatter import NoteFormatter


class AIProcessor:
    """AI processing pipeline for email handling"""

    def __init__(
        self,
        db_path: str,
        ai_client: Optional[AIClient] = None,
        attachment_handler: Optional[AttachmentHandler] = None,
        note_formatter: Optional[NoteFormatter] = None,
    ):
        """
        Initialize AI processor

        Args:
            db_path: Path to SQLite database
            ai_client: Optional AIClient instance (creates new if not provided)
            attachment_handler: Optional AttachmentHandler instance
            note_formatter: Optional NoteFormatter instance
        """
        self.db_path = db_path
        self.ai_client = ai_client or AIClient()
        self.attachment_handler = attachment_handler or AttachmentHandler(db_path)
        self.note_formatter = note_formatter or NoteFormatter()

    def classify_intent(self, subject: str, body: str) -> Dict[str, Any]:
        """
        Classify email intent

        Args:
            subject: Email subject
            body: Email body

        Returns:
            Dictionary with intent, confidence, and reasoning
        """
        prompt = format_intent_prompt(subject, body)

        try:
            result = self.ai_client.generate_json(
                JARVIS_SYSTEM_PROMPT,
                prompt,
                max_tokens=200
            )
            return result
        except Exception as e:
            print(f"  ✗ Intent classification failed: {e}")
            # Fallback to GENERAL
            return {
                "intent": "GENERAL",
                "confidence": 0.5,
                "reasoning": "Failed to classify, defaulting to GENERAL"
            }

    def extract_assignment_entities(self, subject: str, body: str) -> Dict[str, Any]:
        """
        Extract assignment information

        Args:
            subject: Email subject
            body: Email body

        Returns:
            Dictionary with class_name, due_date, title, description, priority
        """
        current_date = datetime.now().isoformat()
        prompt = format_entity_extraction_assignment(subject, body, current_date)

        try:
            result = self.ai_client.generate_json(
                JARVIS_SYSTEM_PROMPT,
                prompt,
                max_tokens=500
            )
            return result
        except Exception as e:
            print(f"  ✗ Entity extraction failed: {e}")
            return {
                "class_name": None,
                "due_date": None,
                "title": subject or "Untitled Assignment",
                "description": body[:200],
                "priority": "medium"
            }

    def extract_note_entities(self, subject: str, body: str) -> Dict[str, Any]:
        """
        Extract note information

        Args:
            subject: Email subject
            body: Email body

        Returns:
            Dictionary with class_name, content, note_type, tags
        """
        prompt = format_entity_extraction_note(subject, body)

        try:
            result = self.ai_client.generate_json(
                JARVIS_SYSTEM_PROMPT,
                prompt,
                max_tokens=500
            )
            return result
        except Exception as e:
            print(f"  ✗ Entity extraction failed: {e}")
            return {
                "class_name": None,
                "content": body,
                "note_type": "general",
                "tags": []
            }

    def process_assignment(self, parsed_email: Dict) -> Dict[str, Any]:
        """
        Process assignment email and save to database

        Args:
            parsed_email: Parsed email dictionary

        Returns:
            Result dictionary with success status and response message
        """
        subject = parsed_email['subject']
        body = parsed_email['body']

        print("  🤖 Extracting assignment details...")
        entities = self.extract_assignment_entities(subject, body)

        # Validate required fields
        if not entities.get('due_date'):
            return {
                'success': False,
                'error': 'no_due_date',
                'message': ERROR_RESPONSE_TEMPLATE.format(
                    error_message="I couldn't find a due date in your email.",
                    suggestion="Please include the deadline (e.g., 'due October 20th at 11:59 PM')."
                )
            }

        # Parse due date
        try:
            due_date = datetime.fromisoformat(entities['due_date'])
        except:
            return {
                'success': False,
                'error': 'invalid_due_date',
                'message': ERROR_RESPONSE_TEMPLATE.format(
                    error_message="I couldn't parse the due date.",
                    suggestion="Please use a clear format like 'October 20, 2024 at 11:59 PM'."
                )
            }

        # Get or create class
        conn = get_connection(self.db_path)
        class_name = entities.get('class_name') or "General"
        class_id = Classes.get_or_create(conn, class_name)

        # Create assignment
        assignment_id = Assignments.create(
            conn,
            class_id=class_id,
            title=entities['title'],
            due_date=due_date,
            description=entities.get('description'),
            reminder_hours=24
        )

        conn.close()

        # Format confirmation
        due_formatted = due_date.strftime("%B %d, %Y at %I:%M %p")
        reminder_date = due_date - timedelta(hours=24)
        reminder_formatted = reminder_date.strftime("%B %d at %I:%M %p")

        additional_note = ""
        if entities.get('priority') == 'high':
            additional_note = "⚠️  This appears to be high priority. I recommend starting soon."

        message = ASSIGNMENT_CONFIRMATION_TEMPLATE.format(
            class_name=class_name,
            title=entities['title'],
            due_date_formatted=due_formatted,
            reminder_date_formatted=reminder_formatted,
            additional_note=additional_note
        )

        return {
            'success': True,
            'assignment_id': assignment_id,
            'message': message
        }

    def process_note(self, parsed_email: Dict) -> Dict[str, Any]:
        """
        Process note email and save to database

        Args:
            parsed_email: Parsed email dictionary

        Returns:
            Result dictionary with success status and response message
        """
        subject = parsed_email['subject']
        body = parsed_email['body']
        attachments_count = len(parsed_email.get('attachments') or [])

        print("  🤖 Extracting note details...")
        entities = self.extract_note_entities(subject, body)
        note_content = entities.get('content', body)

        conn = get_connection(self.db_path)
        attachments_info: List[Dict[str, Any]] = []
        formatted_path: Optional[str] = None

        try:
            class_name = entities.get('class_name') or "General"
            class_id = Classes.get_or_create(conn, class_name)

            metadata = {
                'note_type': entities.get('note_type', 'general'),
                'tags': entities.get('tags', []),
                'source': 'email',
                'subject': subject,
                'attachments_count': attachments_count,
                'email_id': parsed_email.get('email_id'),
                'received_at': parsed_email.get('date')
            }

            note_id = Notes.create(
                conn,
                class_id=class_id,
                content=note_content,
                note_type='text',
                metadata=metadata
            )

            if attachments_count:
                attachments_info = self._process_attachments_for_note(note_id, parsed_email)

            try:
                formatted_path = self.note_formatter.format_note(
                    class_name=class_name,
                    subject=subject,
                    note_content=note_content,
                    email_body=body,
                    note_id=note_id,
                    email_date=parsed_email.get('date'),
                    metadata=metadata,
                    attachments=attachments_info
                )
                Notes.set_formatted_path(conn, note_id, formatted_path)
            except Exception as exc:
                print(f"  ⚠️  Failed to format note file: {exc}")
        finally:
            conn.close()

        # Format confirmation
        content_preview = note_content[:100]
        if len(note_content) > 100:
            content_preview += "..."

        message = NOTE_CONFIRMATION_TEMPLATE.format(
            class_name=class_name,
            content_preview=content_preview
        )

        extra_lines = []
        if attachments_info:
            extra_lines.append(f"📎 Processed {len(attachments_info)} attachment(s) with OCR.")
        if formatted_path:
            extra_lines.append(f"📂 Saved to notes folder as {os.path.basename(formatted_path)}.")
        if extra_lines:
            message = message.replace("- Jarvis", "\n".join(extra_lines + ["", "- Jarvis"]))

        return {
            'success': True,
            'note_id': note_id,
            'message': message
        }

    def _process_attachments_for_note(self, note_id: int, parsed_email: Dict) -> List[Dict[str, Any]]:
        """
        Run OCR on attachments and persist metadata for a note.
        """
        attachments = parsed_email.get('attachments') or []
        if not attachments:
            return []

        email_id = parsed_email.get('email_id') or "unknown-email"
        print(f"  📎 Processing {len(attachments)} attachment(s)...")

        processed: List[Dict[str, Any]] = []
        for attachment in attachments:
            filename = attachment.get('filename') or os.path.basename(attachment.get('filepath') or "attachment")
            filepath = attachment.get('filepath')

            try:
                result = self.attachment_handler.process_and_store(
                    email_id=email_id,
                    filename=filename,
                    filepath=filepath,
                    note_id=note_id
                )
                processed.append({
                    "filename": filename,
                    "filepath": filepath,
                    "ocr_status": result.get("ocr_status"),
                    "ocr_text": result.get("ocr_text"),
                    "error": result.get("error"),
                })
                print(f"    ✓ Attachment processed: {filename} (OCR: {result.get('ocr_status')})")
            except Exception as exc:
                processed.append({
                    "filename": filename,
                    "filepath": filepath,
                    "ocr_status": "failed",
                    "ocr_text": None,
                    "error": str(exc),
                })
                print(f"    ✗ Failed to process attachment {filename}: {exc}")

        return processed

    def process_query(self, parsed_email: Dict) -> Dict[str, Any]:
        """
        Process query email and generate response

        Args:
            parsed_email: Parsed email dictionary

        Returns:
            Result dictionary with success status and response message
        """
        body = parsed_email['body']

        print("  🤖 Understanding query...")
        query_prompt = format_query_understanding(body)

        try:
            query_analysis = self.ai_client.generate_json(
                JARVIS_SYSTEM_PROMPT,
                query_prompt,
                max_tokens=300
            )
        except:
            query_analysis = {
                "query_type": "general",
                "time_filter": None,
                "class_filter": None,
                "search_terms": []
            }

        # Fetch relevant data
        conn = get_connection(self.db_path)
        data_str = ""

        if query_analysis['query_type'] == 'assignments_due':
            # Get upcoming assignments
            days = 1 if query_analysis['time_filter'] == 'today' else \
                   1 if query_analysis['time_filter'] == 'tomorrow' else \
                   7 if query_analysis['time_filter'] == 'this_week' else \
                   14 if query_analysis['time_filter'] == 'next_week' else 30

            assignments = Assignments.get_upcoming(conn, days=days)

            if assignments:
                data_str = "Upcoming Assignments:\n"
                for a in assignments:
                    due_date = datetime.fromisoformat(a['due_date']) if isinstance(a['due_date'], str) else a['due_date']
                    due_formatted = due_date.strftime("%B %d at %I:%M %p")
                    data_str += f"- {a['class_name']}: {a['title']} (Due: {due_formatted})\n"
            else:
                data_str = "No upcoming assignments found."

        elif query_analysis['query_type'] == 'notes_search':
            # Search notes
            if query_analysis['search_terms']:
                search_query = ' '.join(query_analysis['search_terms'])
                notes = Notes.search(conn, search_query, limit=10)

                if notes:
                    data_str = "Found Notes:\n"
                    for n in notes:
                        data_str += f"- {n.get('class_name', 'General')}: {n['content'][:100]}...\n"
                else:
                    data_str = f"No notes found matching '{search_query}'."
            else:
                data_str = "Please specify what you'd like to search for."

        elif query_analysis['query_type'] == 'class_info':
            # Get all classes
            classes = Classes.get_all(conn)
            if classes:
                data_str = "Your Classes:\n"
                for c in classes:
                    data_str += f"- {c['name']}\n"
            else:
                data_str = "No classes found in your system yet."

        else:
            data_str = "General query - no specific data retrieved."

        conn.close()

        # Generate response
        print("  🤖 Generating response...")
        response_prompt = format_query_response(body, data_str)

        try:
            response = self.ai_client.generate(
                JARVIS_SYSTEM_PROMPT,
                response_prompt,
                max_tokens=800
            )
        except:
            response = f"{data_str}\n\n- Jarvis"

        return {
            'success': True,
            'message': response
        }

    def process_email(self, parsed_email: Dict) -> Dict[str, Any]:
        """
        Main processing pipeline for emails

        Args:
            parsed_email: Parsed email dictionary from EmailParser

        Returns:
            Result dictionary with processing outcome
        """
        subject = parsed_email['subject']
        body = parsed_email['body']

        print(f"  🤖 Classifying intent...")

        # Classify intent
        intent_result = self.classify_intent(subject, body)
        intent = intent_result['intent']
        confidence = intent_result['confidence']

        print(f"  📊 Intent: {intent} (confidence: {confidence:.2f})")

        # Process based on intent
        if intent == 'ASSIGNMENT':
            return self.process_assignment(parsed_email)

        elif intent == 'NOTE':
            return self.process_note(parsed_email)

        elif intent == 'QUERY':
            return self.process_query(parsed_email)

        else:  # GENERAL
            message = """Acknowledged, sir.

I've received your message. If you need me to:
- Save an assignment: Include the due date
- Save notes: Share the content you'd like filed
- Query information: Ask me what you'd like to know

How may I assist you?

- Jarvis
"""
            return {
                'success': True,
                'message': message
            }


if __name__ == "__main__":
    # Test AI processor
    from config import Config
    from database.db import initialize_database

    print("Testing AI Processor...")

    if not Config.is_configured():
        print("✗ Configuration not complete")
        Config.print_status()
        exit(1)

    # Initialize database
    db_path = "./data/test.db"
    initialize_database(db_path)

    processor = AIProcessor(db_path)

    # Test assignment processing
    test_email = {
        'email_id': 'test-123',
        'subject': 'Data Mining Project',
        'body': 'We have a classification project due October 25, 2024 at 11:59 PM. Need to implement decision trees.',
        'from': 'test@test.com',
        'to': 'me@test.com',
        'date': datetime.now().isoformat(),
        'attachments': [],
        'has_attachments': False
    }

    print("\n--- Testing Assignment Processing ---")
    result = processor.process_email(test_email)
    print(f"Success: {result['success']}")
    print(f"Response:\n{result['message']}")

    print("\n✓ AI Processor test complete!")
