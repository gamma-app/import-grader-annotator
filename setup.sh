#!/usr/bin/env bash
# One-time setup: create the Python venv, install backend + frontend deps.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Backend: creating venv + installing deps"
python3 -m venv "$ROOT/backend/.venv"
"$ROOT/backend/.venv/bin/python" -m pip install --upgrade pip --quiet
"$ROOT/backend/.venv/bin/pip" install --only-binary=:all: -r "$ROOT/backend/requirements.txt"

echo "==> Frontend: installing deps + building UI"
( cd "$ROOT/frontend" && npm install && npm run build )

echo "Done."
echo "Next: copy .env.example to .env and set SLIDE_GRADER_DATA to your Google Drive folder."
echo "Then start the app with: ./run.sh"
