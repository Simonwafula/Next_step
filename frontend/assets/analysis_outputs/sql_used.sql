-- NextStep PostgreSQL inspection and coursework analysis
-- Source of truth: career_lmi PostgreSQL database
-- Safety: read-only queries plus reproducible cleaning query for CSV export

\pset pager off

-- 1. Schemas
SELECT schema_name
FROM information_schema.schemata
ORDER BY schema_name;

-- 2. User tables
SELECT schemaname, tablename, tableowner
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;

-- 3. Main jobs-related table definitions
SELECT
    table_schema,
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('job_post', 'organization', 'location', 'job_entities', 'job_skill', 'skill')
ORDER BY table_name, ordinal_position;

-- 4. Exact row counts for main tables
SELECT 'job_post' AS table_name, count(*) AS exact_rows FROM job_post
UNION ALL
SELECT 'organization', count(*) FROM organization
UNION ALL
SELECT 'location', count(*) FROM location
UNION ALL
SELECT 'job_entities', count(*) FROM job_entities
UNION ALL
SELECT 'job_skill', count(*) FROM job_skill
UNION ALL
SELECT 'skill', count(*) FROM skill
ORDER BY table_name;

-- 5. Null/blank profile for critical job fields
SELECT
    count(*) AS total_rows,
    count(*) FILTER (WHERE nullif(btrim(source), '') IS NULL) AS missing_source,
    count(*) FILTER (WHERE nullif(btrim(url), '') IS NULL) AS missing_url,
    count(*) FILTER (WHERE nullif(btrim(title_raw), '') IS NULL) AS missing_title_raw,
    count(*) FILTER (WHERE org_id IS NULL) AS missing_org_id,
    count(*) FILTER (WHERE location_id IS NULL) AS missing_location_id,
    count(*) FILTER (WHERE nullif(btrim(coalesce(description_clean, description_raw)), '') IS NULL) AS missing_description,
    count(*) FILTER (WHERE length(coalesce(description_clean, description_raw, '')) < 100) AS short_description_lt_100,
    count(*) FILTER (WHERE length(coalesce(description_clean, description_raw, '')) < 250) AS short_description_lt_250,
    count(*) FILTER (WHERE nullif(btrim(seniority), '') IS NULL) AS missing_seniority,
    count(*) FILTER (WHERE nullif(btrim(tenure), '') IS NULL) AS missing_tenure,
    count(*) FILTER (WHERE nullif(btrim(education), '') IS NULL) AS missing_education,
    count(*) FILTER (WHERE salary_min IS NULL AND salary_max IS NULL) AS missing_salary_range
FROM job_post;

-- 6. Duplicate profile
SELECT count(*) AS duplicated_urls
FROM (
    SELECT url
    FROM job_post
    WHERE nullif(btrim(url), '') IS NOT NULL
    GROUP BY url
    HAVING count(*) > 1
) t;

SELECT count(*) AS rows_in_duplicated_urls
FROM (
    SELECT url
    FROM job_post
    WHERE nullif(btrim(url), '') IS NOT NULL
    GROUP BY url
    HAVING count(*) > 1
) d
JOIN job_post jp USING (url);

SELECT count(*) AS duplicated_title_company_date_keys
FROM (
    SELECT
        lower(btrim(jp.title_raw)) AS title_key,
        lower(btrim(coalesce(o.name, ''))) AS company_key,
        jp.first_seen::date AS first_seen_date
    FROM job_post jp
    LEFT JOIN organization o ON o.id = jp.org_id
    WHERE nullif(btrim(jp.title_raw), '') IS NOT NULL
    GROUP BY 1, 2, 3
    HAVING count(*) > 1
) t;

SELECT count(*) AS rows_in_duplicated_title_company_date_keys
FROM (
    SELECT
        lower(btrim(jp.title_raw)) AS title_key,
        lower(btrim(coalesce(o.name, ''))) AS company_key,
        jp.first_seen::date AS first_seen_date
    FROM job_post jp
    LEFT JOIN organization o ON o.id = jp.org_id
    WHERE nullif(btrim(jp.title_raw), '') IS NOT NULL
    GROUP BY 1, 2, 3
    HAVING count(*) > 1
) d
JOIN (
    SELECT
        jp.id,
        lower(btrim(jp.title_raw)) AS title_key,
        lower(btrim(coalesce(o.name, ''))) AS company_key,
        jp.first_seen::date AS first_seen_date
    FROM job_post jp
    LEFT JOIN organization o ON o.id = jp.org_id
) jp
ON jp.title_key = d.title_key
AND jp.company_key = d.company_key
AND jp.first_seen_date = d.first_seen_date;

-- 7. Label consistency and coverage
SELECT source, count(*) AS rows
FROM job_post
GROUP BY source
ORDER BY rows DESC, source;

SELECT coalesce(seniority, '[NULL]') AS seniority, count(*) AS rows
FROM job_post
GROUP BY seniority
ORDER BY rows DESC, seniority;

SELECT coalesce(tenure, '[NULL]') AS tenure, count(*) AS rows
FROM job_post
GROUP BY tenure
ORDER BY rows DESC, tenure;

SELECT coalesce(education, '[NULL]') AS education, count(*) AS rows
FROM job_post
GROUP BY education
ORDER BY rows DESC, education;

