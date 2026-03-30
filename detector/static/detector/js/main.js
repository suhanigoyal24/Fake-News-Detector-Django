document.addEventListener("DOMContentLoaded", function () {

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

    const historyList = document.getElementById("historyList");
    const newsForm = document.getElementById("newsForm");

    const resultCard = document.getElementById("resultCard");
    const resultBadge = document.getElementById("resultBadge");

    const confidenceFill = document.getElementById("confidenceFill");
    const confidenceText = document.getElementById("confidenceText");

    const reasonEl = document.getElementById("reason");
    const sourceEl = document.getElementById("source");
    const urlEl = document.getElementById("url");

    // HISTORY
    function saveHistory(text, label, confidence) {
        let history = JSON.parse(localStorage.getItem("newsHistory")) || [];

        history = history.filter(item => item.text !== text);
        history.unshift({ text, label, confidence });
        history = history.slice(0, 3);

        localStorage.setItem("newsHistory", JSON.stringify(history));
        loadHistory();
    }

    function loadHistory() {
        if (!historyList) return;

        let history = JSON.parse(localStorage.getItem("newsHistory")) || [];
        historyList.innerHTML = "";

        if (history.length === 0) {
            historyList.innerHTML = "<p>No history yet</p>";
            return;
        }

        history.forEach(item => {
            let cls = item.label === "REAL" ? "real" : "fake";

            let div = document.createElement("div");
            div.innerHTML = `
                <div class="history-row">
                    <span class="badge ${cls}">
                        ${item.label} (${item.confidence}%)
                    </span>
                    <p>${item.text}</p>
                </div>
            `;
            historyList.appendChild(div);
        });
    }

    loadHistory();

    // CHECK NEWS
    if (newsForm) {
        newsForm.addEventListener("submit", function (e) {
            e.preventDefault();

            const formData = new FormData(newsForm);
            const text = formData.get("news_text");

            if (!text.trim()) return;

            fetch(CHECK_NEWS_URL, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                body: formData
            })
            .then(res => res.json())
            .then(data => {

                if (!data.success) {
                    alert(data.error);
                    return;
                }

                resultCard.style.display = "block";

                let label = data.label;
                let conf = data.confidence;

                resultBadge.textContent = label + " NEWS";
                resultBadge.className = "badge " + (label === "REAL" ? "real" : "fake");

                confidenceFill.style.width = conf + "%";
                confidenceText.textContent = "Confidence: " + conf + "%";

                reasonEl.textContent = data.reason ? "Reason: " + data.reason : "";
                sourceEl.textContent = "Source: " + (data.source || "Unknown");

                urlEl.innerHTML = data.url
                    ? `<a href="${data.url}" target="_blank">Read Source</a>`
                    : "";

                saveHistory(text, label, conf);
            });
        });
    }

});