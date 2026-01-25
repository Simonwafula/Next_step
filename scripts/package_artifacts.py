import os
import hashlib
import json
from pathlib import Path

def get_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def package_artifacts(artifact_dir):
    files = [
        "jobs_normalized.csv",
        "job_entities.jsonl",
        "job_embeddings.csv",
        "job_embeddings_meta.json"
    ]
    
    print(f"Packaging artifacts in {artifact_dir}...")
    checksums = {}
    
    for f in files:
        full_path = os.path.join(artifact_dir, f)
        if os.path.exists(full_path):
            checksums[f] = get_sha256(full_path)
            print(f"  {f}: {checksums[f]}")
        else:
            print(f"  Warning: {f} missing!")
            
    with open(os.path.join(artifact_dir, "checksums.txt"), "w") as f:
        for name, sha in checksums.items():
            f.write(f"{sha}  {name}\n")
            
    # Generate README_PROD.md
    readme_content = f"""# Production Transition Artifacts {os.path.basename(artifact_dir)}

## Files & Checksums
"""
    for name, sha in checksums.items():
        readme_content += f"- `{name}`: `{sha}`\n"
        
    readme_content += """
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
"""
    with open(os.path.join(artifact_dir, "README_PROD.md"), "w") as f:
        f.write(readme_content)
        
    print(f"Artifacts packaged. README_PROD.md and checksums.txt created.")

if __name__ == "__main__":
    package_artifacts("artifacts/v1_baseline_v2")
