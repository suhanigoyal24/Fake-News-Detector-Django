import pandas as pd
import string
import os
import pickle
import sqlite3
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.metrics.pairwise import cosine_similarity

from .constant_fakes import IMPOSSIBLE_STATEMENTS

# PATHS
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(PROJECT_ROOT, "news.db")
MODEL_FILE = os.path.join(PROJECT_ROOT, "model_state.pkl")

# PREPROCESS
def preprocess_text(text):
    text = str(text).lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return text

# LOAD DATA
def load_dataset():
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=["text", "label", "article_url"])

    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query("SELECT text, label, article_url FROM news_table", conn)
    except:
        df = pd.DataFrame(columns=["text", "label", "article_url"])
    finally:
        conn.close()

    if df.empty:
        return df

    df["cleaned_text"] = df["text"].apply(preprocess_text)
    return df

# TRAIN MODEL
def train_model():
    df = load_dataset()
    if df.empty:
        return None, None, None

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    X = vectorizer.fit_transform(df["cleaned_text"])
    y = df["label"]

    model = SVC(probability=True)
    model.fit(X, y)

    with open(MODEL_FILE, "wb") as f:
        pickle.dump((df, vectorizer, model), f)

    return df, vectorizer, model

# LOAD MODEL
_df, _vectorizer, _model = None, None, None

def get_model():
    global _df, _vectorizer, _model

    if _df is None:
        if not os.path.exists(MODEL_FILE):
            _df, _vectorizer, _model = train_model()
        else:
            with open(MODEL_FILE, "rb") as f:
                _df, _vectorizer, _model = pickle.load(f)

    return _df, _vectorizer, _model

#  FLEXIBLE IMPOSSIBLE CHECK
def is_impossible(text):
    text_clean = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())

    for stmt in IMPOSSIBLE_STATEMENTS:
        stmt_clean = re.sub(r'[^a-zA-Z0-9\s]', '', stmt.lower())

        if stmt_clean in text_clean:
            return True, stmt

        words = stmt_clean.split()
        match = sum(1 for w in words if w in text_clean)

        if match >= max(2, len(words)//2):
            return True, stmt

    return False, ""

# FIND CLOSEST
def find_closest(cleaned, df, vectorizer):
    if df is None or df.empty:
        return None

    vectors = vectorizer.transform(df["cleaned_text"])
    input_vec = vectorizer.transform([cleaned])
    sim = cosine_similarity(input_vec, vectors)[0]
    idx = sim.argmax()
    return df.iloc[idx]

#  FINAL PREDICT
def predict_news(text):
    df, vectorizer, model = get_model()

    # RULE-BASED
    impossible, reason = is_impossible(text)
    if impossible:
        return {
        "label": "FAKE",
        "confidence": 95,
        "reason": "This claim is false and contradicts established scientific facts.",
        "source": "Rule-based",
        "article_url": ""
    }

    # MODEL CHECK
    if model is None or vectorizer is None or df is None or df.empty:
        return {
            "label": "FAKE",
            "confidence": 50,
            "reason": "Model not available",
            "source": "",
            "article_url": ""
        }

    # ML
    cleaned = preprocess_text(text)
    input_vec = vectorizer.transform([cleaned])

    pred = model.predict(input_vec)[0]
    prob = model.predict_proba(input_vec)[0]
    confidence = round(max(prob) * 100, 2)

    closest = find_closest(cleaned, df, vectorizer)

    if closest is not None:
        url = closest.get("article_url", "")
    else:
        url = ""

    return {
        "label": str(pred).upper(),
        "confidence": confidence,
        "reason": "",
        "source": "",
        "article_url": url
    }