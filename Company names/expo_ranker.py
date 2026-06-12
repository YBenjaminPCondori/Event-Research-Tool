"""
Expo Relevance Ranker
---------------------
Turns scraped exhibitor/profile text into a ranked expo visit plan.

Designed for the current project files:
- hardware_pioneers_swapcard_links_extracted.csv
- scraped_results.csv

Run from VS Code/Jupyter or directly with Python. It exports:
- outputs/ranked_exhibitors.csv
- outputs/visit_plan.csv
- outputs/keyword_summary.csv
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover - fallback for very minimal installs
    TfidfVectorizer = None
    cosine_similarity = None


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_EXHIBITOR_CSV = BASE_DIR / "hardware_pioneers_swapcard_links_extracted.csv"
DEFAULT_SCRAPED_CSV = BASE_DIR / "scraped_results.csv"
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs"


# Weighted keywords: tweak these for your target event/career goal.
# Higher keyword weights = stronger signal.
DEFAULT_KEYWORDS: Dict[str, Dict[str, float]] = {
    "ai_ml": {
        "artificial intelligence": 6,
        "machine learning": 6,
        "edge ai": 7,
        "tinyml": 7,
        "deep learning": 5,
        "computer vision": 6,
        "neural network": 4,
        "tensorflow": 4,
        "pytorch": 4,
        "keras": 3,
        "nlp": 3,
        "llm": 3,
        "ai": 2,
        "ml": 2,
    },
    "embedded_hardware": {
        "embedded systems": 7,
        "embedded": 5,
        "firmware": 5,
        "fpga": 6,
        "vhdl": 5,
        "verilog": 5,
        "asic": 6,
        "semiconductor": 5,
        "microcontroller": 5,
        "mcu": 4,
        "pcb": 4,
        "electronics": 4,
        "sensor": 4,
        "sensors": 4,
        "iot": 4,
        "edge computing": 5,
        "hardware": 3,
    },
    "robotics_autonomy": {
        "robotics": 7,
        "robot": 5,
        "autonomous": 5,
        "autonomy": 5,
        "navigation": 3,
        "perception": 4,
        "sensor fusion": 5,
        "automation": 4,
        "control systems": 4,
    },
    "software_data": {
        "python": 4,
        "c++": 4,
        "java": 3,
        "linux": 3,
        "api": 3,
        "cloud": 3,
        "data": 2,
        "dashboard": 3,
        "analytics": 3,
        "software": 3,
        "web": 2,
    },
    "career_signal": {
        "graduate": 7,
        "internship": 7,
        "intern": 5,
        "placement": 5,
        "entry level": 6,
        "junior": 5,
        "early career": 6,
        "hiring": 5,
        "careers": 4,
        "join our team": 5,
        "open positions": 5,
        "vacancies": 5,
        "apply": 3,
    },
}

CATEGORY_WEIGHTS = {
    "ai_ml": 1.30,
    "embedded_hardware": 1.35,
    "robotics_autonomy": 1.25,
    "software_data": 1.00,
    "career_signal": 1.15,
}

DEFAULT_TARGET_PROFILE = """
machine learning, artificial intelligence, edge ai, embedded systems, fpga,
firmware, robotics, computer vision, sensors, python, c++, linux, graduate,
internship, software engineering, data, automation
""".strip()


@dataclass
class ScoreConfig:
    keywords: Dict[str, Dict[str, float]]
    category_weights: Dict[str, float]
    target_profile: str = DEFAULT_TARGET_PROFILE
    tfidf_weight: float = 35.0
    keyword_weight: float = 1.0
    company_name_bonus: float = 0.0  # kept for future use


def normalise_text(value: object) -> str:
    """Lowercase, compact whitespace, and keep simple technical symbols."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    text = str(value)
    text = text.replace("/", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def keyword_regex(keyword: str) -> re.Pattern:
    """
    Phrase-aware regex.
    - Uses word boundaries for normal words.
    - Handles terms such as c++, fpga, ai without matching inside random words.
    """
    kw = re.escape(keyword.lower().strip())
    return re.compile(rf"(?<![a-z0-9]){kw}(?![a-z0-9])", re.IGNORECASE)


def count_keyword_hits(text: str, keywords: Dict[str, Dict[str, float]]) -> Tuple[Dict[str, float], Dict[str, List[str]], Dict[str, int]]:
    """Return weighted category scores, matched keywords, and raw keyword counts."""
    category_scores: Dict[str, float] = {}
    category_matches: Dict[str, List[str]] = {}
    raw_counts: Dict[str, int] = {}

    for category, terms in keywords.items():
        score = 0.0
        matches: List[str] = []
        for term, weight in terms.items():
            n = len(keyword_regex(term).findall(text))
            if n > 0:
                # Diminishing return: repeated mentions help, but not infinitely.
                # 1 hit = 1.00x, 2 hits = 1.58x, 4 hits = 2.32x, etc.
                hit_score = weight * math.log1p(n) / math.log(2)
                score += hit_score
                matches.append(term)
                raw_counts[term] = raw_counts.get(term, 0) + n
        category_scores[category] = round(score, 3)
        category_matches[category] = sorted(matches)

    return category_scores, category_matches, raw_counts


def calculate_tfidf_scores(texts: Sequence[str], target_profile: str) -> List[float]:
    """Cosine similarity between each exhibitor text and the target profile."""
    if not texts:
        return []

    if TfidfVectorizer is None or cosine_similarity is None:
        return [0.0 for _ in texts]

    corpus = list(texts) + [normalise_text(target_profile)]
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 3),
        min_df=1,
        max_features=6000,
    )
    matrix = vectorizer.fit_transform(corpus)
    target_vec = matrix[-1]
    doc_vecs = matrix[:-1]
    sims = cosine_similarity(doc_vecs, target_vec).ravel()
    return [round(float(s) * 100, 3) for s in sims]


