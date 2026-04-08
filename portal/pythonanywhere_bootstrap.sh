#!/usr/bin/env bash

set -euo pipefail

# Usage:
#   bash pythonanywhere_bootstrap.sh https://github.com/<user>/<repo>.git
#
# If repo URL is omitted, update DEFAULT_REPO_URL below.

DEFAULT_REPO_URL="https://github.com/YOUR_USERNAME/opdipdreports.git"
REPO_URL="${1:-$DEFAULT_REPO_URL}"

PROJECT_ROOT="$HOME/opdipdreports"
APP_DIR="$PROJECT_ROOT/portal"
VENV_PATH="$HOME/.venvs/opdportal"

echo "[1/5] Preparing project directory..."
if [ -d "$PROJECT_ROOT/.git" ]; then
  cd "$PROJECT_ROOT"
  git pull --ff-only
else
  git clone "$REPO_URL" "$PROJECT_ROOT"
fi

echo "[2/5] Creating virtualenv if missing..."
if [ ! -d "$VENV_PATH" ]; then
  python3.11 -m venv "$VENV_PATH"
fi

echo "[3/5] Activating virtualenv..."
source "$VENV_PATH/bin/activate"

echo "[4/5] Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r "$APP_DIR/requirements.txt"

echo "[5/5] Bootstrap complete."
echo
echo "Next in PythonAnywhere Web tab:"
echo "- Source code: $APP_DIR"
echo "- Working directory: $APP_DIR"
echo "- Virtualenv: $VENV_PATH"
echo
echo "Then set env vars in Web tab:"
echo "- SECRET_KEY"
echo "- DATABASE_URL (optional, SQLite fallback works)"
echo
echo "Finally reload and test:"
echo "- https://YOUR_USERNAME.pythonanywhere.com/"
echo "- https://YOUR_USERNAME.pythonanywhere.com/health"
