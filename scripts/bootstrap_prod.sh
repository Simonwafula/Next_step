#!/usr/bin/env bash
# One-shot production bootstrap for the NextStep CyberPanel VPS.
# Run as root on the VPS. This script expects /home/nextstep.co.ke/.env to exist.
set -euo pipefail

APP_USER="${APP_USER:-nexts7595}"
APP_GROUP="${APP_GROUP:-nexts7595}"
DEPLOY_HOME="${DEPLOY_HOME:-/home/nextstep.co.ke}"
REPO_ROOT="${REPO_ROOT:-/home/nextstep.co.ke/public_html}"
ENV_FILE="${ENV_FILE:-/home/nextstep.co.ke/.env}"
VENV_DIR="${VENV_DIR:-/home/nextstep.co.ke/.venv}"
AUTO_INSTALL="${AUTO_INSTALL:-0}"

require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "Error: run this script as root." >&2
    exit 1
  fi
}

ensure_paths() {
  if [[ ! -d "$REPO_ROOT" ]]; then
    echo "Error: repo not found at $REPO_ROOT" >&2
    exit 1
  fi
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: missing $ENV_FILE. Create it before running bootstrap." >&2
    exit 1
  fi
}

maybe_install() {
  local pkg="$1"
  if [[ "$AUTO_INSTALL" != "1" ]]; then
    echo "Missing $pkg. Install it and re-run, or set AUTO_INSTALL=1." >&2
    exit 1
  fi
  apt-get update
  apt-get install -y "$pkg"
}

require_cmd() {
  local cmd="$1"
  local pkg="${2:-}"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    if [[ -n "$pkg" ]]; then
      maybe_install "$pkg"
    else
      echo "Missing required command: $cmd" >&2
      exit 1
    fi
  fi
}

load_env() {
  set -o allexport
  source "$ENV_FILE"
  set +o allexport
}

ensure_env_value() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "$value" ]]; then
    echo "Error: $name is missing in $ENV_FILE" >&2
    exit 1
  fi
  if [[ "$value" == *REPLACE_WITH* || "$value" == *your_* || "$value" == *changeme* ]]; then
    echo "Error: $name looks like a placeholder in $ENV_FILE" >&2
    exit 1
  fi
}

ensure_ownership() {
  chown -R "$APP_USER:$APP_GROUP" "$REPO_ROOT"
  chown -R "$APP_USER:$APP_GROUP" "$DEPLOY_HOME/.env"
  if [[ -d "$VENV_DIR" ]]; then
    chown -R "$APP_USER:$APP_GROUP" "$VENV_DIR"
  fi
}

create_db_and_user() {
  require_cmd psql postgresql
  systemctl enable --now postgresql >/dev/null 2>&1 || true

  local user_exists
  user_exists=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${POSTGRES_USER}'")
  if [[ "$user_exists" != "1" ]]; then
    sudo -u postgres psql -c "CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';"
  fi

  local db_exists
  db_exists=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'")
  if [[ "$db_exists" != "1" ]]; then
    sudo -u postgres psql -c "CREATE DATABASE ${POSTGRES_DB};"
  fi
  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};"
}

ensure_redis() {
  if ! command -v redis-server >/dev/null 2>&1; then
    maybe_install redis-server
  fi
  systemctl enable --now redis-server >/dev/null 2>&1
}

bootstrap_venv() {
  require_cmd python3 python3
  sudo -u "$APP_USER" bash -lc "cd '$REPO_ROOT' && bash scripts/setup_prod_environment.sh"
}

run_migrations() {
  local alembic_cfg="$REPO_ROOT/backend/alembic.ini"
  if [[ -f "$alembic_cfg" ]]; then
    sudo -u "$APP_USER" bash -lc "set -o allexport; source '$ENV_FILE'; set +o allexport; source '$VENV_DIR/bin/activate'; cd '$REPO_ROOT/backend'; alembic -c '$alembic_cfg' upgrade head"
    return
  fi
  echo "alembic.ini not found; running SQLAlchemy init_db() instead."
  sudo -u "$APP_USER" bash -lc "set -o allexport; source '$ENV_FILE'; set +o allexport; source '$VENV_DIR/bin/activate'; cd '$REPO_ROOT/backend'; python -c \"from app.db.database import init_db; init_db()\""
}

write_systemd_units() {
  local timestamp
  timestamp=$(date +"%Y%m%d%H%M%S")

  for unit in nextstep-backend nextstep-celery nextstep-celery-beat; do
    if [[ -f "/etc/systemd/system/${unit}.service" ]]; then
      cp "/etc/systemd/system/${unit}.service" "/etc/systemd/system/${unit}.service.bak.${timestamp}"
    fi
  done

  cat > /etc/systemd/system/nextstep-backend.service <<EOF
[Unit]
Description=NextStep Career Platform Backend
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${REPO_ROOT}/backend
EnvironmentFile=${ENV_FILE}
Environment=PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin
ExecStart=${VENV_DIR}/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
EOF

  cat > /etc/systemd/system/nextstep-celery.service <<EOF
[Unit]
Description=NextStep Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${REPO_ROOT}/backend
EnvironmentFile=${ENV_FILE}
Environment=PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin
ExecStart=${VENV_DIR}/bin/celery -A app.core.celery_app worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
EOF

  cat > /etc/systemd/system/nextstep-celery-beat.service <<EOF
[Unit]
Description=NextStep Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${REPO_ROOT}/backend
EnvironmentFile=${ENV_FILE}
Environment=PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin
ExecStart=${VENV_DIR}/bin/celery -A app.core.celery_app beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
EOF

  systemctl daemon-reload
  systemctl enable nextstep-backend nextstep-celery nextstep-celery-beat
  systemctl restart nextstep-backend nextstep-celery nextstep-celery-beat
}

main() {
  require_root
  ensure_paths
  load_env
  ensure_env_value POSTGRES_USER
  ensure_env_value POSTGRES_PASSWORD
  ensure_env_value POSTGRES_DB
  ensure_env_value SECRET_KEY

  ensure_ownership
  create_db_and_user
  ensure_redis
  bootstrap_venv
  run_migrations
  write_systemd_units

  echo "Bootstrap complete. Check services with:"
  echo "  systemctl status nextstep-backend nextstep-celery nextstep-celery-beat"
}

main "$@"
