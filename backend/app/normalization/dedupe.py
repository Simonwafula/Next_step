from __future__ import annotations

import logging
import re

from datasketch import MinHash, MinHashLSH
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def get_shingles(text: str, k=5):
    """Generate k-shingles from text."""
    if not text:
        return set()
    text = re.sub(r"\s+", " ", text.lower().strip())
    return set(text[i : i + k] for i in range(len(text) - k + 1))


def create_minhash(text: str, num_perm=128):
    """Create a MinHash object from text shingles."""
    shingles = get_shingles(text)
    m = MinHash(num_perm=num_perm)
    for s in shingles:
        m.update(s.encode("utf8"))
    return m


class Deduplicator:
    def __init__(self, threshold=0.8, num_perm=128):
        self.lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
        self.id_map = {}  # job_id -> minhash

    def add_job(self, job_id, text):
        m = create_minhash(text)
        self.lsh.insert(str(job_id), m)
        self.id_map[job_id] = m

    def find_duplicates(self, job_id, text):
        """Find potential duplicates in the LSH index."""
        m = create_minhash(text)
        candidates = self.lsh.query(m)

        duplicates = []
        for cand_id in candidates:
            if cand_id == str(job_id):
                continue

            # Fuzzy validation
            # In a real scenario we'd fetch the candidate text
            # but for this module we assume it's external or pre-computed
            duplicates.append(
                {"job_id": int(cand_id), "score": self.id_map[int(cand_id)].jaccard(m)}
            )

        return sorted(duplicates, key=lambda x: x["score"], reverse=True)


def is_near_duplicate(text1: str, text2: str, threshold=0.9) -> bool:
    """Fuzzy string comparison for two job descriptions."""
    if not text1 or not text2:
        return False
    # Use token sort ratio for robustness against word ordering
    score = fuzz.token_sort_ratio(text1, text2) / 100.0
    return score >= threshold


# ---------------------------------------------------------------------------
# Incremental deduplication (T-601c)
# ---------------------------------------------------------------------------


def run_incremental_dedup(db, batch_size: int = 500) -> dict:
    """Find and record duplicates for jobs not yet in job_dedupe_map.

    Builds an in-memory LSH index from *all* jobs that already have dedup
    entries (the baseline), then processes new jobs in batches.  For each
    new job the best match (if any) is written to ``JobDedupeMap``.

    Returns a summary dict suitable for ProcessingLog.
    """
    from sqlalchemy import select, func

    from ..db.models import JobDedupeMap, JobPost

    # IDs already processed
    already_done_sq = select(JobDedupeMap.job_id).correlate(None).scalar_subquery()
    new_jobs_q = (
        select(JobPost.id, JobPost.description_raw)
        .where(JobPost.description_raw.is_not(None))
        .where(JobPost.id.not_in(already_done_sq))
        .order_by(JobPost.id)
    )
    total_new = db.execute(
        select(func.count()).select_from(new_jobs_q.subquery())
    ).scalar()

    if total_new == 0:
        logger.info("Incremental dedup: nothing to process.")
        return {"status": "success", "processed": 0, "duplicates_found": 0}

    # Build LSH baseline from already-processed jobs
    dedup = Deduplicator()
    baseline_q = (
        select(JobPost.id, JobPost.description_raw)
        .where(JobPost.description_raw.is_not(None))
        .where(JobPost.id.in_(already_done_sq))
        .order_by(JobPost.id)
    )
    baseline_count = 0
    for job_id, text in db.execute(baseline_q):
        dedup.add_job(job_id, text)
        baseline_count += 1
    logger.info("Incremental dedup: loaded %d baseline jobs into LSH.", baseline_count)

    # Process new jobs in batches
    processed = 0
    duplicates_found = 0
    offset = 0

    while offset < total_new:
        rows = db.execute(new_jobs_q.offset(offset).limit(batch_size)).all()
        if not rows:
            break

        for job_id, text in rows:
            matches = dedup.find_duplicates(job_id, text)
            if matches:
                best = matches[0]
                db.add(
                    JobDedupeMap(
                        job_id=job_id,
                        canonical_job_id=best["job_id"],
                        similarity_score=best["score"],
                    )
                )
                duplicates_found += 1
            else:
                # Record self-mapping so this job is in the "done" set
                db.add(
                    JobDedupeMap(
                        job_id=job_id,
                        canonical_job_id=job_id,
                        similarity_score=1.0,
                    )
                )
            # Add to index for subsequent matches within this batch
            dedup.add_job(job_id, text)
            processed += 1

        db.commit()
        offset += batch_size
        logger.info("Incremental dedup: %d / %d processed.", processed, total_new)

    summary = {
        "status": "success",
        "processed": processed,
        "duplicates_found": duplicates_found,
        "baseline_size": baseline_count,
    }
    logger.info("Incremental dedup complete: %s", summary)
    return summary
