-- Example passthrough (adjust to your schema)
select
  id,
  date_trunc('day', first_seen) as date,
  title_raw,
  tenure,
  salary_min,
  salary_max,
  currency
from job_post