def relevance_label(score: float) -> str:
    if score >= 55:
        return "High"
    if score >= 25:
        return "Medium"
    if score > 0:
        return "Low"
    return "No clear match"


def load_and_merge_data(
    exhibitor_csv: Path = DEFAULT_EXHIBITOR_CSV,
    scraped_csv: Path = DEFAULT_SCRAPED_CSV,
) -> pd.DataFrame:
    """Load exhibitor metadata and scraped profile text, then merge by profile URL."""
    exhibitors = pd.read_csv(exhibitor_csv)
    scraped = pd.read_csv(scraped_csv)

    # Standardise expected column names without breaking your original CSVs.
    if "profile_url" not in exhibitors.columns:
        raise ValueError("exhibitor CSV must contain a 'profile_url' column")
    if "url" not in scraped.columns:
        raise ValueError("scraped CSV must contain a 'url' column")

    merged = exhibitors.merge(scraped, how="left", left_on="profile_url", right_on="url")

    for col in ["company", "stand_or_location", "page_title", "extracted_text", "profile_url"]:
        if col not in merged.columns:
            merged[col] = ""

    merged["combined_text"] = (
        merged["company"].fillna("").astype(str)
        + " | "
        + merged["stand_or_location"].fillna("").astype(str)
        + " | "
        + merged["page_title"].fillna("").astype(str)
        + " | "
        + merged["extracted_text"].fillna("").astype(str)
    )
    merged["clean_text"] = merged["combined_text"].apply(normalise_text)
    return merged


def score_exhibitors(
    exhibitor_csv: Path = DEFAULT_EXHIBITOR_CSV,
    scraped_csv: Path = DEFAULT_SCRAPED_CSV,
    config: Optional[ScoreConfig] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Score exhibitors and return (ranked_dataframe, keyword_summary_dataframe)."""
    config = config or ScoreConfig(DEFAULT_KEYWORDS, CATEGORY_WEIGHTS)
    df = load_and_merge_data(exhibitor_csv, scraped_csv)

    tfidf_scores = calculate_tfidf_scores(df["clean_text"].tolist(), config.target_profile)

    rows = []
    all_keyword_counts: Counter = Counter()

    for idx, row in df.iterrows():
        text = row["clean_text"]
        cat_scores, cat_matches, raw_counts = count_keyword_hits(text, config.keywords)
        all_keyword_counts.update(raw_counts)

        weighted_keyword_score = 0.0
        for category, value in cat_scores.items():
            weighted_keyword_score += value * config.category_weights.get(category, 1.0)

        tfidf_score = tfidf_scores[idx] if idx < len(tfidf_scores) else 0.0
        final_score = (weighted_keyword_score * config.keyword_weight) + (tfidf_score / 100.0 * config.tfidf_weight)

        matched_flat = sorted({term for terms in cat_matches.values() for term in terms})
        matched_by_category = "; ".join(
            f"{cat}: {', '.join(terms)}" for cat, terms in cat_matches.items() if terms
        )

        rows.append({
            "company": row.get("company", ""),
            "stand_or_location": row.get("stand_or_location", ""),
            "profile_url": row.get("profile_url", ""),
            "website_or_contact": extract_first_url(str(row.get("extracted_text", ""))),
            "page_title": row.get("page_title", ""),
            "status": row.get("status", ""),
            "final_score": round(final_score, 3),
            "keyword_score": round(weighted_keyword_score, 3),
            "tfidf_similarity_0_100": tfidf_score,
            "relevance": relevance_label(final_score),
            "matched_keywords": ", ".join(matched_flat),
            "matched_by_category": matched_by_category,
            "text_preview": str(row.get("extracted_text", ""))[:500],
            **{f"score_{cat}": cat_scores.get(cat, 0.0) for cat in config.keywords},
        })

    ranked = pd.DataFrame(rows).sort_values(
        by=["final_score", "keyword_score", "tfidf_similarity_0_100"],
        ascending=False,
    ).reset_index(drop=True)
    ranked.insert(0, "rank", range(1, len(ranked) + 1))

    keyword_summary = pd.DataFrame(
        [{"keyword": k, "count": v} for k, v in all_keyword_counts.most_common()]
    )
    return ranked, keyword_summary


def extract_first_url(text: str) -> str:
    match = re.search(r"https?://[^\s|]+", text or "")
    return match.group(0) if match else ""


def export_outputs(
    ranked: pd.DataFrame,
    keyword_summary: pd.DataFrame,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    top_n: int = 20,
) -> Tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked_path = output_dir / "ranked_exhibitors.csv"
    visit_plan_path = output_dir / "visit_plan.csv"
    keyword_summary_path = output_dir / "keyword_summary.csv"

    ranked.to_csv(ranked_path, index=False)
    ranked.head(top_n).to_csv(visit_plan_path, index=False)
    keyword_summary.to_csv(keyword_summary_path, index=False)
    return ranked_path, visit_plan_path, keyword_summary_path


def main() -> None:
    ranked, keyword_summary = score_exhibitors()
    paths = export_outputs(ranked, keyword_summary)

    print("\nTop 15 exhibitors to visit:\n")
    cols = ["rank", "company", "stand_or_location", "final_score", "relevance", "matched_keywords"]
    print(ranked[cols].head(15).to_string(index=False))

    print("\nSaved outputs:")
    for path in paths:
        print(f"- {path}")


if __name__ == "__main__":
    main()
