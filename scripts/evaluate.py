# scripts/evaluate.py
# Run from the project root folder:
#   python scripts/evaluate.py
#
# Compares class_weight strategies on the same train/test split so you can
# pick whichever gives the best fake-class recall/precision for your resume.
# Does NOT overwrite model_state.pkl.

import os
import sqlite3
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from detector.model_training import preprocess_text

DB_FILE = os.path.join(PROJECT_ROOT, "ml_artifacts", "news.db")
RANDOM_STATE = 42  # fixed so results are reproducible run-to-run


def load_dataset():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT text, label, article_url FROM news_table", conn)
    conn.close()
    df["cleaned_text"] = df["text"].apply(preprocess_text)
    return df


def run_config(name, class_weight, X_train_vec, X_test_vec, y_train, y_test):
    model = SVC(probability=True, class_weight=class_weight, random_state=RANDOM_STATE)
    model.fit(X_train_vec, y_train)
    y_pred = model.predict(X_test_vec)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, pos_label="fake")
    rec = recall_score(y_test, y_pred, pos_label="fake")
    f1 = f1_score(y_test, y_pred, pos_label="fake")
    weighted_f1 = f1_score(y_test, y_pred, average="weighted")

    print("\n" + "=" * 60)
    print(f"CONFIG: {name}  (class_weight={class_weight})")
    print("=" * 60)
    print(f"Accuracy:              {acc:.4f}")
    print(f"Fake Precision:        {prec:.4f}")
    print(f"Fake Recall:           {rec:.4f}")
    print(f"Fake F1:               {f1:.4f}")
    print(f"Weighted F1 (overall): {weighted_f1:.4f}")

    labels = ["fake", "real"]
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    print("\nConfusion Matrix (rows=actual, cols=predicted):")
    print(f"           pred_fake  pred_real")
    for i, row_label in enumerate(labels):
        print(f"actual_{row_label:<5} {cm[i][0]:>9} {cm[i][1]:>10}")

    print("\n" + classification_report(y_test, y_pred, target_names=labels))

    return {"name": name, "accuracy": acc, "fake_f1": f1, "weighted_f1": weighted_f1}


def main():
    print("Loading dataset...")
    df = load_dataset()
    print(f"Total rows: {len(df)}")
    print(df["label"].value_counts())

    X_text = df["cleaned_text"]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X_text, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"\nTrain size: {len(X_train)}  |  Test size: {len(X_test)}")

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    results = []
    results.append(run_config(
        "Current (manual 3:1)", {"fake": 3, "real": 1},
        X_train_vec, X_test_vec, y_train, y_test
    ))
    results.append(run_config(
        "Balanced (auto)", "balanced",
        X_train_vec, X_test_vec, y_train, y_test
    ))
    results.append(run_config(
        "Manual 5:1", {"fake": 5, "real": 1},
        X_train_vec, X_test_vec, y_train, y_test
    ))

    print("\n" + "=" * 60)
    print("SUMMARY (pick the best for your resume)")
    print("=" * 60)
    for r in results:
        print(f"{r['name']:<25} acc={r['accuracy']:.4f}  fake_f1={r['fake_f1']:.4f}  weighted_f1={r['weighted_f1']:.4f}")


if __name__ == "__main__":
    main()