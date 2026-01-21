# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI service, SQLAlchemy models, ingestion jobs, API endpoints.
- `backend/app/`: core application modules (models, services, ingestion, normalization, ML stubs).
- `backend/app/ingestion/government_sources.yaml`: source list for national + county + assembly career pages.
- `backend/app/ingestion/connectors/gov_careers.py`: government career page HTML ingest logic.
- `backend/app/tasks/gov_monitor_tasks.py`: Celery worker that monitors government sources.
- `scripts/generate_government_sources.py`: regenerate the government source list from the seed spreadsheet.
- `backend/test_*.py`: pytest suites for workflow and processors.
- `frontend/`: static UI (`index.html`, `styles/`, `js/`).
- `dbt/`: dbt project for LMI aggregates.
- `docker-compose.yml` and `docker-compose.prod.yml`: local and prod orchestration.

## Build, Test, and Development Commands
- `docker compose up --build`: build and start the full stack (API, Postgres, Metabase).
- `docker compose logs -f backend`: tail backend logs while developing.
- `DATABASE_URL=sqlite:///./var/nextstep.sqlite pytest backend/test_automated_workflow.py -q`: fast local test run against SQLite.
- `dbt debug`, `dbt run`, `dbt test` from `dbt/`: validate and build analytics models (requires `~/.dbt/profiles.yml`).

## Coding Style & Naming Conventions
- Python: follow PEP8, 4-space indentation, `snake_case` for functions/modules, `PascalCase` for classes.
- Frontend: 4-space indentation in HTML/CSS/JS, `kebab-case` for CSS classes, `camelCase` for JS methods.
- No repo-wide formatter is enforced; keep style consistent with adjacent files.

## Testing Guidelines
- Use `pytest` with `backend/test_*.py` naming; add tests for new endpoints, data transforms, or ingestion logic.
- Prefer SQLite for fast unit tests; run the full Docker stack when changes depend on Postgres/pgvector.
- If you change dbt models, run `dbt test` to catch schema or logic regressions.

## Government Jobs Monitoring (Immediate Priority)
- Keep national, parastatal, county government, and county assembly sources updated in `backend/app/ingestion/government_sources.yaml`.
- When adding new sources, supply career/vacancies URLs (or PDFs) and keep notes/status current.
- The monitor uses keyword-based link detection; add source-specific keywords in the YAML if a site uses unusual labels.
- Regenerate the source list with `python scripts/generate_government_sources.py <xlsx>`.
- Manual trigger: `POST /admin/ingest/government`.

## Commit & Pull Request Guidelines
- Commit messages follow a Conventional Commits pattern such as `feat:`, `fix:`, or `chore:`.
- Use `PR_DESCRIPTION.md` as the PR template; include a concise summary, test commands run, and note any config or schema changes.
- Add UI screenshots or short clips when modifying `frontend/`.

## Security & Configuration Tips
- Copy `.env.example` to `.env` and keep secrets out of version control.
- Respect robots.txt and source TOS for ingestion; prefer official APIs and RSS feeds.

## Quality
This codebase will outlive you. Every shortcut you take becomes
someone else's burden. Every hack compounds into technical debt
that slows the whole team down.

You are not just writing code. You are shaping the future of this
project. The patterns you establish will be copied. The corners
you cut will be cut again.

Fight entropy. Leave the codebase better than you found it.