# dbt for LMI

This is a tiny dbt project to generate simple aggregates (weekly postings, top skills).

## Setup
- Install dbt for Postgres on your machine (or use a container).
- Copy `profiles.example.yml` to `~/.dbt/profiles.yml` and adjust credentials to match your `.env`.
- Run:
  - `dbt debug`
  - `dbt run`
  - `dbt test`

## Models
- `models/postings_daily.sql`: fact table copied from raw job posts (example).
- `models/weekly_metrics.sql`: weekly aggregates for Metabase.
