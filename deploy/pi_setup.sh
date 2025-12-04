#!/usr/bin/env bash

# One-time setup for Uni Helper on Raspberry Pi
# Usage: APP_DIR=/home/fahad/Uni_Helper ./deploy/pi_setup.sh

set -euo pipefail

APP_DIR="${APP_DIR:-$(pwd)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$APP_DIR/venv}"
DATA_DIR="${DATA_DIR:-$APP_DIR/data}"
MODEL_DIR="${MODEL_DIR:-$APP_DIR/models}"

echo "==> App directory: $APP_DIR"
echo "==> Virtualenv:    $VENV_DIR"

echo "==> Installing OS dependencies (may prompt for sudo)..."
sudo apt-get update -y
sudo apt-get install -y \
  python3-venv python3-dev python3-pip \
  build-essential cmake pkg-config \
  tesseract-ocr libtesseract-dev poppler-utils libopenblas-dev

echo "==> Ensuring directories..."
mkdir -p "$APP_DIR" "$DATA_DIR" "$MODEL_DIR"

echo "==> Creating virtualenv..."
$PYTHON_BIN -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "==> Upgrading pip and installing Python deps..."
pip install --upgrade pip
pip install --no-cache-dir -r "$APP_DIR/requirements.txt"

echo "==> Setup complete."
echo "Next:"
echo "  1) Place your .env in $APP_DIR/.env (copy from .env.template)."
echo "  2) Copy the TinyLlama GGUF model into $MODEL_DIR (update LOCAL_MODEL_PATH if different)."
echo "  3) Run ./deploy/pi_service_install.sh to install/start the systemd service."
