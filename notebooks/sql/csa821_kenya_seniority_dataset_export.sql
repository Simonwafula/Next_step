WITH skill_counts AS (
    SELECT
        job_post_id,
        COUNT(*) AS skill_count
    FROM job_skill
    GROUP BY job_post_id
)
SELECT
    jp.id,
    jp.source,
    jp.title_raw,
    COALESCE(tn.canonical_title, 'UNKNOWN') AS canonical_title,
    jp.seniority,
    jp.description_clean,
    COALESCE(org.sector, 'UNKNOWN') AS sector,
    COALESCE(loc.country, 'UNKNOWN') AS country,
    COALESCE(loc.city, 'UNKNOWN') AS city,
    COALESCE(loc.region, 'UNKNOWN') AS region,
    COALESCE(jp.education, 'UNKNOWN') AS education,
    COALESCE(sc.skill_count, 0) AS skill_count,
    COALESCE(jp.quality_score, 0.0) AS quality_score,
    COALESCE(jp.repost_count, 0) AS repost_count
FROM job_post jp
JOIN location loc
    ON jp.location_id = loc.id
LEFT JOIN title_norm tn
    ON jp.title_norm_id = tn.id
LEFT JOIN organization org
    ON jp.org_id = org.id
LEFT JOIN skill_counts sc
    ON jp.id = sc.job_post_id
WHERE loc.country = 'Kenya'
  AND jp.is_active = TRUE
  AND jp.description_clean IS NOT NULL
  AND jp.seniority IS NOT NULL
  AND jp.title_norm_id IS NOT NULL
ORDER BY jp.id;
