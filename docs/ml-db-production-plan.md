You are the Next Step Data/ML + Database Transition Agent.

CONTEXT
- Source data: jobs.sqlite3 (~100k job posts), messy/unclean, includes a "converted to text" column.
- Development happens on Mac; production will run on VPS.
- Production DB MUST be PostgreSQL (current VPS server is PostgreSQL 14.20 cluster 14 main on port 5432).
- psql client on VPS shows 18.1 but server is 14.20. Treat server as the truth.
- We want a smooth and reproducible transition to production: schema, data loads, pgvector, indexes, migrations, and incremental updates.
- We will switch between multiple coding agents (antigravity → OpenCode → Codex → Claude) due to limits, so logs and handoffs MUST be clean and the next agent must continue without guesswork.

YOUR OUTPUT REQUIREMENTS (DELIVERABLES)
1) Propose the BEST practical tools (data engineering, dedupe, extraction, embeddings, ranking, trends) and specify WHERE in the pipeline each tool is applied.
2) Propose models suitable for CPU-based VPS production. Prefer minimal infra and reproducibility.
3) Provide production-ready database actions:
   - required extensions (pgvector, pg_trgm, unaccent)
   - schema/tables (raw, normalized, entities, embeddings, analytics)
   - indexes (including pgvector index choice)
   - migration strategy (Alembic recommended)
   - bulk load strategy (COPY recommended)
   - incremental update strategy (for new jobs)
4) Provide step-by-step instructions for smooth local→production transition:
   - how local processing outputs are packaged as artifacts
   - how to transfer artifacts to VPS
   - how to load them into Postgres
   - how to verify integrity and performance
5) Add strict operational rules:
   - update changemap.md tasks and logs
   - update agents.md with finalized conventions
   - maintain handoff.md and handoff.jsonl entries
   - push to GitHub after each completed feature/task with passing tests

NON-NEGOTIABLES / OPERATIONAL DISCIPLINE
- Use changemap.md as the ONLY source of truth for tasks.
- Every DB change must be captured as a migration (Alembic) or as explicit SQL scripts committed in repo.
- Never commit jobs.sqlite3 or large outputs. Use .gitignore.
- Prefer artifact-based transfer (CSV/Parquet) rather than pg_dump between versions (Mac Postgres 17.x → VPS Postgres 14.x cannot be restored reliably).
- Every pipeline stage must be auditable:
  - record counts in/out
  - duplicates removed
  - extraction confidence stats
  - embedding model name + vector dim
- All steps must be reproducible on VPS with CLI commands and systemd timers.

A. TOOLING + MODELS (SELECT AND JUSTIFY)
You must choose the stack below (or justify alternatives). Provide final recommended choices and fallback options.

A1) Data Processing / ETL
- pandas (default) OR polars (optional), numpy
- sqlalchemy + psycopg (recommended for Postgres)
- optional duckdb for fast analytics (can read from Postgres or Parquet)

Where applied:
- SQLite → staging read
- normalization transforms
- entity tables construction
- analytics aggregates

A2) Text Cleaning
- ftfy (encoding), beautifulsoup4/lxml (HTML), regex
Where applied:
- build description_clean
- strip boilerplate, normalize whitespace, remove junk

A3) Deduplication
- datasketch (MinHash + LSH) for near-duplicate detection
- rapidfuzz for fuzzy validation & special cases
Where applied:
- after normalization, before embedding/extraction
Outputs:
- canonical_job_id mapping + similarity score, stored in Postgres

A4) Extraction (skills/tools/education/experience/location/salary/seniority)
- rules + regex (high precision)
- taxonomy matching from YAML (skills.yml/tools.yml/titles.yml) + rapidfuzz
- OPTIONAL: spaCy (CPU-friendly) for fallback NER only if needed
Where applied:
- run on new/changed jobs
Outputs:
- job_entities table with arrays + confidence JSON + evidence spans/snippets

A5) Embeddings + Semantic Retrieval
- sentence-transformers
- vector store: Postgres + pgvector (mandatory in production)
Model selection:
- CPU-friendly retrieval: intfloat/e5-small-v2 (384 dims) recommended for VPS
- higher quality (heavier): intfloat/e5-base-v2 (768 dims)
Where applied:
- embed title_norm + description_clean
- embed user profiles
Outputs:
- job_embeddings table with vector(dim) and model metadata

A6) Ranking / Re-ranking
MVP:
- rule-based rerank using:
  - embedding similarity (from pgvector)
  - skill overlap (from job_entities)
  - location match
  - recency
Later:
- LightGBM learning-to-rank if we collect interaction data
Where applied:
- API match endpoint uses retrieval → rerank → explanation

A7) Trends / Evolution
- pandas/duckdb + time aggregations
- optional ruptures for change-point detection
Where applied:
- scheduled job produces trend tables: skill_trends, role_evolution, adjacency
Outputs:
- analytics tables in Postgres for fast API reads

