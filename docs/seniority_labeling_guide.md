# Seniority Labeling Guide

Date: `2026-04-18`  
Task: `T-1A12 Action 2`

## Purpose

This guide defines how to manually review seniority labels for the production rollout audit set in `data/samples/seniority_review_sample.csv`.

The sample is a **silver audit set**, not a gold benchmark. It is designed to expose obvious label noise before model work advances, while staying safe for repo inclusion.

## Repo-Safe Scope

The committed sample is intentionally anonymized and title-centric.

Included:
- sanitized job titles
- coarse source name
- coarse education and quality metadata
- manual reviewed label
- confidence and rationale

Excluded:
- employer names
- contact details
- raw descriptions
- direct snapshot row identifiers
- any secret or operational-only back-links

If future reviewers need to trace a sample back to a raw posting, keep that mapping outside the repo.

## Seniority Taxonomy

### Entry

Use `Entry` when the role is primarily early-career, trainee, or support-oriented.

Common cues:
- `intern`
- `trainee`
- `junior`
- `assistant`
- `attachment`
- explicitly graduate or campus roles

Typical scope:
- learning-focused work
- close supervision
- support or execution tasks without broad ownership

### Mid-Level

Use `Mid-Level` when the role is a standard professional individual contributor or coordinator with independent execution responsibility but without broad leadership scope.

Common cues:
- `officer`
- `coordinator`
- `specialist`
- `designer`
- `developer`
- `consultant` when there is no leadership cue

Typical scope:
- owns deliverables
- works independently
- may guide peers informally
- does not clearly manage a function, team, or organization

### Senior

Use `Senior` when the role has clear leadership, supervisory, lead, or advanced specialist scope, but is still below organization-level executive leadership.

Common cues:
- `senior`
- `lead`
- `manager`
- `supervisor`
- `head teacher`
- `advisor` when the role reads like a senior specialist

Typical scope:
- team leadership or departmental ownership
- advanced specialist authority
- management below director/chief/VP level

### Executive

Use `Executive` only for top-tier organizational or high-level public-service leadership roles.

Common cues:
- `director`
- `chief`
- `vp`
- `vice president`
- `principal` when it implies institution leadership
- `county secretary`
- `chief officer`

Typical scope:
- organization, division, or institution leadership
- strategic governance or top-level decision authority
- executive appointment rather than ordinary individual contribution

## Lexical Traps

These terms often create false positives and should be reviewed carefully.

- `sales executive`
  - usually not executive leadership
  - often a sales IC role
- `account executive`
  - often mid-level client-facing IC work
- `executive assistant`
  - usually entry or mid-level support, not executive
- `executive sous chef`
  - a senior culinary rank, not company executive leadership
- `chief engineer`
  - may be senior technical leadership, not necessarily executive
- `head`
  - can be senior or executive depending on organizational scope
- `advisor`
  - can be mid-level or senior depending on authority
- `consultant`
  - can be mid-level or senior depending on specialization and scope

## Review Rules

Apply these rules in order.

1. Judge hierarchy, not title prestige.
2. Prefer explicit leadership cues over education level.
3. Do not treat the word `executive` as executive leadership by default.
4. When a title contains both a senior cue and a lowering cue, prefer the more specific scope cue.
   Example: `assistant manager` is usually below `manager`.
5. If the title is too generic or noisy, assign the safest lower-confidence label and record why.

## Confidence Guide

- `high`
  - title contains a direct and unambiguous seniority cue
  - little reasonable disagreement expected
- `medium`
  - label is defensible but the title could map to more than one band
- `low`
  - title is too noisy or generic for reliable review

The current committed audit set avoids `low` confidence rows on purpose. If future review samples include low-confidence rows, record that explicitly.

## Current Action 2 Sample Design

The committed review sample is balanced by **current label**, not by reviewed label.

Composition:
- `5` rows currently labeled `Entry`
- `5` rows currently labeled `Mid-Level`
- `5` rows currently labeled `Senior`
- `5` rows currently labeled `Executive`

Why:
- this makes label noise visible across all current classes
- it prevents the audit set from collapsing into the majority class
- it surfaces known lexical traps in the current data, especially around `executive`

## Known Limits

- The sample uses sanitized titles rather than full descriptions.
- Some reviews are necessarily title-first judgments.
- This is enough for rollout gating and error discovery, but not enough for final model certification.

The next quality step after this guide is to expand into an operational-only reviewed set with richer evidence and explicit back-links.
