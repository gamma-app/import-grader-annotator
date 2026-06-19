#!/usr/bin/env bash
# Start the grader as ONE local service: FastAPI serves the API, the built UI,
# and rendered slide images at http://127.0.0.1:8000.
# Reads ./.env for the shared Google Drive data path (SLIDE_GRADER_DATA).
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load per-machine config (Drive path, optional cache dir / port) if present.
if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/.env"
  set +a
fi

if [ ! -x "$ROOT/backend/.venv/bin/python" ]; then
  echo "Backend venv missing. Run ./setup.sh first." >&2
  exit 1
fi
if [ ! -d "$ROOT/frontend/dist" ]; then
  echo "UI not built. Run ./setup.sh first (it runs 'npm run build')." >&2
  exit 1
fi

PORT="${PORT:-8000}"
URL="http://127.0.0.1:${PORT}"
echo "Slide-Pair Grader  ->  ${URL}"
echo "Shared data dir    ->  ${SLIDE_GRADER_DATA:-(default ./data — set SLIDE_GRADER_DATA in .env to use Google Drive)}"

# Open the browser shortly after the server comes up.
(
  sleep 1.5
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"
  fi
) >/dev/null 2>&1 &

cd "$ROOT/backend"
exec ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
