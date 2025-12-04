# Uni Helper – Session Resume Brief

## 1) Project Context & Current State
- Email-first academic assistant (“Jarvis”) that polls Gmail IMAP, parses emails, uses AI to classify/answer, persists to SQLite, and sends replies/reminders via SMTP + APScheduler.
- Current env (`config.py`): AI provider `openai` → model `gpt-4o`; Anthropic key placeholder present; local LLM optional via llama-cpp with default model path `./models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf`.
- `.env` loaded; config validation passes (`python3 config.py`). Environment set to `development`; poll interval 60s; reminder time 09:00 UTC; DB `./data/unihelper.db`.
- Latest run (`jarvis.log`) shows app initializes (scheduler + processors) but IMAP polling fails with SSL/EOF errors when fetching emails.

## 2) Identified Issues (from testing/logs)
- IMAP polling fails: repeated `socket error: EOF occurred in violation of protocol (_ssl.c:2406)` and `command: FETCH => System Error` immediately after startup. No screenshots supplied; only log evidence.
- Consequence: no emails processed; poller retries until shutdown.

## 3) Fix Plan (priority-ordered)
1. **P0 – Restore Gmail IMAP connectivity**: Verify app password validity, ensure IMAP access is enabled, and confirm no network/firewall blocks on Pi. Test with `imaplib` manually; if SSL issues persist, try forcing modern TLS context or switching to OpenSSL defaults.
2. **P1 – Harden poller reconnect logic**: Add explicit reconnect on SSL/EOF errors and backoff to avoid tight failure loops; ensure `self.connect()` is retried when `get_unread_emails()` errors.
3. **P1 – Credential/config sanity checks**: Double-check `.env` on Pi (GMAIL_EMAIL/GMAIL_APP_PASSWORD/AI_PROVIDER/openai key) and sanitize any accidentally committed secrets.
4. **P2 – End-to-end validation**: After IMAP fix, send test email; confirm processing, DB writes, and SMTP response; verify reminder scheduler still runs.
5. **P2 – Service reliability on Pi**: Reinstall/restart systemd service, confirm logs rotate to `jarvis.log`, and verify model path when `AI_PROVIDER=local`.

## 4) System Configuration Snapshot
- **Python**: 3.12.3 (local). Uses venv `./venv`.
- **AI**: Provider `openai`, model `gpt-4o` (`ai/client.py`). Anthropic (`claude-3-5-sonnet-20241022`) available but key placeholder; local model path default `./models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` (threads=4).
- **Environment**: `.env` in repo root (secrets present but redacted here). `ENVIRONMENT=development`; `DATABASE_PATH=./data/unihelper.db`; `POLL_INTERVAL=60`; `REMINDER_TIME=09:00`; `REMINDER_HOURS_BEFORE=24`.
- **Dependencies** (`requirements.txt`): anthropic 0.39.0, openai 1.54.3, httpx 0.27.2, apscheduler 3.10.4, python-dotenv 1.0.0, llama-cpp-python 0.2.11, Pillow 10.4.0, pytesseract 0.3.10, pdfplumber 0.11.0, pytz 2024.1.
- **Service scripts**: `deploy/pi_setup.sh` (installs deps + venv), `deploy/pi_service_install.sh` (systemd service using `venv/bin/python -u main.py`, DB at `/home/pi/Uni_Helper/data/unihelper.db`, model path `/home/pi/Uni_Helper/models/...`).

## 5) Test Results
- `python3 config.py` → config valid; all required env vars detected.
- Runtime log (`jarvis.log`) → app boot successful; scheduler started; IMAP fetch fails with SSL EOF; shutdown clean after manual stop.
- No other component/unit tests run in this session.

## 6) CLI Delegation Commands (per phase)
- **Prep/verify env**  
  - `cd /home/pi/Uni_Helper`  
  - `python3 -m venv venv && source venv/bin/activate` (if venv missing)  
  - `pip install --upgrade pip && pip install -r requirements.txt`  
  - `python3 config.py`
