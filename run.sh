#!/usr/bin/env bash
# Run ReThread locally: starts Postgres in Docker, sets up the venv if needed,
# and runs the Flask app (which also serves the frontend). Safe to re-run.
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
BACKEND_ENV="$BACKEND_DIR/.env"
DB_CONTAINER=rethread-pg
DB_PORT=5433
APP_PORT="${PORT:-8010}"

# If backend/.env already points DATABASE_URL at a remote host (e.g. Supabase),
# use that instead of spinning up a local Docker Postgres container.
REMOTE_DB=""
if [ -f "$BACKEND_ENV" ]; then
  ENV_DATABASE_URL="$(grep -E '^DATABASE_URL=' "$BACKEND_ENV" | tail -1 | cut -d= -f2-)"
  if [ -n "$ENV_DATABASE_URL" ] && [[ "$ENV_DATABASE_URL" != *localhost* ]] && [[ "$ENV_DATABASE_URL" != *127.0.0.1* ]]; then
    REMOTE_DB=1
  fi
fi

echo "== 1/4 Postgres =="
if [ -n "$REMOTE_DB" ]; then
  echo "Using remote DATABASE_URL from backend/.env — skipping local Postgres container."
else
  if ! command -v docker &>/dev/null; then
    echo "Docker is not installed or not on PATH. Install Docker Desktop (with WSL integration) first."
    exit 1
  fi

  if [ "$(docker ps -aq -f name=^${DB_CONTAINER}$)" ]; then
    if [ "$(docker ps -q -f name=^${DB_CONTAINER}$)" ]; then
      echo "Postgres container already running, reusing it."
    else
      echo "Found a stopped Postgres container, starting it."
      docker start $DB_CONTAINER >/dev/null
    fi
  else
    echo "Creating Postgres container..."
    docker run -d --name $DB_CONTAINER \
      -e POSTGRES_USER=rethread -e POSTGRES_PASSWORD=rethread -e POSTGRES_DB=rethread \
      -p ${DB_PORT}:5432 postgres:16-alpine >/dev/null
  fi

  echo "Waiting for Postgres to accept connections..."
  for i in $(seq 1 30); do
    docker exec $DB_CONTAINER pg_isready -U rethread >/dev/null 2>&1 && break
    sleep 1
  done
  docker exec $DB_CONTAINER pg_isready -U rethread
fi

echo "== 2/4 Python environment =="
cd "$BACKEND_DIR"

# Support both Unix (venv/bin/python) and Windows (venv/Scripts/python.exe) venv layouts.
VENV_PYTHON=""
if [ -x "venv/bin/python" ]; then
  VENV_PYTHON="venv/bin/python"
elif [ -x "venv/Scripts/python.exe" ]; then
  VENV_PYTHON="venv/Scripts/python.exe"
fi

if [ -z "$VENV_PYTHON" ]; then
  echo "Creating venv..."
  PYTHON_BIN=""
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
      PYTHON_BIN="$candidate"
      break
    fi
  done
  if [ -z "$PYTHON_BIN" ]; then
    echo "No working python3/python found on PATH. Install Python 3 first."
    exit 1
  fi
  "$PYTHON_BIN" -m venv venv
  if [ -x "venv/bin/python" ]; then
    VENV_PYTHON="venv/bin/python"
  else
    VENV_PYTHON="venv/Scripts/python.exe"
  fi
  "$VENV_PYTHON" -m pip install -q -r requirements.txt
else
  echo "venv already exists, reusing it."
fi

echo "== 3/4 Config =="
if [ -z "$REMOTE_DB" ]; then
  export DATABASE_URL="postgresql://rethread:rethread@localhost:${DB_PORT}/rethread"
fi
export SESSION_SECRET="${SESSION_SECRET:-dev-secret}"
export GEOAPIFY_API_KEY="${GEOAPIFY_API_KEY:-}"
export PORT="$APP_PORT"
if [ -z "$GEOAPIFY_API_KEY" ]; then
  echo "NOTE: GEOAPIFY_API_KEY is not set — everything works except locator search."
  echo "      Run with:  GEOAPIFY_API_KEY=yourkey ./run.sh"
fi

echo "== 4/4 Starting app on http://localhost:${APP_PORT} =="
echo "Press Ctrl+C to stop. (Postgres container keeps running — remove it with: docker rm -f ${DB_CONTAINER})"
exec "$VENV_PYTHON" app.py
