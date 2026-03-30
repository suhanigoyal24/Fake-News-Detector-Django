from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from urllib.parse import urlparse
from .models import Review
from .model_training import predict_news
import random


def clean_source(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except:
        return "Unknown Source"


def home(request):
    news_text = ""
    result = None

    facts = [
        "Over 50% of adults read news online.",
        "Fake news spreads faster than real news.",
        "Headlines often exaggerate to get clicks.",
        "Always verify news from multiple sources."
    ]
    fact = random.choice(facts)

    if request.method == "POST":

        if "review_submit" in request.POST:
            name = request.POST.get("name", "Anonymous").strip()
            review_text = request.POST.get("review", "").strip()

            if review_text:
                Review.objects.create(name=name or "Anonymous", review=review_text)
                messages.success(request, "Thanks! Review submitted.")
            else:
                messages.error(request, "Please write a review.")

            return redirect("home")

        if "check_news_btn" in request.POST:
            news_text = request.POST.get("news_text", "").strip()

            if news_text:
                result = predict_news(news_text)

                if result.get("article_url"):
                    result["source"] = clean_source(result.get("article_url"))

    return render(request, "detector/home.html", {
        "result": result,
        "news_text": news_text,
        "fact": fact
    })


# AJAX REVIEW
def submit_review(request):
    if request.method == "POST":
        name = request.POST.get("name", "Anonymous").strip()
        review_text = request.POST.get("review", "").strip()

        if review_text:
            Review.objects.create(name=name or "Anonymous", review=review_text)
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Review cannot be empty"})

    return JsonResponse({"success": False, "error": "Invalid request"})


# AJAX CHECK NEWS
def check_news(request):
    try:
        if request.method != "POST":
            return JsonResponse({"success": False, "error": "Invalid request method"})

        news_text = request.POST.get("news_text", "").strip()

        if not news_text:
            return JsonResponse({"success": False, "error": "Empty news input"})

        result = predict_news(news_text)

        url = result.get("article_url", "")
        confidence = result.get("confidence", 0)
        label = result.get("label", "").upper()

        # ✅ ALWAYS show source
        source = clean_source(url) if url else result.get("source", "Unknown Source")

        # ❌ show URL only if REAL + high confidence
        if label != "REAL" or confidence < 70:
            url = ""

        return JsonResponse({
            "success": True,
            "label": label,
            "confidence": confidence,
            "reason": result.get("reason", ""),
            "source": source,
            "url": url
        })

    except Exception as e:
        print("CHECK_NEWS ERROR:", str(e))
        return JsonResponse({"success": False, "error": "Something went wrong"})