- **Reproduce IMAP failure**  
  - `source venv/bin/activate`  
  - `python3 main.py` (watch for IMAP errors)  
  - `tail -f jarvis.log`
- **Debug Gmail IMAP**  
  - `python3 - <<'PY'\nimport imaplib, ssl, os\nctx = ssl.create_default_context()\nm = imaplib.IMAP4_SSL('imap.gmail.com', ssl_context=ctx)\nm.login(os.getenv('GMAIL_EMAIL'), os.getenv('GMAIL_APP_PASSWORD'))\nprint('capabilities', m.capabilities)\nm.logout()\nPY`  
  - If failing, rotate app password and re-run; check network with `openssl s_client -connect imap.gmail.com:993`.
- **Implement fixes**  
  - Edit poller reconnect logic: `nano email_handler/poller.py` (or use `sed/apply_patch`).  
  - Ensure `.env` cleaned/redacted for commits.
- **End-to-end test**  
  - `source venv/bin/activate`  
  - `python3 main.py` (send test email; verify response)  
  - Inspect DB: `sqlite3 data/unihelper.db 'select * from assignments limit 5;'`
- **Service deploy on Pi**  
  - `APP_DIR=/home/pi/Uni_Helper ./deploy/pi_setup.sh`  
  - `APP_DIR=/home/pi/Uni_Helper USER=pi ./deploy/pi_service_install.sh`  
  - `sudo journalctl -u unihelper.service -f` / `sudo systemctl status unihelper.service --no-pager -l`

## 7) File Locations & Important Paths
- App entry: `main.py`
- Config/env: `config.py`, `.env`, `.env.template`
- AI: `ai/client.py`, `ai/prompts.py`, `ai/processor.py`
- Email: `email_handler/poller.py`, `email_handler/parser.py`, `email_handler/sender.py`
- Scheduler: `scheduler/tasks.py`
- Database: `database/db.py`, `database/models.py`, data file `data/unihelper.db`
- Attachments staging: `data/attachments/`
- Logs: `jarvis.log`
- Deployment: `deploy/pi_setup.sh`, `deploy/pi_service_install.sh`
- Model directory (local LLM): `/home/pi/Uni_Helper/models/`

## 8) Next Steps (commands to run)
1) Sync latest code to Pi (from local machine):  
`rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' /home/fahad/Desktop/Uni_Helper/ pi@206.21.118.18:/home/pi/Uni_Helper/`

2) On Pi, refresh deps & config check:  
`ssh pi@206.21.118.18 "cd /home/pi/Uni_Helper && python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt && python3 config.py"`

3) Re-test IMAP manually (after confirming new app password if needed):  
`ssh pi@206.21.118.18 "cd /home/pi/Uni_Helper && source venv/bin/activate && python3 - <<'PY'\nimport imaplib, ssl, os\nctx = ssl.create_default_context()\nm = imaplib.IMAP4_SSL('imap.gmail.com', ssl_context=ctx)\nm.login(os.getenv('GMAIL_EMAIL'), os.getenv('GMAIL_APP_PASSWORD'))\nprint('Login OK, capabilities:', m.capabilities)\nm.logout()\nPY"`

4) Run app interactively to observe polling:  
`ssh pi@206.21.118.18 "cd /home/pi/Uni_Helper && source venv/bin/activate && python3 main.py"` (send test email; watch log)

5) Install/restart service once IMAP works:  
`ssh pi@206.21.118.18 "cd /home/pi/Uni_Helper && APP_DIR=/home/pi/Uni_Helper USER=pi ./deploy/pi_service_install.sh"`  
`ssh pi@206.21.118.18 "sudo systemctl status unihelper.service --no-pager -l"`  
`ssh pi@206.21.118.18 "sudo journalctl -u unihelper.service -f"`

6) Quick DB sanity after processing:  
`ssh pi@206.21.118.18 "cd /home/pi/Uni_Helper && sqlite3 data/unihelper.db 'select id,title,due_date,status from assignments order by created_at desc limit 5;'"`
