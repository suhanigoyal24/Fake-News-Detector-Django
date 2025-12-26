from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Review
from .model_training import preprocess_text, get_model
from .constant_fakes import IMPOSSIBLE_STATEMENTS
from urllib.parse import urlparse
from sklearn.metrics.pairwise import cosine_similarity
import random
from django.http import JsonResponse


# ------------------- Helper functions -------------------

def get_source_name(article_url):
    try:
        parsed = urlparse(article_url)
        domain = parsed.netloc.lower()
        for sub in ["www.", "m.", "news.", "en."]:
            domain = domain.replace(sub, "")
        name_part = domain.split(".")[0]
        return " ".join(word.capitalize() for word in name_part.replace("-", " ").split())
    except:
        return "Unknown Source"


def is_impossible(text):
    for stmt in IMPOSSIBLE_STATEMENTS:
        if stmt.lower() in text.lower():
            return True, stmt
    return False, ""


def find_closest_match(cleaned_text, df, vectorizer):
    if df.empty:
        return None

    vectors = vectorizer.transform(df["cleaned_text"])
    input_vec = vectorizer.transform([cleaned_text])
    similarity = cosine_similarity(input_vec, vectors)[0]
    idx = similarity.argmax()
    return df.iloc[idx]


# ------------------- Main View -------------------

def home(request):
    result = None
    news_text = ""

    # Random fact
    facts = [
        "Over 50% of adults read news online.",
        "Fake news spreads faster than real news.",
        "Headlines often exaggerate to get clicks.",
        "Always verify news from multiple sources."
    ]
    fact = random.choice(facts)

    # Load ML model
    df, vectorizer, model = get_model()

    # -------------------- POST Requests --------------------
    if request.method == "POST":

        # ---------- Review Submit ----------
        if "review_submit" in request.POST:
            name = request.POST.get("name", "Anonymous")
            review_text = request.POST.get("review", "").strip()

            if review_text:
                Review.objects.create(name=name or "Anonymous", review=review_text)
                messages.success(request, "Thanks for your time! Your review was submitted successfully.")
            else:
                messages.error(request, "Please write something before submitting.")

            return redirect("home")

        # ---------- Check News ----------
        if "check_news_btn" in request.POST:
            news_text = request.POST.get("news_text", "")

            if news_text.strip():
                impossible, reason = is_impossible(news_text)

                # Impossible rule-based fake
                if impossible:
                    result = {
                        "label": "fake",
                        "reason": reason,
                        "confidence": 100,
                        "source": "",
                        "url": ""
                    }

                # Model not ready
                elif model is None or vectorizer is None or df.empty:
                    result = {
                        "label": "Model not ready",
                        "confidence": 0,
                        "source": "Unknown",
                        "url": ""
                    }

                # ML Prediction
                else:
                    cleaned = preprocess_text(news_text)
                    input_vec = vectorizer.transform([cleaned])
                    pred = model.predict(input_vec)[0]
                    prob = model.predict_proba(input_vec)[0]
                    confidence = round(max(prob) * 100, 2)

                    closest = find_closest_match(cleaned, df, vectorizer)

                    if closest is not None:
                        source = closest.get("source", get_source_name(closest.get("article_url", "")))
                        url = closest.get("article_url", "")
                    else:
                        source = "Unknown"
                        url = ""

                    result = {
                        "label": pred,
                        "confidence": confidence,
                        "source": source,
                        "url": url
                    }

    # We DO NOT send reviews to template anymore
    return render(request, "detector/home.html", {
        "result": result,
        "news_text": news_text,
        "fact": fact
    })
def submit_review(request):
    if request.method == "POST":
        name = request.POST.get("name", "Anonymous").strip()
        review_text = request.POST.get("review", "").strip()

        if review_text:
            Review.objects.create(name=name or "Anonymous", review=review_text)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Review cannot be empty"})

def check_news(request):
    try:
        if request.method != "POST":
            return JsonResponse({"success": False, "error": "Invalid request method"})

        news_text = request.POST.get("news_text", "").strip()
        if not news_text:
            return JsonResponse({"success": False, "error": "Empty news"})

        # Load model
        df, vectorizer, model = get_model()

        # Rule-based impossible
        impossible, reason = is_impossible(news_text)
        if impossible:
            return JsonResponse({
                "success": True,
                "label": "fake",
                "confidence": 100,
                "reason": reason,
                "source": "",
                "url": ""
            })

        if model is None or vectorizer is None or df is None or df.empty:
            return JsonResponse({
                "success": False,
                "error": "Model not loaded"
            })

        cleaned = preprocess_text(news_text)
        input_vec = vectorizer.transform([cleaned])

        pred = model.predict(input_vec)[0]
        prob = model.predict_proba(input_vec)[0]
        confidence = round(max(prob) * 100, 2)

        closest = find_closest_match(cleaned, df, vectorizer)

        if closest is not None:
            source = closest.get("source", get_source_name(closest.get("article_url", "")))
            url = closest.get("article_url", "")
        else:
            source = "Unknown"
            url = ""

        return JsonResponse({
            "success": True,
            "label": pred,
            "confidence": confidence,
            "source": source,
            "url": url
        })

    except Exception as e:
        print("CHECK_NEWS ERROR:", str(e))
        return JsonResponse({"success": False, "error": str(e)})
