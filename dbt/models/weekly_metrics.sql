-- Toy weekly aggregate for LMI dashboard
with base as (
  select
    date_trunc('week', first_seen) as week,
    title_raw,
    tenure,
    salary_min,
    salary_max
  from job_post
)
select
  week,
  count(*) as postings,
  percentile_cont(0.5) within group (order by salary_min) as salary_p50_min
from base
group by 1
order by 1 desc
