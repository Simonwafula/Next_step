# Seniority Baseline

Date frozen: `2026-04-18`
Task: `T-1A12 Action 0`

## Purpose

This document freezes the current reproducible baseline for seniority classification before any production-oriented model or schema changes are made.

## Baseline Assets

- Notebook: `notebooks/csa821_assignment_1_nextstep_kenya_seniority_classification.ipynb`
- CSV snapshot: `notebooks/data/csa821_kenya_seniority_dataset.csv`
- Export SQL: `notebooks/sql/csa821_kenya_seniority_dataset_export.sql`

## Dataset Snapshot

- Source: Next Step PostgreSQL export restricted to Kenyan active jobs with non-null cleaned description, seniority, and normalized title
- Snapshot rows: `38,335`
- Snapshot columns: `14`
- Snapshot size: `186,728,580` bytes (`~179 MB`)

Columns:
- `id`
- `source`
- `title_raw`
- `canonical_title`
- `seniority`
- `description_clean`
- `sector`
- `country`
- `city`
- `region`
- `education`
- `skill_count`
- `quality_score`
- `repost_count`

## Class Distribution

- `Mid-Level`: `15,106`
- `Senior`: `13,063`
- `Entry`: `5,779`
- `Executive`: `4,387`

## Top Sources

- `migration`: `37,529`
- `gov_careers`: `768`
- `brightermonday.co.ke`: `38`

## Top Canonical Titles

- `sales representative`: `1,184`
- `accountant`: `777`
- `software developer`: `530`
- `project manager`: `340`
- `program officer`: `235`

## Baseline Sample Metrics

CSV-only smoke evaluation on a stratified `3,000`-row sample:

- `Linear SVM` weighted F1: `0.6464`
- `Logistic Regression` weighted F1: `0.5537`

Earlier PostgreSQL-backed smoke evaluation on a `3,000`-row sample with the same pipeline family:

- `Linear SVM` weighted F1: `0.6529`
- `Logistic Regression` weighted F1: `0.6466`

## Interpretation

- The baseline has enough predictive signal to support internal ranking experiments.
- The current quality is not strong enough to justify unconditional hard filtering for users.
- The next improvement priority should be label quality, explicit seniority rules, and stronger extracted features rather than immediate UI exposure.

## Handling Notes

- Keep secrets out of all baseline artifacts and logs.
- Do not commit credentials or raw environment values.
- The full `csa821_kenya_seniority_dataset.csv` snapshot is intentionally treated as a local operational artifact because it is large (`~179 MB`) and the repo rules discourage committing large outputs.
- The committed reproducibility path is:
  - notebook
  - SQL export
  - baseline documentation
  - local regeneration of the CSV when needed
- If the CSV is distributed outside the repo or outside coursework submission, review it again for appropriateness and size constraints first.
