# ruff: noqa: E402
import pandas as pd
from sentence_transformers import SentenceTransformer
import os
import sys
from pathlib import Path
import json

# Add backend to path
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))


def generate_embeddings(input_csv, output_csv, model_name="intfloat/e5-small-v2"):
    """
    Generate embeddings for normalized jobs.
    Artifact: job_embeddings.csv
    """
    if not os.path.exists(input_csv):
        print(f"Error: Input CSV not found at {input_csv}")
        return

    print(f"Loading model {model_name}...")
    model = SentenceTransformer(model_name)

    df = pd.read_csv(input_csv)
    print(f"Generating embeddings for {len(df)} jobs...")

    # Combine title and description for embedding as per common practice
    # Or just use description_clean
    texts = [
        f"query: {row['title_norm']} {row['description_clean']}"
        for _, row in df.iterrows()
    ]

    embeddings = model.encode(texts, show_progress_bar=True)

    embedding_records = []
    for i, row in df.iterrows():
        embedding_records.append(
            {
                "job_id": row["id"],
                "model_name": model_name,
                "vector": embeddings[i].tolist(),
            }
        )

    pd.DataFrame(embedding_records).to_csv(output_csv, index=False)

    # Save metadata
    meta = {
        "model_name": model_name,
        "dim": len(embeddings[0]),
        "count": len(embeddings),
        "created_at": pd.Timestamp.now().isoformat(),
    }
    with open(output_csv.replace(".csv", "_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Embeddings saved to {output_csv}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", default="artifacts/v1_baseline_v2/jobs_normalized.csv"
    )
    parser.add_argument("--out", default="artifacts/v1_baseline_v2/job_embeddings.csv")
    args = parser.parse_args()

    generate_embeddings(args.input, args.out)
