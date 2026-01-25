# Production Transition Artifacts v1_baseline_v2

## Files & Checksums
- `jobs_normalized.csv`: `101cde1fe679ca1c39da21cad2bdff4cf416f427577d11edaa7d66fb25a058a6`
- `job_entities.jsonl`: `8a4817adedf183e085ff992de8e64cab456934a7a4580b420b8245a664a5282e`
- `job_embeddings.csv`: `2ceb0cb67748aae29abd8229560385f0a463624df34b47d6100279b338eacea4`
- `job_embeddings_meta.json`: `10567e3ac263afe30c8873b4e9845f30667bbb20d22e0bd4ff4836f096d6045d`

## Postgres Load Instructions (Postgres 14.20)

1. **Apply Migrations** (if not done):
   ```bash
   alembic upgrade head
   ```

2. **Load Normalized Jobs**:
   ```sql
   COPY job_post (id, source, url, title_raw, title_norm, org_name, location, description_clean, processed_at) 
   FROM 'jobs_normalized.csv' WITH (FORMAT csv, HEADER true);
   ```

3. **Load Entities** (Manual JSONL to JSONB import suggested or use a helper script):
   ```bash
   # Use a script to parse jsonl and insert into job_entities
   ```

4. **Load Embeddings**:
   ```sql
   COPY job_embeddings (job_id, model_name, vector_json) 
   FROM 'job_embeddings.csv' WITH (FORMAT csv, HEADER true);
   ```
