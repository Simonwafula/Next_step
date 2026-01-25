import pandas as pd
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

from app.db.database import engine, SessionLocal, init_db
from app.db.models import Base, JobPost, JobEntities, JobEmbedding, TitleNorm

def load_baseline_to_sqlite(artifact_dir):
    print(f"Initializing fresh database schema...")
    # This will use the DATABASE_URL from .env via settings
    init_db()
    
    db = SessionLocal()
    try:
        print(f"Loading baseline from {artifact_dir}...")
        
        # 1. Clear existing
        db.query(JobPost).delete()
        db.query(JobEntities).delete()
        db.query(JobEmbedding).delete()
        db.query(TitleNorm).delete()
        db.commit()
        
        # 2. Dummy TitleNorm
        tn = TitleNorm(id=1, family="software_development", canonical_title="Software Engineer")
        db.add(tn)
        db.commit()
        
        # 3. Load Normalized Jobs
        jobs_df = pd.read_csv(os.path.join(artifact_dir, "jobs_normalized.csv"))
        now = datetime.utcnow()
        for _, row in jobs_df.iterrows():
            jp = JobPost(
                id=int(row['id']),
                source=row['source'],
                url=row['url'],
                title_raw=row['title_raw'],
                title_norm_id=1,
                processed_at=datetime.fromisoformat(row['processed_at']) if isinstance(row['processed_at'], str) else now,
                first_seen=now,
                last_seen=now,
                repost_count=0,
                attachment_flag=False,
                seniority=row['seniority'] if 'seniority' in row else None,
                education=row['education'] if 'education' in row else None
            )
            db.add(jp)
        db.commit()
        print(f"  Loaded {len(jobs_df)} jobs.")
            
        # 4. Load Entities
        with open(os.path.join(artifact_dir, "job_entities.jsonl"), "r") as f:
            count = 0
            for line in f:
                data = json.loads(line)
                ent = JobEntities(
                    job_id=data['job_id'],
                    skills=data['skills'],
                    education=data['education'],
                    experience=data['experience']
                )
                db.add(ent)
                count += 1
        db.commit()
        print(f"  Loaded {count} entities.")
                  
        # 5. Load Embeddings
        emb_df = pd.read_csv(os.path.join(artifact_dir, "job_embeddings.csv"))
        for _, row in emb_df.iterrows():
            # row['vector'] is a string representation of a list
            vec = json.loads(row['vector']) if isinstance(row['vector'], str) else row['vector']
            emb = JobEmbedding(
                job_id=int(row['job_id']),
                model_name=row['model_name'],
                vector_json=vec
            )
            db.add(emb)
        db.commit()
        print(f"  Loaded {len(emb_df)} embeddings.")
        
    except Exception as e:
        db.rollback()
        print(f"Error during load: {e}")
        raise
    finally:
        db.close()
    print("Baseline loaded successfully.")

if __name__ == "__main__":
    load_baseline_to_sqlite("artifacts/v1_full_baseline")
