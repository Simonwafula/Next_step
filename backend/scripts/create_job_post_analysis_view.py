"""Create a non-destructive Postgres analysis schema and materialized view."""

from __future__ import annotations

from sqlalchemy import create_engine, text

from app.core.config import settings


SQL = """
CREATE SCHEMA IF NOT EXISTS analysis;

DROP MATERIALIZED VIEW IF EXISTS analysis.job_post_cleaned_mv;

CREATE MATERIALIZED VIEW analysis.job_post_cleaned_mv AS
WITH base AS (
    SELECT
        jp.id AS job_id,
        jp.source,
        jdm.canonical_job_id AS dedupe_cluster_id,
        NULLIF(BTRIM(jp.url), '') AS url,
        NULLIF(REGEXP_REPLACE(BTRIM(jp.title_raw), '\\s+', ' ', 'g'), '') AS title_raw_clean,
        NULLIF(REGEXP_REPLACE(BTRIM(COALESCE(o.name, '')), '\\s+', ' ', 'g'), '') AS company_raw_clean,
        NULLIF(REGEXP_REPLACE(BTRIM(COALESCE(l.raw, CONCAT_WS(', ', l.city, l.region, l.country), '')), '\\s+', ' ', 'g'), '') AS location_raw_clean,
        jp.first_seen,
        jp.last_seen,
        jp.first_seen::date AS posted_date,
        jp.last_seen::date AS last_seen_date,
        COALESCE(NULLIF(BTRIM(jp.description_clean), ''), NULLIF(BTRIM(jp.description_raw), '')) AS description_text,
        NULLIF(BTRIM(jp.requirements_raw), '') AS requirements_text,
        NULLIF(BTRIM(jp.tenure), '') AS employment_type,
        NULLIF(BTRIM(jp.seniority), '') AS experience_level,
        NULLIF(BTRIM(jp.education), '') AS education_level,
        jp.salary_min,
        jp.salary_max,
        NULLIF(BTRIM(jp.currency), '') AS currency,
        l.city,
        l.region,
        l.country,
        o.sector,
        jp.is_active,
        CASE
            WHEN LOWER(COALESCE(jp.source, '')) LIKE 'telegram:%' THEN 0.58
            WHEN LOWER(COALESCE(jp.source, '')) IN ('greenhouse', 'lever') THEN 0.97
            WHEN LOWER(COALESCE(jp.source, '')) = 'rss' THEN 0.84
            WHEN LOWER(COALESCE(jp.source, '')) = 'gov_careers' THEN 0.78
            WHEN LOWER(COALESCE(jp.source, '')) = 'html_generic' THEN 0.62
            WHEN LOWER(COALESCE(jp.source, '')) = 'tender_rss' THEN 0.72
            WHEN COALESCE(jp.source, '') LIKE '%.%' THEN 0.62
            ELSE 0.65
        END AS source_quality_score,
        ROW_NUMBER() OVER (
            PARTITION BY COALESCE(
                NULLIF(BTRIM(jp.url), ''),
                LOWER(BTRIM(jp.title_raw)) || '|' || LOWER(BTRIM(COALESCE(o.name, ''))) || '|' || jp.first_seen::date::text
            )
            ORDER BY jp.last_seen DESC, jp.id DESC
        ) AS dedupe_rank
    FROM job_post jp
    LEFT JOIN organization o ON o.id = jp.org_id
    LEFT JOIN location l ON l.id = jp.location_id
    LEFT JOIN job_dedupe_map jdm ON jdm.job_id = jp.id
)
SELECT
    job_id,
    source,
    source_quality_score,
    CASE
        WHEN source_quality_score >= 0.85 THEN 'high'
        WHEN source_quality_score >= 0.70 THEN 'medium'
        ELSE 'low'
    END AS source_quality_tier,
    url,
    title_raw_clean,
    company_raw_clean,
    location_raw_clean,
    posted_date,
    last_seen_date,
    first_seen,
    last_seen,
    description_text,
    requirements_text,
    employment_type,
    experience_level,
    education_level,
    salary_min,
    salary_max,
    currency,
    city,
    region,
    country,
    sector,
    is_active,
    dedupe_rank,
    dedupe_cluster_id,
    (description_text IS NOT NULL AND LENGTH(description_text) >= 250) AS has_rich_description,
    (company_raw_clean IS NOT NULL) AS has_company,
    (location_raw_clean IS NOT NULL) AS has_location,
    (
        title_raw_clean ~* '^(jobs?|vacancies|careers?|job opportunities|current opportunities|positions?|openings?) at '
        OR title_raw_clean IN ('jobs', 'vacancies', 'careers', 'job opportunities', 'current opportunities', 'open positions')
    ) AS listing_page_flag,
    (
        COALESCE(company_raw_clean, '') = ''
        OR company_raw_clean ~* '^(jobs?|vacancies|careers?) at '
        OR company_raw_clean ~* '^read more about this company$'
    ) AS company_noise_flag,
    CASE
        WHEN city IS NOT NULL AND region IS NOT NULL AND country IS NOT NULL THEN 'high'
        WHEN LOWER(COALESCE(location_raw_clean, '')) IN ('global', 'international', 'multiple locations', 'various locations', 'nationwide') THEN 'low'
        WHEN LOWER(COALESCE(location_raw_clean, '')) LIKE '%remote%' THEN 'medium'
        WHEN location_raw_clean IS NOT NULL THEN 'medium'
        ELSE 'low'
    END AS location_confidence
FROM base;

CREATE INDEX IF NOT EXISTS idx_job_post_cleaned_mv_posted_date
ON analysis.job_post_cleaned_mv (posted_date DESC);

CREATE INDEX IF NOT EXISTS idx_job_post_cleaned_mv_experience_level
ON analysis.job_post_cleaned_mv (experience_level);

CREATE INDEX IF NOT EXISTS idx_job_post_cleaned_mv_source
ON analysis.job_post_cleaned_mv (source);
"""


def create_job_post_analysis_view() -> None:
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text(SQL))


def main() -> None:
    create_job_post_analysis_view()
    print("Created analysis.job_post_cleaned_mv")


if __name__ == "__main__":
    main()
