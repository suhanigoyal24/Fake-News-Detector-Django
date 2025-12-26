# dynamic_news_scraper_db_cleaned.py

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
import time
import re
import html

# ---------------- SOURCES ----------------
real_sources = [
    "https://www.hindustantimes.com/",
    "https://www.indiatoday.in/",
    "https://www.ndtv.com/latest",
    "https://www.dnaindia.com/",
    "https://www.bhaskar.com/",
    "https://timesofindia.indiatimes.com/",
    "https://www.reuters.com/world/",
    "https://www.bbc.com/news"
]

fake_sources = [
    "https://www.altnews.in/fake-news/",
    "https://www.boomlive.in/fact-check/",
    "https://www.factchecker.in/",
    "https://www.thequint.com/webqoof",
    "https://www.indiatoday.in/fact-check",
    "https://factcheck.pib.gov.in/",
    "https://www.snopes.com/fact-check/",
    "https://factcheck.afp.com/",
    "https://www.reuters.com/fact-check/"
]

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect("news.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS news_table (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    label TEXT,
    article_url TEXT UNIQUE
)
""")
conn.commit()

# ---------------- TEXT CLEANING ----------------
def clean_text(text):
    text = html.unescape(text)  # convert HTML entities
    text = re.sub(r'\s+', ' ', text)  # remove extra spaces/newlines
    text = text.strip()
    text = text.lower()  # lowercase for consistency
    return text

# ---------------- SCRAPER ----------------
def scrape_url(url, label, retries=3, delay=2):
    articles = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive"
    }

    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            for link in soup.find_all("a", href=True):
                title = clean_text(link.get_text())
                if len(title) < 8:  # skip very short titles
                    continue
                href = link["href"]
                full_url = href if href.startswith("http") else urljoin(url, href)
                articles.append({"text": title, "label": label, "article_url": full_url})
            return articles
        except requests.exceptions.RequestException as e:
            print(f"[WARN] Attempt {attempt+1} failed for {url} -> {e}")
            time.sleep(delay)
    print(f"[ERROR] Skipping URL due to repeated failures: {url}")
    return articles

# ---------------- DYNAMIC SCRAPING ----------------
def scrape_all(sources, label, max_workers=8):
    all_articles = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(scrape_url, url, label): url for url in sources}
        for future in as_completed(future_to_url):
            articles = future.result()
            all_articles.extend(articles)
    return all_articles

# ---------------- DATABASE INSERTION ----------------
def insert_articles_to_db(articles):
    count = 0
    for article in articles:
        try:
            cursor.execute("""
            INSERT OR IGNORE INTO news_table (text, label, article_url)
            VALUES (?, ?, ?)
            """, (article['text'], article['label'], article['article_url']))
            count += 1
        except Exception as e:
            print(f"[ERROR] Could not insert article: {article['article_url']} -> {e}")
    conn.commit()
    print(f"{count} articles processed into database.")

# ---------------- MAIN ----------------
def main():
    print("Scraping REAL news sources...")
    real_articles = scrape_all(real_sources, "real")
    print("Scraping FAKE news sources...")
    fake_articles = scrape_all(fake_sources, "fake")

    # Combine and remove duplicates by article_url
    all_articles = real_articles + fake_articles
    unique_articles = {a['article_url']: a for a in all_articles}.values()
    unique_articles = list(unique_articles)

    # Insert directly into DB
    insert_articles_to_db(unique_articles)
    print("Scraping, cleaning, and DB insertion complete!")

if __name__ == "__main__":
    main()
    conn.close()
