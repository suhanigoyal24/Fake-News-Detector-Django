# model_training.py

import pandas as pd
import string
import os
import pickle
import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.metrics.pairwise import cosine_similarity

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(PROJECT_ROOT, "news.db")
MODEL_FILE = os.path.join(PROJECT_ROOT, "model_state.pkl")


# --------------------------------------------------------------------------
# Preprocess Text
# --------------------------------------------------------------------------
def preprocess_text(text):
    text = str(text).lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    tokens = text.split()
    return " ".join(tokens)

# --------------------------------------------------------------------------
# Map domain to human-readable source name
# --------------------------------------------------------------------------
SOURCE_MAPPING = {
    "www.bhaskar.com": "Dainik Bhaskar",
    "bhaskar.com": "Dainik Bhaskar",
    "www.ndtv.com": "NDTV",
    "ndtv.com": "NDTV",
    "www.bbc.com": "BBC",
    "bbc.com": "BBC",
    "www.hindustantimes.com": "Hindustan Times",
    "hindustantimes.com": "Hindustan Times",
    "www.indiatoday.in": "India Today",
    "indiatoday.in": "India Today",
    "www.thequint.com": "The Quint",
    "thequint.com": "The Quint",
    "www.altnews.in": "Alt News",
    "altnews.in": "Alt News",
    "www.snopes.com": "Snopes",
    "snopes.com": "Snopes",
}

def get_source_name(url):
    if isinstance(url, str) and url.strip():
        try:
            domain = url.split("/")[2]
            return SOURCE_MAPPING.get(domain, domain)
        except IndexError:
            return "Unknown Source"
    return "Unknown Source"

# --------------------------------------------------------------------------
# Load Dataset from SQLite DB
# --------------------------------------------------------------------------
def load_dataset():
    """Load news dataset from SQLite DB. Returns empty DataFrame if table missing."""
    if not os.path.exists(DB_FILE):
        print(f"[WARN] {DB_FILE} not found. Returning empty dataset.")
        return pd.DataFrame(columns=["id", "text", "label", "article_url", "cleaned_text", "source"])

    conn = sqlite3.connect(DB_FILE)
    query = "SELECT id, text, label, article_url FROM news_table"  # Only required columns
    try:
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        print("[WARN] Could not load table:", e)
        df = pd.DataFrame(columns=["id", "text", "label", "article_url", "cleaned_text", "source"])
    finally:
        conn.close()

    if df.empty:
        print("[WARN] Dataset is empty after loading.")
        return pd.DataFrame(columns=["id", "text", "label", "article_url", "cleaned_text", "source"])

    # Preprocess text and add extra columns
    df["cleaned_text"] = df["text"].astype(str).apply(preprocess_text)
    df["source"] = df["article_url"].astype(str).apply(get_source_name)
    df.reset_index(drop=True, inplace=True)

    print(f"[INFO] Loaded {len(df)} articles from database.")
    return df

# --------------------------------------------------------------------------
# Train Model
# --------------------------------------------------------------------------
def train_model():
    df = load_dataset()
    if df.empty:
        print("[WARN] Dataset is empty. Training skipped.")
        return df, None, None

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    X = vectorizer.fit_transform(df["cleaned_text"])
    y = df["label"]

    model = SVC(probability=True)
    model.fit(X, y)

    with open(MODEL_FILE, "wb") as f:
        pickle.dump((df, vectorizer, model), f)

    print("[INFO] Model trained and saved successfully.")
    return df, vectorizer, model

# --------------------------------------------------------------------------
# Lazy Loading for Django Safety
# --------------------------------------------------------------------------
_df = None
_vectorizer = None
_model = None

def get_model():
    global _df, _vectorizer, _model
    if _df is None or _vectorizer is None or _model is None:
        try:
            _df, _vectorizer, _model = load_or_train()
        except Exception as e:
            print(f"[ERROR] Could not load or train model: {e}")
            _df, _vectorizer, _model = pd.DataFrame(), None, None
    return _df, _vectorizer, _model

# --------------------------------------------------------------------------
# Load or Retrain Automatically
# --------------------------------------------------------------------------
def load_or_train():
    if not os.path.exists(MODEL_FILE):
        return train_model()

    if os.path.exists(DB_FILE):
        db_time = os.path.getmtime(DB_FILE)
        model_time = os.path.getmtime(MODEL_FILE)
        if db_time > model_time:
            print("[INFO] Database updated — retraining model...")
            return train_model()

    with open(MODEL_FILE, "rb") as f:
        df, vectorizer, model = pickle.load(f)
    return df, vectorizer, model

# --------------------------------------------------------------------------
# Predict Function
# --------------------------------------------------------------------------
def predict_news(text, confidence_threshold=80):
    df, vectorizer, model = get_model()
    cleaned = preprocess_text(text)

    if vectorizer is None or model is None:
        return {
            "prediction": "Model not trained",
            "confidence": 0,
            "source": "Unknown",
            "confidence_source": "0% credibility estimate",
            "matched_headline": "N/A",
            "article_url": "N/A"
        }

    vector_input = vectorizer.transform([cleaned])
    pred_label = model.predict(vector_input)[0]
    confidence = float(model.predict_proba(vector_input).max()) * 100

    filtered_df = df[df["label"] == pred_label].copy()
    filtered_df = filtered_df[filtered_df["article_url"].notna() & (filtered_df["article_url"].str.strip() != "")]

    if filtered_df.empty:
        matched_headline = "No similar article found"
        article_url = "No URL available"
        source_name = "Unknown Source"
    else:
        similarities = cosine_similarity(vector_input, vectorizer.transform(filtered_df["cleaned_text"]))
        idx = similarities[0].argmax()
        closest_row = filtered_df.iloc[idx]
        article_url = closest_row.get("article_url", "No URL available")
        source_name = get_source_name(article_url)
        matched_headline = closest_row["text"]

    prediction_text = "Possibly Fake / Needs Verification" if confidence < confidence_threshold else pred_label.upper()

    return {
        "prediction": prediction_text,
        "confidence": round(confidence, 2),
        "source": source_name,
        "confidence_source": f"{round(confidence, 2)}% credibility estimate",
        "matched_headline": matched_headline,
        "article_url": article_url
    }

# --------------------------------------------------------------------------
# Run model safely when executed directly
# --------------------------------------------------------------------------
if __name__ == "__main__":
    df, vectorizer, model = get_model()
    print("[INFO] Model ready and dataset loaded.")
