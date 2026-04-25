# NextStep Job Data Quality Report

## Verdict
**Suitable with light cleaning**

The PostgreSQL data is usable for a student data mining assignment because the main job table is large, direct URL duplicates are absent, text fields are generally rich, and `seniority` is a strong target label. Light cleaning is still required because company names, locations, employment type, education labels, and extracted skills contain visible noise.

## Evidence From PostgreSQL

### Table size and coverage
- `job_post`: `110,781` rows
- `job_entities`: `109,392` rows
- `organization`: `2,817` rows
- `location`: `787` rows
- `job_skill`: `895,494` rows
- `skill`: `41,254` rows

### Missingness in critical `job_post` fields
- `source`: `0` missing
- `url`: `0` missing
- `title_raw`: `0` missing
- `org_id`: `31,822` missing
- `location_id`: `31,087` missing
- `description`: `1,585` missing
- `seniority`: `1,391` missing
- `tenure`: `33,112` missing
- `education`: `5,001` missing
- salary range: `109,809` missing both min and max

Interpretation:
- Core text and ID fields are strong.
- Company and location enrichment are incomplete but still usable after filtering.
- Salary is too sparse to be central to the assignment.

### Duplicate checks
- Duplicate URLs: `0`
- Rows in duplicate URLs: `0`
- Duplicate `(title, company, first_seen_date)` keys: `9,320`
- Rows participating in those duplicate composite keys: `29,880`

Interpretation:
- URL-level deduplication is already strong.
- Near-duplicate title/company/date combinations still exist, so a lightweight dedupe rule is sensible.

### Date quality
- `first_seen` range: `2024-02-25` to `2026-03-23`
- `last_seen` range: `2026-01-25` to `2026-03-23`
- `last_seen < first_seen`: `0`

Interpretation:
- Dates are stored as proper timestamps and are internally consistent.

### Text richness
- Description length profile from a 5% PostgreSQL sample (`6,048` rows):
  - 25th percentile: `2,659.75`
  - median: `3,963.5`
  - 75th percentile: `6,505.25`
  - mean: `5,686.32`
  - max: `86,298`
  - descriptions under 100 chars: `151`
  - descriptions under 250 chars: `164`

Interpretation:
- The job descriptions are rich enough for text mining.
- Very short descriptions are a minority and can be filtered safely.

### Extracted-entity coverage
- Jobs with `job_entities` row: `109,392 / 110,781`
- Jobs with non-empty `skills` JSON: `107,452`
- Jobs with non-empty `education` JSON: `104,908`
- Jobs with non-empty `experience` JSON: `88,909`

Interpretation:
- Structured extraction coverage is high.
- JSON skill values are usable as supporting features, but not perfectly clean.

### Candidate label quality
- `seniority`
  - `Mid-Level`: `40,075`
  - `Senior`: `37,380`
  - `Entry`: `18,766`
  - `Executive`: `13,169`
  - missing: `1,391`
- `tenure`
  - `Full-time`: `74,997`
  - missing: `33,112`
  - `Contract`: `1,798`
  - `Internship`: `605`
  - `Part-time`: `269`
- `education`
  - `Bachelor`: `61,007`
  - `Master`: `34,971`
  - missing: `5,001`
  - `PhD`: `3,655`
  - `Diploma`: `3,475`
  - `"Master's Degree"`: `1,287`
  - `Certificate`: `986`
  - `High School`: `399`
- `sector` via `organization`
  - missing: `108,072`
  - `Government`: `2,572`
  - others are tiny

Interpretation:
- `seniority` is the most reliable label for classification.
- `tenure` is too sparse and imbalanced.
- `education` is usable but has minor label inconsistency.
- `sector` is too sparse to be a good target.

### Exploratory signals
- Most frequent raw titles include obvious noise such as `Facebook`, `Jobs at ...`, and `Vacancies at ...`
- Most frequent company values include obvious scrape artifacts such as `Read more about this company`
- Most frequent extracted skills include useful values (`communication`, `excel`, `finance`) but also noisy ones (`r`)

Interpretation:
- Raw text should be lightly cleaned before modelling.
- Company and skill features should be treated cautiously.

## Cleaning Actions Taken

### Reproducible rules
- Use `job_post` as source of truth.
- Join `organization`, `location`, and `job_entities` only for enrichment.
- Keep only `is_active = true`.
- Trim whitespace and collapse repeated spaces.
- Convert blank strings to `NULL`.
- Deduplicate by URL where present.
- If URL is missing, deduplicate by `(title, company, posted_date)` surrogate key.
- Filter out rows missing:
  - title
  - company
  - description
  - posted date
- Filter out descriptions shorter than `250` characters.
- Do not invent values or overwrite source tables.

### Result
- Cleaned eligible rows after light cleaning: `76,690`
- Missing values inside cleaned eligible set:
  - `experience_level`: `0`
  - `employment_type`: `663`
  - `education`: `464`
  - `location`: `356`
  - `skills_json`: `15`
- Exported coursework sample: `500` rows to `analysis_outputs/cleaned_sample.csv`

## Assignment Recommendation
- Preferred task: `classification`
- Recommended target: `experience_level` / `seniority`
- Recommended algorithm: `Logistic Regression` on TF-IDF features built from `title + description`

## Why Classification Fits Better Than Clustering
- A strong, mostly complete four-class label already exists.
- The classes are not perfectly balanced but are reasonable for coursework.
- Clustering is possible, but it would be harder to evaluate clearly because category and sector labels are weak.

## Risks / Limitations
- Company names still include scrape artifacts.
- Location still has nulls and broad labels such as `Global` and `International`.
- Skill extraction contains noisy tokens.
- Salary fields are too sparse for meaningful modelling.
- The exported 500-row sample is good for coursework demonstration, but a larger cleaned subset would be better for training a serious model.
