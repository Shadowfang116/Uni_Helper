# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Uni_Helper is an email-based AI academic assistant ("Jarvis") that processes emails via Gmail IMAP/SMTP. It uses AI (Claude or OpenAI) to classify intent, extract entities, and manage academic tasks in a SQLite database with automated reminders via APScheduler.

**Core Flow:**
```
Gmail IMAP → EmailPoller → EmailParser → AIProcessor → Database
                                              ↓
                                         Response via SMTP
                                              ↓
                                    TaskScheduler (APScheduler)
                                              ↓
                                    Daily reminder emails
```

## Development Commands

### Running the Application

**Start Jarvis (foreground):**
```bash
python main.py
```

**Start Jarvis (background with logging):**
```bash
nohup ./venv/bin/python main.py > jarvis.log 2>&1 &
# or
./venv/bin/python -u main.py > /tmp/jarvis_output.log 2>&1 &
```

**Monitor logs:**
```bash
tail -f jarvis.log
# or
tail -f /tmp/jarvis_output.log
```

**Stop Jarvis:**
```bash
pkill -f "python.*main.py"
# or
kill $(cat /tmp/jarvis.pid)  # if PID was saved
```

### Testing Individual Components

**Test configuration:**
```bash
python config.py
```

**Test database setup:**
```bash
python database/db.py
```

**Test database models (CRUD operations):**
```bash
python database/models.py
```

**Test email IMAP connection:**
```bash
python email_handler/poller.py
```

**Test AI client:**
```bash
python ai/client.py
```

**Test AI processor (intent classification + entity extraction):**
```bash
python ai/processor.py
```

**Test scheduler and reminders:**
```bash
python scheduler/tasks.py
```

### Environment Setup

**Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # or ./venv/bin/activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
# or with venv
./venv/bin/pip install -r requirements.txt
```

**Configure environment:**
```bash
cp .env.template .env
# Edit .env with your credentials
```

**Required environment variables:**
- `GMAIL_EMAIL` - Gmail address
- `GMAIL_APP_PASSWORD` - Gmail app password (16-char from Google)
- `AI_PROVIDER` - "claude" or "openai"
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` - AI provider API key
- `POLL_INTERVAL` - Email polling interval in seconds (default: 60)
- `REMINDER_TIME` - Daily reminder time in HH:MM format (default: 09:00 UTC)
- `DATABASE_PATH` - SQLite database path (default: ./data/unihelper.db)

### Database Queries

**Check database contents:**
```bash
./venv/bin/python -c "
from database.db import get_connection
from database.models import Classes, Notes, Assignments

conn = get_connection('./data/unihelper.db')
print('Classes:', Classes.get_all(conn))
print('Assignments:', Assignments.get_upcoming(conn, days=30))
print('Notes:', len(Notes.search(conn, '', limit=100)))
conn.close()
"
```

## Architecture Details

### Email Processing Pipeline

1. **EmailPoller** (`email_handler/poller.py`) - Connects via IMAP, polls every `POLL_INTERVAL` seconds
2. **EmailParser** (`email_handler/parser.py`) - Extracts subject, body, attachments from raw email
3. **AIProcessor** (`ai/processor.py`) - Main processing logic:
   - `classify_intent()` - Determines if email is ASSIGNMENT, NOTE, QUERY, or GENERAL
   - `extract_assignment_entities()` - Extracts class_name, due_date, title, description, priority
   - `extract_note_entities()` - Extracts class_name, content, note_type, tags
   - `process_assignment()` - Saves to database, generates confirmation
   - `process_note()` - Saves to database, generates confirmation
   - `process_query()` - Searches database, generates AI response
4. **EmailSender** (`email_handler/sender.py`) - Sends confirmations/responses via SMTP
5. **ProcessedEmails** model - Tracks email_id to prevent duplicate processing

### AI Client Abstraction

**AIClient** (`ai/client.py`) provides unified interface for both providers:
- `generate(system_prompt, user_prompt)` - Returns text response
- `generate_json(system_prompt, user_prompt)` - Returns parsed JSON for structured extraction
- Automatically selects Claude or OpenAI based on `Config.AI_PROVIDER`
- Claude: Uses `claude-3-5-sonnet-20241022` model
- OpenAI: Uses `gpt-4-turbo-preview` model

**Prompts** (`ai/prompts.py`) contains:
- `JARVIS_SYSTEM_PROMPT` - Defines Jarvis personality (professional, witty, addresses user as "sir")
- Intent classification prompts
- Entity extraction prompts (assignments vs notes)
- Query understanding and response generation prompts
- Response templates for confirmations and errors

### Database Schema

**4 Core Tables:**

1. **classes** - Stores course names (auto-created from AI extraction)
   - `id`, `name` (unique), `code`, `created_at`

