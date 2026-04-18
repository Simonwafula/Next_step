# Seniority Rollout Policy

Date: `2026-04-18`  
Task: `T-1A12 Action 1`

## Purpose

This document defines how model-predicted seniority is allowed to influence the Next Step product while the current offline quality remains below the bar for hard user-facing decisions.

It applies to future **predicted seniority** generated from the seniority-model rollout work. It does **not** replace the existing `JobPost.seniority` field already populated from ingestion-time extraction and title heuristics.

## Baseline Constraint

The frozen baseline in `docs/seniority_baseline.md` shows sampled weighted F1 around `0.6-0.65`. That is useful for internal prioritization and experimentation, but not strong enough for unconditional hard filtering or silent suppression of jobs for users.

## Policy Decision

Chosen rollout mode: `internal_only`

Interpretation:
- predicted seniority may be used as a secondary internal relevance signal
- predicted seniority may be stored and audited once Action 6 is complete
- predicted seniority must not be used as a hard eligibility rule
- predicted seniority must not drive a public filter control in the current rollout phase

Deferred modes:
- `soft_user_label`: deferred until reviewed-label evaluation, confidence calibration, and prediction storage/versioning exist
- `hard_filter`: explicitly disallowed until a later policy review

## Confidence Bands

These bands define how future model output is interpreted.

- `high_confidence`
  - calibrated top-class probability `>= 0.80`
  - top-1 vs top-2 margin `>= 0.15`
  - or deterministic rule hit from a reviewed seniority rule layer
- `medium_confidence`
  - calibrated top-class probability `>= 0.60`
  - top-1 vs top-2 margin `>= 0.10`
  - no contradicting deterministic rule
- `low_confidence`
  - anything below the thresholds above
  - any uncalibrated notebook-only score
  - any prediction with conflicting rule/model evidence

Until calibrated probabilities exist in production, all notebook-style model outputs are treated as `low_confidence` research signals by default.

## User-Facing Language

If soft labels are approved later, only the following wording is allowed:

- `Likely Entry`
- `Likely Mid-Level`
- `Likely Senior`
- `Likely Executive`

Do not present predicted labels as facts. If shown, pair them with confidence-aware wording such as `Likely Senior` rather than `Senior`.

## Allowed Product Usage

### Search Ranking

Allowed now:
- use predicted seniority as a small ranking feature behind existing lexical, semantic, quality, and recency signals
- use it only to reorder results, not to remove them

Not allowed now:
- do not zero out results because predicted seniority disagrees with the user profile
- do not let predicted seniority outrank stronger verified relevance signals on its own

Implementation note:
- existing search APIs and ranking code already handle `seniority` as a contextual feature; predicted seniority should enter that path only as a bounded internal signal, with raw extracted seniority remaining the stronger source when present

### Alerts

Allowed now:
- use predicted seniority only for internal ordering of alert candidates when confidence is high
- use it to diversify or annotate internal digest generation

Not allowed now:
- do not suppress an alert solely because predicted seniority looks mismatched
- do not expose predicted seniority text in alert copy during the `internal_only` phase

### Recommendations And Match Surfaces

Allowed now:
- use predicted seniority as a secondary feature in recommendation scoring
- use it in internal diagnostics for recommendation quality review

Deferred:
- showing `Likely ...` labels in seeker-facing recommendation cards requires the `soft_user_label` promotion gate below

### Explicit Filter UI

Not allowed now:
- no predicted-seniority filter chip, dropdown, or hard constraint in the public UI
- no API parameter that filters only on model-predicted seniority

Current exception:
- the existing search/filter behavior for the already-populated `JobPost.seniority` field may remain, because that is part of the current ingestion-time data model rather than the new predictive model rollout

## Promotion Gates

### Gate To `soft_user_label`

All of the following must be true:
- Action 2 reviewed audit set exists
- Action 4 rule layer exists
- Action 5 offline evaluation shows meaningful improvement over the frozen baseline
- Action 6 prediction storage includes label, confidence band, source, and model version
- per-class evaluation is reviewed and no class is obviously unsafe to surface
- calibration review shows that `high_confidence` is materially trustworthy

Minimum evidence for promotion review:
- macro F1 at least `0.70`
- weighted F1 at least `0.75`
- no class recall below `0.60`
- documented confusion patterns for ambiguous titles

### Gate To `hard_filter`

Hard filtering remains prohibited unless a separate policy document replaces this one. That later review must show:
- audited high-confidence precision is strong enough for user-facing exclusion decisions
- rollback and re-backfill paths are proven
- the product team explicitly accepts the false-negative risk

## Logging And Audit Requirements

When predicted seniority enters production code, the system must log or persist:
- predicted label
- confidence band
- score or probability
- prediction source (`rule`, `model`, or `hybrid`)
- model version
- timestamp/backfill context when generated

Do not log secrets, raw credentials, or unsafe user-identifying exports.

## Deferred Decisions Recorded Here

- Soft user labels are deferred until the reviewed audit set, rule layer, stronger model evaluation, and versioned storage exist.
- Hard filters are deferred beyond the current rollout plan and require a new policy decision.
- Existing extracted `JobPost.seniority` remains usable in current product filters; this policy governs only the new predicted seniority path.
