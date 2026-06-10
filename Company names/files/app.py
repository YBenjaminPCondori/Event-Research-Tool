from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests as req
from bs4 import BeautifulSoup
import pandas as pd
import threading
import time
import re
import uuid
import os
from collections import deque
from urllib.parse import urljoin, urlparse
import math

app = Flask(__name__, static_folder=".")
CORS(app)

REQUEST_DELAY = 0.4
MAX_PAGES_PER_SITE = 80

jobs = {}

DEFAULT_KEYWORDS = {
    "role_fit": [
        "graduate", "internship", "entry level", "junior", "placement",
        "trainee", "apprentice", "new grad", "early career"
    ],
    "tech_stack": [
        "artificial intelligence", "machine learning", "data science",
        "deep learning", "computer vision", "nlp", "python", "pytorch",
        "tensorflow", "llm", "neural network", "robotics", "automation"
    ],
    "hardware": [
        "hardware", "semiconductor", "chip", "fpga", "embedded", "firmware",
        "asic", "pcb", "electronics", "sensor", "iot", "edge computing"
    ],
    "company_signals": [
        "hiring", "careers", "join our team", "open positions", "we are looking",
        "apply now", "job opening", "vacancies"
    ]
}

def extract_company_url_from_swapcard(swapcard_url):
    """Try to pull the company website link from a Swapcard exhibitor page."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = req.get(swapcard_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, "html.parser")

        # Look for any external link that isn't swapcard itself
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if (
                href.startswith("http")
                and "swapcard.com" not in href
                and "linkedin.com" not in href
                and "twitter.com" not in href
                and "facebook.com" not in href
            ):
                return href

        # Fallback: check meta tags for website
        for meta in soup.find_all("meta"):
            content = meta.get("content", "")
            if content.startswith("http") and "swapcard.com" not in content:
                return content

        return None
    except Exception:
        return None


def is_swapcard_url(url):
    return "swapcard.com" in url


def clean_text(text):
    if text:
        return re.sub(r'\s+', ' ', text).strip()
    return ""

def score_text(text, keywords_by_category):
    text_lower = text.lower()
    scores = {}
    matches = {}
    total = 0
    for category, kws in keywords_by_category.items():
        found = [kw for kw in kws if kw in text_lower]
        count = len(found)
        scores[category] = count
        matches[category] = found
        total += count
    return scores, matches, total

def scrape_site(start_url, max_depth, job_id, keywords_by_category):
    job = jobs[job_id]
    visited = set()
    queue = deque([(start_url, 0)])
    site_pages = []

    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    while queue and len(visited) < MAX_PAGES_PER_SITE:
        url, depth = queue.popleft()

        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = req.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.content, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()

            page_title = soup.title.get_text(strip=True) if soup.title else url

            elements = soup.find_all(["h1", "h2", "h3", "h4", "p", "li"])
            parts = list(dict.fromkeys(
                clean_text(el.get_text(" ", strip=True))
                for el in elements
                if len(clean_text(el.get_text(" ", strip=True))) > 20
            ))
            text = " | ".join(parts)

            cat_scores, cat_matches, total = score_text(text, keywords_by_category)

            site_pages.append({
                "url": url,
                "depth": depth,
                "title": page_title,
                "text_preview": text[:400],
                "scores": cat_scores,
                "matches": cat_matches,
                "total_score": total,
                "word_count": len(text.split())
            })

            if depth < max_depth:
                for a_tag in soup.find_all("a", href=True):
                    link = urljoin(url, a_tag["href"])
                    parsed_link = urlparse(link)
                    if (
                        parsed_link.netloc == base_domain
                        and link not in visited
                        and "#" not in link
                        and "mailto:" not in link
                        and "tel:" not in link
                        and parsed_link.scheme in ("http", "https")
                    ):
                        queue.append((link, depth + 1))

        except Exception as e:
            pass

        time.sleep(REQUEST_DELAY)

    best_score = max((p["total_score"] for p in site_pages), default=0)
    top_matches = {}
    for page in site_pages:
        for cat, mlist in page["matches"].items():
            if cat not in top_matches:
                top_matches[cat] = set()
            top_matches[cat].update(mlist)
    top_matches = {k: list(v) for k, v in top_matches.items()}

    return {
        "start_url": start_url,
        "pages_scraped": len(site_pages),
        "best_score": best_score,
        "total_score": sum(p["total_score"] for p in site_pages),
        "top_matches": top_matches,
        "pages": site_pages
    }

def run_job(job_id, urls, max_depth, keywords_by_category):
    job = jobs[job_id]
    job["status"] = "running"
    job["total"] = len(urls)
    job["done"] = 0
    job["results"] = []
    job["log"] = []

    for i, url in enumerate(urls):
        if job.get("cancelled"):
            break

        actual_url = url

        # If it's a Swapcard URL, try to extract the real company website first
        if is_swapcard_url(url):
            job["log"].append(f"Resolving Swapcard page {i+1}/{len(urls)}: {url}")
            company_url = extract_company_url_from_swapcard(url)
            if company_url:
                job["log"].append(f"Found company site: {company_url}")
                actual_url = company_url
            else:
                job["log"].append(f"No company site found, scraping Swapcard page directly")
            time.sleep(REQUEST_DELAY)

        job["log"].append(f"Scraping site {i+1}/{len(urls)}: {actual_url}")
        result = scrape_site(actual_url, max_depth, job_id, keywords_by_category)
        result["swapcard_url"] = url if is_swapcard_url(url) else None
        job["results"].append(result)
        job["done"] = i + 1

    job["status"] = "done"

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/start", methods=["POST"])
def start_job():
    data = request.json
    urls = [u.strip() for u in data.get("urls", []) if u.strip()]
    max_depth = min(int(data.get("max_depth", 2)), 5)
    custom_kw = data.get("keywords", None)
    keywords_by_category = custom_kw if custom_kw else DEFAULT_KEYWORDS

    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "queued", "total": 0, "done": 0, "results": [], "log": []}

    t = threading.Thread(target=run_job, args=(job_id, urls, max_depth, keywords_by_category))
    t.daemon = True
    t.start()

    return jsonify({"job_id": job_id})

@app.route("/status/<job_id>")
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status": job["status"],
        "total": job["total"],
        "done": job["done"],
        "log": job["log"][-5:],
        "results": job["results"]
    })

@app.route("/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id):
    job = jobs.get(job_id)
    if job:
        job["cancelled"] = True
    return jsonify({"ok": True})

@app.route("/keywords/defaults")
def get_defaults():
    return jsonify(DEFAULT_KEYWORDS)

if __name__ == "__main__":
    app.run(debug=False, port=5050, threaded=True)
