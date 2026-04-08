# Deployment

This is the canonical deployment document for Next Step.

If this file disagrees with older deployment notes in the repo, follow this file.

## Production Topology

- Domain: `nextstep.co.ke`
- Repo root: `/home/nextstep.co.ke/public_html`
- Frontend docroot: `/home/nextstep.co.ke/public_html/frontend`
- Shared env file: `/home/nextstep.co.ke/.env`
- Python runtime: `/home/nextstep.co.ke/.venv`
- App user/group: `nexts9742:nexts9742`
- Backend bind address: `127.0.0.1:8010`
- Reverse proxy: OpenLiteSpeed vhost for `nextstep.co.ke`

## Live Services

- `nextstep-backend.service`
- `nextstep-celery.service`
- `nextstep-celery-beat.service`

The backend should remain bound to localhost only. Public access should go through LiteSpeed.

## LiteSpeed Routing

The `nextstep.co.ke` vhost should:

- serve `/` from the frontend docroot
- proxy `/api/` to `127.0.0.1:8010`
- proxy `/r/` to `127.0.0.1:8010`
- proxy `/health` to `127.0.0.1:8010`
- proxy `/health/detailed` to `127.0.0.1:8010`

## Standard Deploy Procedure

1. Update the repo:
   - `cd /home/nextstep.co.ke/public_html`
   - `git pull origin main`
2. Ensure the runtime exists:
   - `bash scripts/setup_prod_environment.sh`
3. Load env for one-off commands:
   - `set -o allexport; source /home/nextstep.co.ke/.env; set +o allexport`
4. Run migrations carefully:
   - `cd /home/nextstep.co.ke/public_html/backend`
   - `/home/nextstep.co.ke/.venv/bin/alembic -c alembic.ini current`
   - If multiple heads exist, inspect before upgrading.
5. Restart app services:
   - `sudo systemctl restart nextstep-backend.service nextstep-celery.service nextstep-celery-beat.service`
6. Verify:
   - `curl http://127.0.0.1:8010/health`
   - `curl http://127.0.0.1:8010/api/search?limit=1`
   - `curl https://nextstep.co.ke/health`
   - `curl https://nextstep.co.ke/api/search?limit=1`

## Source of Truth Files

Repo-managed references:

- `scripts/bootstrap_prod.sh` (canonical production bootstrap)
- `scripts/setup_prod_environment.sh` (supporting helper for runtime setup)
- `deploy/systemd/`
- `scripts/legacy/deploy-to-cyberpanel.sh` (legacy reference)
- `scripts/legacy/deploy_upgrades.sh` (legacy reference)

Live server files:

- `/etc/systemd/system/nextstep-backend.service`
- `/etc/systemd/system/nextstep-celery.service`
- `/etc/systemd/system/nextstep-celery-beat.service`
- `/usr/local/lsws/conf/vhosts/nextstep.co.ke/vhost.conf`

Long term, the repo should generate or fully define the live server files above.

## Known Operational Issue

Alembic currently has a multi-head / duplicate-table mismatch in production history. Do not assume `alembic upgrade head` is safe without checking current revision state first.
