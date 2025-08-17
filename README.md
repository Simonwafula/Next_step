# Career Translator + Labour Market Intelligence (LMI)

A starter scaffold for a system that:
- Ingests jobs from reputable boards/ATS (e.g., Greenhouse/Lever/RSS).
- Cleans/normalizes titles & skills, deduplicates, embeds text for similarity search.
- Stores everything in Postgres (+ pgvector).
- Exposes APIs (FastAPI) for search, recommendations, stats, and a WhatsApp webhook.
- Generates Labour Market Intelligence (LMI) weekly via dbt.
- Spins up Metabase for dashboards.

> This is a scaffold intended to run with Docker. Components are minimal and ready to extend.

## Services
- **backend**: FastAPI app (search, recommend, stats, WhatsApp webhook, ingestion jobs).
- **postgres**: Postgres 16 with pgvector extension.
- **metabase**: Metabase UI (http://localhost:3000) — connect to Postgres manually on first run.

## Quick start
1. Copy `.env.example` to `.env` and adjust values.
2. `docker compose up --build` (first run will build backend image).
3. Visit FastAPI docs: http://localhost:8000/docs
4. Visit Metabase: http://localhost:3000 (create admin, add Postgres using env values).

## Data model (simplified)
See `backend/app/models/` for SQLAlchemy models. Key tables:
- `job_post`, `organization`, `location`, `title_norm`, `skill`, `job_skill`

## Ingestion
Connectors live in `backend/app/ingestion/connectors`. Start with:
- `greenhouse.py`
- `lever.py`
- `rss.py` (generic RSS/Atom feeds)
- `html_generic.py` (placeholder for polite scraping if allowed)

Configure sources in `backend/app/ingestion/sources.yaml`. Run ingestion via `/admin/ingest` endpoint or background scheduler.

## Normalization
- Titles mapped to canonical families in `normalization/titles.py`
- Skills extracted via simple patterns in `normalization/skills.py` (stub — extend with NLP later).

## Recommender
- Embeddings stub in `ml/embeddings.py` (deterministic hashing → vectors; swap with a real model later).
- Cosine similarity for title/skills vectors in `services/recommend.py`.

## WhatsApp mini-advisor
- Webhook at `/whatsapp/webhook` (Twilio-compatible). Add your credentials to `.env`.
- Minimal intents: search by degree/skills, basic transition suggestion, set alert (stub).

## dbt & LMI
- `dbt/` holds a tiny dbt project with weekly metrics examples.
- After ingestion, run dbt models to compute aggregates for Metabase.

## Notes
- This scaffold avoids heavy NLP deps by default. Replace `ml/embeddings.py` with your provider (OpenAI, HuggingFace, etc).
- Respect robots.txt and TOS for any scraping; prefer official ATS APIs/RSS feeds.
- Ensure compliance with data protection laws for user data and messaging consent.

## Commands
- `docker compose up --build`
- `docker compose logs -f backend`
- Run dbt from a container or your host: see `dbt/README.md`.
