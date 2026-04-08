#!/usr/bin/env python3
"""Example coursework pipeline: TF-IDF + Logistic Regression."""

from __future__ import annotations

import csv
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "cleaned_sample.csv"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_examples(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    examples: list[dict[str, str]] = []
    labels: list[str] = []
    for row in rows:
        label = (row.get("experience_level") or "").strip()
        title = (row.get("title") or "").strip()
        description = (row.get("description") or "").strip()
        if not label or not title or not description:
            continue
        examples.append({"title": title, "description": description})
        labels.append(label)
    return examples, labels


def main() -> None:
    rows = load_rows(CSV_PATH)
    X, y = build_examples(rows)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    features = ColumnTransformer(
        transformers=[
            ("title_tfidf", TfidfVectorizer(max_features=1500, ngram_range=(1, 2)), "title"),
            (
                "desc_tfidf",
                TfidfVectorizer(max_features=4000, ngram_range=(1, 2), stop_words="english"),
                "description",
            ),
        ]
    )

    model = Pipeline(
        steps=[
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    multi_class="auto",
                ),
            ),
        ]
    )

    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    print("Rows used:", len(y))
    print("Classes:", sorted(set(y)))
    print(classification_report(y_test, predictions))


if __name__ == "__main__":
    main()
