document.addEventListener("DOMContentLoaded", function () {

    // ---------- CSRF ----------
    function getCSRFToken() {
        let cookieValue = null;
        const cookies = document.cookie.split(";");

        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith("csrftoken=")) {
                cookieValue = cookie.substring("csrftoken=".length);
                break;
            }
        }
        return cookieValue;
    }
    const csrfToken = getCSRFToken();


    // ---------- REVIEW ----------
    const reviewForm = document.getElementById("reviewForm");
    const reviewMessage = document.getElementById("reviewMessage");

    if (reviewForm) {
        reviewForm.addEventListener("submit", function (e) {
            e.preventDefault();

            const formData = new FormData(reviewForm);

            fetch(SUBMIT_REVIEW_URL, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken
                },
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    reviewMessage.textContent = "Thanks for your time! Review submitted.";
                    reviewMessage.style.display = "block";
                    reviewForm.reset();

                    setTimeout(() => {
                        reviewMessage.style.display = "none";
                    }, 3000);
                } else {
                    reviewMessage.textContent = data.error || "Error submitting review.";
                    reviewMessage.style.display = "block";
                }
            })
            .catch(() => {
                reviewMessage.textContent = "Error submitting review.";
                reviewMessage.style.display = "block";
            });
        });
    }


    // ---------- CHECK NEWS ----------
    const newsForm = document.getElementById("newsForm");
    const newsMessage = document.getElementById("newsMessage");

    const resultCard = document.getElementById("resultCard");
    const resultBox = document.getElementById("resultBox");
    const reason = document.getElementById("reason");
    const confidence = document.getElementById("confidence");
    const source = document.getElementById("source");
    const url = document.getElementById("url");

    if (newsForm) {
        newsForm.addEventListener("submit", function (e) {
            e.preventDefault();

            const formData = new FormData(newsForm);

            fetch(CHECK_NEWS_URL, {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken
                },
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    resultCard.style.display = "block";

                    resultBox.textContent = data.label.toUpperCase() + " NEWS";
                    resultBox.className = "result-box " + data.label.toLowerCase();

                    reason.textContent = data.reason ? "Reason: " + data.reason : "";
                    confidence.textContent = "Confidence: " + data.confidence + "%";
                    source.textContent = data.source ? "Source: " + data.source : "";
                    url.innerHTML = data.url ? `<a href="${data.url}" target="_blank">Read Source</a>` : "";

                    newsMessage.style.display = "none";
                } else {
                    newsMessage.textContent = data.error || "Error checking news.";
                    newsMessage.style.display = "block";
                }
            })
            .catch(() => {
                newsMessage.textContent = "Error checking news.";
                newsMessage.style.display = "block";
            });
        });
    }

});