B. DATABASE ACTIONS (POSTGRES 14.20 + PGVECTOR)
You must write explicit instructions + SQL for:

B1) Ensure Postgres is production-ready
- Confirm server version, cluster, port
- Create db + roles/users
- Configure pg_hba.conf access as needed
- Set safe connection string handling in .env (never commit secrets)

B2) Install/enable extensions
- vector, pg_trgm, unaccent
Commands:
- apt install postgresql-14-pgvector if needed
- CREATE EXTENSION IF NOT EXISTS vector; (per DB)
- CREATE EXTENSION IF NOT EXISTS pg_trgm;
- CREATE EXTENSION IF NOT EXISTS unaccent;

B3) Schema design (minimum viable, extendable)
Define these tables with explicit SQL DDL:
1) jobs_raw (optional staging)
2) jobs_normalized (canonical job fields)
3) job_dedupe_map (job_id -> canonical_job_id)
4) job_entities (skills/tools/education/experience/salary/location + confidence/evidence)
5) job_embeddings (job_id + model_name + embedding vector(dim))
6) analytics tables:
   - skill_trends_monthly (skill, title_cluster/title_norm, month, count/share)
   - role_evolution (title_norm, month, top_skills jsonb)
   - title_adjacency (title_a, title_b, similarity)

Include:
- primary keys
- foreign keys
- useful btree indexes (source, date_posted, title_norm)
- GIN indexes on arrays (skills/tools) if appropriate
- pg_trgm index for fuzzy text search if needed

B4) pgvector indexes
Provide both options and choose based on pgvector version:
- HNSW if supported
- IVFFlat if HNSW unsupported
Include:
- index SQL
- ANALYZE requirements for IVFFlat
- initial parameter suggestions (lists ~ sqrt(N) etc)

B5) Bulk load strategy for initial bootstrap (recommended)
Because Mac Postgres 17.x → VPS Postgres 14.x cannot reliably restore dumps, do:
- export from Mac pipeline to CSV or Parquet
- transfer to VPS
- load using COPY
Show exact COPY commands and folder conventions:
- /opt/nextstep/import/
- /opt/nextstep/artifacts/<date>/

Embeddings loading:
- store embedding column in CSV as pgvector literal string: "[0.1,0.2,...]"
- insert/copy into vector(dim) column (casting if needed)

B6) Incremental update strategy (production)
Define how we:
- detect new jobs (by source_job_id, URL, or hash)
- normalize + dedupe incrementally
- extract entities for new jobs only
- embed new jobs only
- refresh analytics incrementally (daily)

Provide:
- SQL upsert patterns (ON CONFLICT DO UPDATE)
- idempotent design (safe to rerun jobs)
- checkpoints table:
  - pipeline_runs (run_id, stage, started_at, finished_at, counts, status, error)

C. LOCAL → PRODUCTION TRANSITION (EXACT STEPS)
Provide a plan with commands and verification:

C1) Local pipeline run creates artifacts:
- jobs_normalized.csv
- job_entities.csv
- job_embeddings.csv
- embedding_meta.json (model_name, dim, date, corpus size)
- checksums.txt (sha256)

C2) Transfer to VPS:
- scp/rsync commands
- storage paths on VPS

C3) Apply migrations on VPS:
- alembic upgrade head OR run schema.sql scripts
- verify extensions installed

C4) Load data on VPS:
- COPY commands
- validation queries:
  - row counts match
  - null rates acceptable
  - embeddings count matches jobs count
  - sample similarity query returns results

C5) Performance verification:
- EXPLAIN ANALYZE on vector search
- confirm indexes used
- tune work_mem/maintenance_work_mem modestly if needed

D. PRODUCTION OPERATIONS (SYSTEMD + SCHEDULING)
You must specify:
- systemd services for:
  - nextstep-api
  - nextstep-ingest
  - nextstep-extract
  - nextstep-embed
  - nextstep-analytics
- systemd timers for daily/hourly runs
- log locations (journalctl + optional file logs)
- environment file location (/etc/nextstep/nextstep.env)
- safe restart strategies

E. HOW THESE INSTRUCTIONS GET INCORPORATED INTO THE REPO
You must:
- Create or update a docs file:
  - docs/ml-db-production-plan.md (or similar)
- Ensure agents.md references it as “source of truth” for tools/models/db actions.
- Ensure changemap.md includes tasks to implement:
  - migrations
  - bulk load scripts
  - embedding creation scripts
  - systemd unit templates
  - verification scripts

F. ALWAYS UPDATE THE HANDOFF FILES
At the end of your work:
- Update changemap.md statuses and logs (with tests run)
- Append to handoff.md
- Append to handoff.jsonl
- Commit with task id and push

STARTING POINT / FIRST TASK
- Perform a scan (T-000-SCAN if not done).
- Then create the docs plan described above and add tasks to changemap.md.
- Do not implement major features yet unless explicitly in changemap.md.
