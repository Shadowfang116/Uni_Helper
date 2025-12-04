#!/usr/bin/env bash

# Install and enable the Uni Helper systemd service on Raspberry Pi
# Usage: APP_DIR=/home/fahad/Uni_Helper USER=fahad ./deploy/pi_service_install.sh

set -euo pipefail

APP_DIR="${APP_DIR:-$(pwd)}"
USER_NAME="${USER:-$(whoami)}"
SERVICE_NAME="unihelper.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
PY_BIN="${APP_DIR}/venv/bin/python"
LOG_FILE="${APP_DIR}/jarvis.log"
DB_PATH="${APP_DIR}/data/unihelper.db"
MODEL_PATH="${APP_DIR}/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

echo "==> Installing systemd service as $SERVICE_PATH"

sudo tee "$SERVICE_PATH" > /dev/null <<EOF
[Unit]
Description=Uni Helper (Jarvis AI) service
After=network.target

[Service]
User=${USER_NAME}
WorkingDirectory=${APP_DIR}
Environment=ENVIRONMENT=production
Environment=DATABASE_PATH=${DB_PATH}
Environment=LOCAL_MODEL_PATH=${MODEL_PATH}
ExecStart=${PY_BIN} -u main.py
Restart=on-failure
RestartSec=5
StandardOutput=append:${LOG_FILE}
StandardError=append:${LOG_FILE}

[Install]
WantedBy=multi-user.target
EOF

echo "==> Reloading systemd..."
sudo systemctl daemon-reload

echo "==> Enabling and starting ${SERVICE_NAME}..."
sudo systemctl enable "${SERVICE_NAME}"
sudo systemctl restart "${SERVICE_NAME}"

echo "==> Service status:"
sudo systemctl status "${SERVICE_NAME}" --no-pager -l | head -n 50

echo "==> Tail logs with:"
echo "   sudo journalctl -u ${SERVICE_NAME} -f"
