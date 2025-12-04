"""
Note formatting utilities
Creates clean .txt files for notes organized by class.
"""

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class NoteFormatter:
    """Format note content into organized text files."""

    def __init__(self, base_dir: str = "./data/notes"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def format_note(
        self,
        class_name: str,
        subject: str,
        note_content: str,
        email_body: str,
        note_id: int,
        email_date: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Create a formatted note file and return its absolute path.
        """
        class_dir = self._ensure_class_dir(class_name)
        filename = self._build_filename(subject, note_id)
        filepath = self._dedupe_path(os.path.join(class_dir, filename))

        tags = []
        source = "email"
        if metadata:
            tags = metadata.get("tags") or []
            source = metadata.get("source", source)

        header_lines = [
            f"Class: {class_name or 'General'}",
            f"Subject: {subject or 'No Subject'}",
            f"Note ID: {note_id}",
            f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Source: {source}",
        ]

        if email_date:
            header_lines.append(f"Email Date: {email_date}")
        if tags:
            header_lines.append(f"Tags: {', '.join(tags)}")

        attachment_entries = attachments or []
        if attachment_entries:
            header_lines.append(f"Attachments: {len(attachment_entries)}")

        sections = [
            ("Summary", (note_content or "").strip() or "No content provided."),
            ("Original Email Body", (email_body or "").strip() or "No email body captured."),
        ]

        if attachment_entries:
            sections.append(
                (
                    "Attachments",
                    self._format_attachments(attachment_entries),
                )
            )

        body_parts = ["\n".join(header_lines)]
        for title, body in sections:
            body_parts.append(f"--- {title} ---\n{body}")

        file_text = "\n\n".join(body_parts).strip() + "\n"

        with open(filepath, "w", encoding="utf-8") as file_handle:
            file_handle.write(file_text)

        return os.path.abspath(filepath)

    def _format_attachments(self, attachments: List[Dict[str, Any]]) -> str:
        """Render attachment OCR details into text."""
        blocks: List[str] = []
        for attachment in attachments:
            filename = attachment.get("filename") or "attachment"
            filepath = attachment.get("filepath") or ""
            status = attachment.get("ocr_status") or "unknown"
            ocr_text = (attachment.get("ocr_text") or "").strip()
            error = attachment.get("error")

            blocks.append(f"[{filename}] (OCR: {status})")
            if ocr_text:
                blocks.append(ocr_text)
            else:
                blocks.append(error or "No text extracted.")

            if filepath:
                blocks.append(f"File: {filepath}")
            blocks.append("")  # spacer

        return "\n".join(blocks).strip()

    def _ensure_class_dir(self, class_name: str) -> str:
        """Create and return the directory for a class."""
        class_slug = self._slugify(class_name or "general") or "general"
        class_dir = os.path.join(self.base_dir, class_slug)
        os.makedirs(class_dir, exist_ok=True)
        return class_dir

    def _build_filename(self, subject: str, note_id: int) -> str:
        """Build a timestamped filename for the note."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = self._slugify(subject or "note") or "note"
        return f"{timestamp}-{slug}-note{note_id}.txt"

    def _dedupe_path(self, filepath: str) -> str:
        """Ensure the filepath is unique by appending a counter if needed."""
        base, ext = os.path.splitext(filepath)
        counter = 1
        candidate = filepath
        while os.path.exists(candidate):
            candidate = f"{base}_{counter}{ext}"
            counter += 1
        return candidate

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text into a filesystem-safe slug."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9]+", "-", text)
        return text.strip("-")[:80]


__all__ = ["NoteFormatter"]
