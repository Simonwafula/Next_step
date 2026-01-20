# This helper prepares the production environment referenced in the CyberPanel instructions.
# Run it once from `/home/nextstep.co.ke/public_html` as the `nexts7595` user.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_HOME="/home/nextstep.co.ke"
VENV_DIR="${DEPLOY_HOME}/.venv"
ENV_FILE="${DEPLOY_HOME}/.env"

ensure_required() {
  if [[ ! -d "$REPO_ROOT/backend" ]]; then
    echo "Error: this repository must be located at /home/nextstep.co.ke/public_html" >&2
    exit 1
  fi
}

warn_missing_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    cat <<'WARNING'
Warning: no production .env file found at /home/nextstep.co.ke/.env.
Place your production variables there before starting the backend services.
WARNING
  fi
}

ensure_required
warn_missing_env

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$REPO_ROOT/backend/requirements.txt"

echo "Production virtual environment ready at $VENV_DIR"
echo "Remember to activate it (source $VENV_DIR/bin/activate) before running backend commands."