SELECT coalesce(o.sector, '[NULL]') AS sector, count(*) AS rows
FROM job_post jp
LEFT JOIN organization o ON o.id = jp.org_id
GROUP BY o.sector
ORDER BY rows DESC, sector
LIMIT 25;

-- 8. Date profile
SELECT
    min(first_seen) AS min_first_seen,
    max(first_seen) AS max_first_seen,
    min(last_seen) AS min_last_seen,
    max(last_seen) AS max_last_seen,
    count(*) FILTER (WHERE last_seen < first_seen) AS invalid_last_seen_before_first_seen
FROM job_post;

-- 9. Richness of text and extracted labels
SELECT
    percentile_cont(0.25) WITHIN GROUP (ORDER BY length(coalesce(description_clean, description_raw, ''))) AS p25_desc_len,
    percentile_cont(0.50) WITHIN GROUP (ORDER BY length(coalesce(description_clean, description_raw, ''))) AS p50_desc_len,
    percentile_cont(0.75) WITHIN GROUP (ORDER BY length(coalesce(description_clean, description_raw, ''))) AS p75_desc_len,
    avg(length(coalesce(description_clean, description_raw, ''))) AS avg_desc_len,
    max(length(coalesce(description_clean, description_raw, ''))) AS max_desc_len
FROM job_post;

SELECT
    count(*) AS total_jobs,
    count(je.job_id) AS jobs_with_entities,
    count(*) FILTER (WHERE je.skills <> '[]'::jsonb) AS jobs_with_skills_json,
    count(*) FILTER (WHERE je.education <> '{}'::jsonb) AS jobs_with_education_json,
    count(*) FILTER (WHERE je.experience <> '{}'::jsonb) AS jobs_with_experience_json
FROM job_post jp
LEFT JOIN job_entities je ON je.job_id = jp.id;

-- 10. Exploratory counts for assignment narrative
SELECT title_raw, count(*) AS rows
FROM job_post
WHERE nullif(btrim(title_raw), '') IS NOT NULL
GROUP BY title_raw
ORDER BY rows DESC, title_raw
LIMIT 15;

SELECT coalesce(o.name, '[NULL]') AS company, count(*) AS rows
FROM job_post jp
LEFT JOIN organization o ON o.id = jp.org_id
GROUP BY o.name
ORDER BY rows DESC, company
LIMIT 15;

SELECT coalesce(l.raw, '[NULL]') AS location, count(*) AS rows
FROM job_post jp
LEFT JOIN location l ON l.id = jp.location_id
GROUP BY l.raw
ORDER BY rows DESC, location
LIMIT 15;

SELECT skill_name, count(*) AS rows
FROM (
    SELECT jsonb_array_elements(je.skills)->>'value' AS skill_name
    FROM job_entities je
    WHERE je.skills <> '[]'::jsonb
) s
WHERE nullif(btrim(skill_name), '') IS NOT NULL
GROUP BY skill_name
ORDER BY rows DESC, skill_name
LIMIT 20;

-- 11. Reproducible cleaned subset for coursework
WITH base AS (
    SELECT
        jp.id,
        jp.source,
        nullif(btrim(jp.url), '') AS url,
        nullif(regexp_replace(btrim(jp.title_raw), '\s+', ' ', 'g'), '') AS title,
        nullif(regexp_replace(btrim(coalesce(o.name, '')), '\s+', ' ', 'g'), '') AS company,
        nullif(regexp_replace(btrim(coalesce(l.raw, concat_ws(', ', l.city, l.region, l.country), '')), '\s+', ' ', 'g'), '') AS location,
        nullif(btrim(jp.tenure), '') AS employment_type,
        nullif(btrim(jp.seniority), '') AS experience_level,
        nullif(btrim(jp.education), '') AS education,
        jp.salary_min,
        jp.salary_max,
        nullif(btrim(jp.currency), '') AS currency,
        jp.first_seen::date AS posted_date,
        jp.last_seen::date AS closing_or_last_seen_date,
        coalesce(nullif(btrim(jp.description_clean), ''), nullif(btrim(jp.description_raw), '')) AS description,
        nullif(btrim(jp.requirements_raw), '') AS requirements,
        nullif(btrim(o.sector), '') AS sector,
        case when je.skills = '[]'::jsonb then NULL else je.skills end AS skills_json,
        row_number() OVER (
            PARTITION BY coalesce(nullif(btrim(jp.url), ''), '__missing_url__' || lower(btrim(jp.title_raw)) || '|' || coalesce(lower(btrim(o.name)), '') || '|' || jp.first_seen::date::text)
            ORDER BY jp.last_seen DESC, jp.id DESC
        ) AS rn
    FROM job_post jp
    LEFT JOIN organization o ON o.id = jp.org_id
    LEFT JOIN location l ON l.id = jp.location_id
    LEFT JOIN job_entities je ON je.job_id = jp.id
    WHERE jp.is_active IS TRUE
),
cleaned AS (
    SELECT *
    FROM base
    WHERE rn = 1
      AND title IS NOT NULL
      AND description IS NOT NULL
      AND length(description) >= 250
      AND company IS NOT NULL
      AND posted_date IS NOT NULL
)
SELECT *
FROM cleaned
ORDER BY posted_date DESC, id DESC
LIMIT 500;