2. **notes** - Stores lecture notes/concepts
   - `id`, `class_id` (FK), `content`, `note_type`, `metadata` (JSON), `created_at`

3. **assignments** - Stores tasks with due dates
   - `id`, `class_id` (FK), `title`, `description`, `due_date`, `reminder_hours`, `status` ('pending'/'completed'), `created_at`, `reminded_at`

4. **processed_emails** - Deduplication tracking
   - `id`, `email_id` (unique), `subject`, `processed_at`

**Models** (`database/models.py`) provide CRUD operations:
- `Classes.get_or_create(conn, name)` - Atomic find-or-create
- `Assignments.get_upcoming(conn, days)` - Query assignments within timeframe
- `Assignments.get_due_soon(conn, hours)` - Find assignments needing reminders (due within hours, not yet reminded)
- `Notes.search(conn, query, limit)` - Full-text search on note content

### Scheduler Architecture

**TaskScheduler** (`scheduler/tasks.py`):
- Uses APScheduler with `BackgroundScheduler` (timezone: UTC)
- **ReminderScheduler** runs daily at `Config.REMINDER_TIME` (default 09:00 UTC)
- `check_and_send_reminders()` queries `Assignments.get_due_soon()` and sends emails via `EmailSender.send_reminder()`
- After sending, marks assignment with `Assignments.mark_reminded()` to prevent duplicates

### Main Application Loop

**UniHelper class** (`main.py`):
1. `initialize()` - Sets up database, email handlers, AI processor, scheduler
2. `start()` - Begins polling loop via `EmailPoller.start_polling()`
3. `process_email_callback()` - Called for each new email:
   - Parses email → AI processes → Sends response → Marks as processed
4. Signal handlers (SIGINT/SIGTERM) for graceful shutdown

## Important Implementation Notes

### AI Version Compatibility

The OpenAI library version matters. If you see `Client.__init__() got an unexpected keyword argument 'proxies'` error:

```bash
./venv/bin/pip install --upgrade openai
```

Current working version: `openai>=2.8.1`

### Email Processing Deduplication

Every processed email's ID is stored in `processed_emails` table. The `is_email_processed()` callback prevents reprocessing emails if Jarvis restarts.

### Date Parsing

AI returns dates in ISO format (`YYYY-MM-DDTHH:MM:SS`). Parse with:
```python
from datetime import datetime
due_date = datetime.fromisoformat(entities['due_date'])
```

Always validate that AI returned a due_date before creating assignments - return error response if missing.

### Jarvis Personality

All responses must:
- Address user as "sir" (occasionally, not every sentence)
- Sign off with "- Jarvis"
- Be concise but helpful
- Use professional tone with occasional wit
- Include relevant emojis sparingly (📚, 📝, ⏰, etc.)

Templates in `ai/prompts.py` maintain consistency.

### Testing Email Flow

To test end-to-end without waiting for polling:

1. Start Jarvis: `python main.py`
2. Send email to configured Gmail address
3. Watch console output for processing
4. Check inbox for Jarvis response (usually within 60 seconds)

Or test AI components in isolation (see Testing Individual Components above).

### Railway Deployment

The `Procfile` defines the process:
```
worker: python main.py
```

Railway auto-detects Python, installs from `requirements.txt`, and runs the worker process. Set all env vars in Railway dashboard.

## Common Issues

**"IMAP login failed"**: Verify Gmail app password (not regular password). Must have 2FA enabled.

**"No emails processed"**: Check that emails are unread. Jarvis only processes unread emails and marks them as read after processing.

**AI extraction returns null values**: Increase `max_tokens` in `generate_json()` calls or check prompt formatting.

**Scheduler not firing**: Verify `REMINDER_TIME` format (HH:MM). Check timezone (scheduler uses UTC).

**Database locked**: Only one connection can write at a time. Use `conn.close()` promptly after operations.

## Adding New Features

**To add new intent types:**
1. Update `format_intent_prompt()` in `ai/prompts.py` with new intent option
2. Add handling in `AIProcessor.process_email()` (main.py line ~385)
3. Create corresponding `process_<intent>()` method

**To add new database tables:**
1. Add schema to `database/db.py` in `initialize_database()`
2. Create model class in `database/models.py` with CRUD methods
3. Import and use in `ai/processor.py`

**To add new scheduled tasks:**
1. Create task function in `scheduler/tasks.py`
2. Add to `TaskScheduler.start()` with appropriate trigger

**To support attachments (images/PDFs):**
1. EmailParser already extracts attachments to `parsed_email['attachments']`
2. Add OCR processing in `AIProcessor` (consider pytesseract or multimodal AI)
3. Store attachment data in notes metadata or separate table
