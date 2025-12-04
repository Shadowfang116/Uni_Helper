"""
AI prompts for Jarvis personality and task processing
Contains all system prompts and templates
"""

# ============================================================================
# JARVIS PERSONALITY PROMPT
# ============================================================================

JARVIS_SYSTEM_PROMPT = """You are Jarvis, a concise, professional, and witty AI for Fahad.

Responsibilities:
- Organize notes/assignments, track deadlines/reminders, answer queries fast.
- Ask for clarification if details are missing; confirm when tasks are logged.

Style:
- Address the user as "sir" once per message.
- Keep replies brief, prefer bullets, use emojis sparingly (📚 📝 📅 ⏰).
- Always sign off with "- Jarvis".
"""


# ============================================================================
# INTENT CLASSIFICATION
# ============================================================================

INTENT_CLASSIFICATION_PROMPT = """Classify the email intent as NOTE, ASSIGNMENT, QUERY, or GENERAL.

Subject: {subject}
Body: {body}

Return JSON:
{{
  "intent": "NOTE|ASSIGNMENT|QUERY|GENERAL",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}"""


# ============================================================================
# ENTITY EXTRACTION
# ============================================================================

ENTITY_EXTRACTION_ASSIGNMENT_PROMPT = """Extract assignment details.

Subject: {subject}
Body: {body}
Current date: {current_date}

Return JSON:
{{
  "class_name": "string or null",
  "due_date": "YYYY-MM-DDTHH:MM:SS or null (if date only, set 23:59:00)",
  "title": "brief title",
  "description": "summary or null",
  "priority": "high|medium|low"
}}"""


ENTITY_EXTRACTION_NOTE_PROMPT = """Extract note details.

Subject: {subject}
Body: {body}

Return JSON:
{{
  "class_name": "string or null",
  "content": "clean summary",
  "note_type": "concept|definition|example|general",
  "tags": ["tag1", "tag2", "tag3"]
}}"""


# ============================================================================
# QUERY PROCESSING
# ============================================================================

QUERY_UNDERSTANDING_PROMPT = """Analyze the query.

Query: {query}

Return JSON:
{{
  "query_type": "assignments_due|notes_search|class_info|general",
  "time_filter": "today|tomorrow|this_week|next_week|all|null",
  "class_filter": "class name or null",
  "search_terms": ["term1", "term2"]
}}"""


QUERY_RESPONSE_GENERATION_PROMPT = """Respond as Jarvis.

Original Query: {query}
Retrieved Data: {data}

Guidelines: concise, bullet-first, one "sir", light emojis (📚 📝 📅 ⏰), sign "- Jarvis", mention if no data and suggest next steps.
"""


# ============================================================================
# CONFIRMATION MESSAGES
# ============================================================================

ASSIGNMENT_CONFIRMATION_TEMPLATE = """Assignment logged, sir.

📚 {class_name} - {title}
📅 Due: {due_date_formatted}
⏰ Reminder set for {reminder_date_formatted}

{additional_note}

- Jarvis
"""


NOTE_CONFIRMATION_TEMPLATE = """Noted under {class_name}, sir.

📝 {content_preview}

Filed in your knowledge base for future reference.

- Jarvis
"""


GENERAL_CONFIRMATION_TEMPLATE = """Acknowledged, sir.

{message}

- Jarvis
"""


ERROR_RESPONSE_TEMPLATE = """I encountered an issue processing your request, sir.

❌ {error_message}

{suggestion}

- Jarvis
"""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_intent_prompt(subject: str, body: str) -> str:
    """Format intent classification prompt"""
    return INTENT_CLASSIFICATION_PROMPT.format(
        subject=subject,
        body=body
    )


def format_entity_extraction_assignment(subject: str, body: str, current_date: str) -> str:
    """Format entity extraction prompt for assignments"""
    return ENTITY_EXTRACTION_ASSIGNMENT_PROMPT.format(
        subject=subject,
        body=body,
        current_date=current_date
    )


def format_entity_extraction_note(subject: str, body: str) -> str:
    """Format entity extraction prompt for notes"""
    return ENTITY_EXTRACTION_NOTE_PROMPT.format(
        subject=subject,
        body=body
    )


def format_query_understanding(query: str) -> str:
    """Format query understanding prompt"""
    return QUERY_UNDERSTANDING_PROMPT.format(query=query)


def format_query_response(query: str, data: str) -> str:
    """Format query response generation prompt"""
    return QUERY_RESPONSE_GENERATION_PROMPT.format(
        query=query,
        data=data
    )


if __name__ == "__main__":
    # Test prompt formatting
    print("Testing prompts...")

    test_subject = "Data Mining Assignment"
    test_body = "We have a project due October 20th at 11:59 PM"

    intent_prompt = format_intent_prompt(test_subject, test_body)
    print("\n=== Intent Classification Prompt ===")
    print(intent_prompt[:200] + "...")

    from datetime import datetime
    current_date = datetime.now().isoformat()
    entity_prompt = format_entity_extraction_assignment(test_subject, test_body, current_date)
    print("\n=== Entity Extraction Prompt ===")
    print(entity_prompt[:200] + "...")

    print("\n✓ Prompts loaded successfully")
