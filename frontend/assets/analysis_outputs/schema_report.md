# NextStep PostgreSQL Schema Inspection

## Scope
- Database inspected: `career_lmi`
- Access mode: direct PostgreSQL inspection with `sudo -u postgres psql`
- Schemas found: `public`, `pg_catalog`, `information_schema`, `pg_toast`
- Relevant application data is in `public`

## Relevant tables for extracted job-post data

### `public.job_post`
- Purpose: main extracted job-post table; one row per ingested posting/version
- Exact rows: `110,781`
- Key columns:
  - `id integer not null`: primary identifier
  - `source varchar not null`: source site/domain
  - `url text not null`: canonical job URL
  - `url_hash varchar`: optional hashed URL
  - `first_seen timestamp not null`: first time the job was seen in the system
  - `last_seen timestamp not null`: last time the job was seen in the system
  - `repost_count integer not null`: repost tracking
  - `org_id integer`: foreign key to `organization`
  - `title_raw varchar not null`: raw extracted title
  - `title_norm_id integer`: normalized title link
  - `location_id integer`: foreign key to `location`
  - `tenure varchar`: employment type style field
  - `salary_min double precision`
  - `salary_max double precision`
  - `currency varchar`
  - `seniority varchar`: strong candidate label
  - `description_raw text`
  - `requirements_raw text`
  - `education varchar`: extracted education requirement
  - `attachment_flag boolean not null`
  - `quality_score double precision`
  - `processed_at timestamp`
  - `embedding text`
  - `description_clean text`
  - `source_url text`
  - `application_url text`
  - `is_active boolean not null`

### `public.organization`
- Purpose: employer / organization dimension table
- Exact rows: `2,817`
- Key columns:
  - `id integer not null`
  - `name varchar not null`
  - `sector varchar`
  - `ats varchar`
  - `verified boolean not null`

### `public.location`
- Purpose: normalized location dimension
- Exact rows: `787`
- Key columns:
  - `id integer not null`
  - `country varchar`
  - `region varchar`
  - `city varchar`
  - `raw varchar`

### `public.job_entities`
- Purpose: extracted structured entities linked to jobs
- Exact rows: `109,392`
- Key columns:
  - `id integer not null`
  - `job_id integer not null`
  - `entities jsonb not null`
  - `skills jsonb not null`
  - `tools jsonb not null`
  - `education jsonb not null`
  - `experience jsonb not null`

### `public.skill`
- Purpose: skill dictionary / taxonomy table
- Exact rows: `41,254`
- Key columns:
  - `id integer not null`
  - `name varchar not null`
  - `taxonomy_ref varchar`
  - `aliases jsonb not null`

### `public.job_skill`
- Purpose: many-to-many bridge from jobs to normalized skills
- Exact rows: `895,494`
- Key columns:
  - `id integer not null`
  - `job_post_id integer not null`
  - `skill_id integer not null`
  - `confidence double precision not null`

## Inferred data model
- `job_post` is the source of truth for assignment work.
- `organization` and `location` enrich jobs with company and place information.
- `job_entities` stores extracted JSON labels useful for text mining and feature engineering.
- `job_skill` and `skill` can support skill-frequency analysis, but they are secondary to the raw job text.

## Coursework mapping
- Ideal coursework fields present directly or by safe mapping:
  - `id` -> `job_post.id`
  - `source` -> `job_post.source`
  - `url` -> `job_post.url`
  - `title` -> `job_post.title_raw`
  - `company` -> `organization.name` via `job_post.org_id`
  - `location` -> `location.raw` via `job_post.location_id`
  - `description` -> `coalesce(job_post.description_clean, job_post.description_raw)`
  - `requirements` -> `job_post.requirements_raw`
  - `education` -> `job_post.education`
  - `employment_type` -> `job_post.tenure`
  - `experience_level` -> `job_post.seniority`
  - `salary` -> `salary_min`, `salary_max`, `currency`
  - `posted_date` -> `job_post.first_seen::date`
  - `closing_date` proxy -> `job_post.last_seen::date`
- Weak or absent coursework fields:
  - `category`: no robust category column in `job_post`
  - `sector`: available only through `organization.sector`, but very sparse

## Summary
- Best table for coursework: `public.job_post`
- Best supporting tables: `public.organization`, `public.location`, `public.job_entities`
- Most usable label for supervised learning: `job_post.seniority`
