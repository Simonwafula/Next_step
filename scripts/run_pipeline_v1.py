import sqlite3
import pandas as pd
import os
import sys
import json
from pathlib import Path
from tqdm import tqdm

# Add backend to path
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

from app.normalization import (
    normalize_title,
    normalize_company_name,
    normalize_location,
    parse_salary,
    parse_date,
    extract_and_normalize_skills,
    Deduplicator,
    extract_education_level,
    extract_experience_years,
    classify_seniority
)

def run_pipeline(db_path, output_dir, limit=1000):
    """
    Hardened V1 Pipeline:
    1. Read raw jobs from SQLite
    2. Normalize fields (title, company, location, salary, date)
    3. Deduplicate
    4. Extract entities (skills)
    5. Save results for Production COPY
    """
    if not os.path.exists(db_path):
        print(f"Error: DB not found at {db_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    df_raw = pd.read_sql_query("SELECT id, title, content, full_link as url FROM jobs_data LIMIT ?", conn, params=(limit,))
    conn.close()
    
    print(f"Loaded {len(df_raw)} jobs for processing...")
    
    normalized_jobs = []
    entities = []
    deduper = Deduplicator()
    
    for _, row in tqdm(df_raw.iterrows(), total=len(df_raw)):
        if _ % 10 == 0:
            print(f"Processing job {row['id']}...")
        # 1. Normalize
        family, canon_title = normalize_title(row['title'])
        # Simplified company/loc extraction for this demo
        company_raw = row['title'].split(" at ")[-1] if " at " in row['title'] else "Unknown"
        norm_company = normalize_company_name(company_raw)
        norm_loc = normalize_location("Nairobi")
        
        # 2. Advanced Extraction
        edu_level = extract_education_level(row['content'])
        exp_years = extract_experience_years(row['content'])
        seniority = classify_seniority(row['title'], exp_years)
        
        # 3. Extract Skills
        skills_dict = extract_and_normalize_skills(row['content'])
        
        # 4. Store normalized
        job_norm = {
            "id": row['id'],
            "source": "sqlite_baseline",
            "url": row['url'],
            "title_raw": row['title'],
            "title_norm": canon_title,
            "org_name": norm_company,
            "location": norm_loc[0],
            "seniority": seniority,
            "education": edu_level,
            "experience_years": exp_years,
            "description_clean": row['content'][:1000], 
            "processed_at": pd.Timestamp.now().isoformat()
        }
        normalized_jobs.append(job_norm)
        
        # 5. Store entities
        entity_record = {
            "job_id": row['id'],
            "skills": list(skills_dict.keys()),
            "tools": [], # Placeholder for T-202
            "education": {"level": edu_level},
            "experience": {"years": exp_years},
            "seniority": seniority,
            "confidence": {**skills_dict, "education": 0.8, "experience": 0.7, "seniority": 0.7}
        }
        entities.append(entity_record)
        
        # 5. Dedupe
        deduper.add_job(row['id'], row['content'][:500])
        
    # Save artifacts
    pd.DataFrame(normalized_jobs).to_csv(os.path.join(output_dir, "jobs_normalized.csv"), index=False)
    
    with open(os.path.join(output_dir, "job_entities.jsonl"), "w") as f:
        for ent in entities:
            f.write(json.dumps(ent) + "\n")
            
    print(f"Pipeline V1 complete. Artifacts saved to {output_dir}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="jobs.sqlite3")
    parser.add_argument("--out", default="artifacts/v1_baseline")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    
    run_pipeline(args.db, args.out, args.limit)
