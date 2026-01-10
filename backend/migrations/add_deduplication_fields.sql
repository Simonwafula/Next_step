-- Migration: Add deduplication and quality fields to job_post table
-- Date: 2026-01-08
-- Description: Adds url_hash, repost_count, quality_score, and processed_at fields for enhanced deduplication

-- Add url_hash column for fast duplicate lookups
ALTER TABLE job_post ADD COLUMN IF NOT EXISTS url_hash VARCHAR(32);

-- Add index on url_hash for performance
CREATE INDEX IF NOT EXISTS idx_job_post_url_hash ON job_post(url_hash);

-- Add repost_count to track job urgency/popularity
ALTER TABLE job_post ADD COLUMN IF NOT EXISTS repost_count INTEGER DEFAULT 0;

-- Add quality_score for data quality tracking
ALTER TABLE job_post ADD COLUMN IF NOT EXISTS quality_score FLOAT;

-- Add processed_at timestamp
ALTER TABLE job_post ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP;

-- Populate url_hash for existing records (if any)
-- This should be run after deployment to backfill existing data
-- UPDATE job_post SET url_hash = MD5(LOWER(TRIM(url))) WHERE url_hash IS NULL;

COMMENT ON COLUMN job_post.url_hash IS 'MD5 hash of normalized URL for fast duplicate detection';
COMMENT ON COLUMN job_post.repost_count IS 'Number of times this job has been reposted (signal of urgency)';
COMMENT ON COLUMN job_post.quality_score IS 'Data quality score 0-100';
COMMENT ON COLUMN job_post.processed_at IS 'Timestamp when job was fully processed (normalized, skills extracted, etc.)';
