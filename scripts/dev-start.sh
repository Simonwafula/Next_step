#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"
ENV_FILE="${ROOT_DIR}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing .env at ${ENV_FILE}. Copy .env.example and update values."
  exit 1
fi

if [[ ! -d "${BACKEND_DIR}/venv3.11" ]]; then
  echo "Missing virtual environment at ${BACKEND_DIR}/venv3.11."
  exit 1
fi

# shellcheck disable=SC1091
source "${BACKEND_DIR}/venv3.11/bin/activate"

if ! python -m dotenv --help >/dev/null 2>&1; then
  echo "python-dotenv not available. Install backend requirements first."
  exit 1
fi

pids=()
cleanup() {
  for pid in "${pids[@]}"; do
    kill "${pid}" 2>/dev/null || true
  done
}
trap cleanup EXIT

echo "Starting backend on http://127.0.0.1:8000 ..."
(
  cd "${BACKEND_DIR}"
  python -m dotenv -f "${ENV_FILE}" run -- \
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
) &
pids+=("$!")

echo "Starting frontend on http://127.0.0.1:5173 ..."
python3 -m http.server 5173 --bind 127.0.0.1 --directory "${FRONTEND_DIR}" &
pids+=("$!")

echo "Open http://127.0.0.1:5173 (frontend) and http://127.0.0.1:8000/docs (API)."
echo "Press Ctrl+C to stop."

wait
