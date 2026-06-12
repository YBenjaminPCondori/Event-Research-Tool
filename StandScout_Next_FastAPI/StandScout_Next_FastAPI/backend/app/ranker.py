from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
EXHIBITORS_CSV = DATA_DIR / "exhibitors_enriched.csv"
IMG_WIDTH = 1344
IMG_HEIGHT = 2048
ENTRANCE = {"x": 687.0, "y": 1695.0, "label": "Entrance / start"}

DEFAULT_QUERY = (
    "machine learning, AI, edge AI, embedded systems, FPGA, firmware, robotics, "
    "computer vision, IoT, sensors, Python, Linux, graduate, internship"
)

PRESETS = {
    "ai": "AI, machine learning, edge AI, tinyML, computer vision, neural networks, inference, data",
    "embedded": "embedded systems, firmware, FPGA, microcontroller, PCB, semiconductor, sensors, C++, Linux",
    "robotics": "robotics, autonomous systems, automation, control systems, sensor fusion, computer vision",
    "jobs": "graduate, internship, junior, early career, hiring, careers, placement, software engineer",
    "suppliers": "components, distributor, electronics, PCB, sensors, connectors, manufacturing, supply chain",
}

CATEGORY_ALIASES = {
    "ai_ml": ["ai", "artificial intelligence", "machine learning", "edge ai", "tinyml", "computer vision", "neural network", "tensorflow", "pytorch", "ml"],
    "embedded_hardware": ["embedded", "embedded systems", "firmware", "fpga", "vhdl", "verilog", "asic", "semiconductor", "microcontroller", "mcu", "pcb", "electronics", "sensor", "sensors", "iot", "edge computing", "hardware"],
    "robotics_autonomy": ["robotics", "robot", "autonomous", "autonomy", "navigation", "perception", "sensor fusion", "automation", "control systems"],
    "software_data": ["python", "c++", "java", "linux", "api", "cloud", "data", "dashboard", "analytics", "software", "web"],
    "career_signal": ["graduate", "internship", "intern", "placement", "entry level", "junior", "early career", "hiring", "careers", "join our team", "open positions", "vacancies", "apply"],
}

CATEGORY_LABELS = {
    "ai_ml": "AI / machine learning",
    "embedded_hardware": "embedded hardware",
    "robotics_autonomy": "robotics / automation",
    "software_data": "software / data",
    "career_signal": "jobs / hiring",
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value)


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", clean(value).lower()).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def split_terms(query: str) -> list[str]:
    terms = []
    for part in re.split(r"[,;\n]+", query or ""):
        part = re.sub(r"\s+", " ", part).strip().lower()
        if part and part not in terms:
            terms.append(part)
    return terms


def term_count(text: str, term: str) -> int:
    text = norm(text)
    term = norm(term)
    if not term:
        return 0
    # Phrase match for multi-word terms.
    if " " in term:
        return len(re.findall(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text))
    # Exact-ish token match, with a controlled substring match for longer technical terms.
    tokens = re.findall(r"[a-z0-9+#.]+", text)
    return sum(1 for token in tokens if token == term or (len(term) >= 4 and term in token))


def label_priority(rank: int, match_percent: int) -> dict[str, str]:
    if rank <= 5 or match_percent >= 74:
        return {"key": "visit", "label": "Visit first"}
    if rank <= 15 or match_percent >= 42:
        return {"key": "worth", "label": "Worth visiting"}
    return {"key": "backup", "label": "Backup"}


@lru_cache(maxsize=1)
def load_exhibitors() -> pd.DataFrame:
    df = pd.read_csv(EXHIBITORS_CSV).fillna("")
    # Keep column names stable for the API.
    for col in [
        "company", "stand_or_location", "stand_code", "profile_url", "website", "text",
        "matched_keywords", "matched_by_category", "relevance", "x", "y", "zone",
        "final_score", "score_ai_ml", "score_embedded_hardware", "score_robotics_autonomy",
        "score_software_data", "score_career_signal", "logo_original_url",
    ]:
        if col not in df.columns:
            df[col] = ""
    return df


def category_hints(row: pd.Series) -> list[str]:
    hints = []
    for key, label in CATEGORY_LABELS.items():
        if safe_float(row.get(f"score_{key}")) > 0:
            hints.append(label)
    return hints


def score_row(row: pd.Series, terms: list[str], mode: str) -> tuple[float, list[str]]:
    if mode == "prepared":
        return safe_float(row.get("final_score")), []

    text = " ".join([
        clean(row.get("company")),
        clean(row.get("stand_or_location")),
        clean(row.get("matched_keywords")),
        clean(row.get("matched_by_category")),
        clean(row.get("text")),
    ])
    exact_score = 0.0
    matched: list[str] = []

    for term in terms:
        n = term_count(text, term)
        if n:
            phrase_boost = 9.0 if " " in term else 5.0
            exact_score += min(22.0, phrase_boost + n * 2.2)
            matched.append(term)

    # If user says "AI" or "embedded", also boost related categories.
    category_boost = 0.0
    term_text = " ".join(terms)
    for category, aliases in CATEGORY_ALIASES.items():
        if any(alias in term_text for alias in aliases):
            category_boost += safe_float(row.get(f"score_{category}")) / 6.5

    prepared_boost = min(35.0, safe_float(row.get("final_score")) / 2.8)

    if mode == "strict":
        score = exact_score + prepared_boost * 0.2
    else:
        score = exact_score + category_boost + prepared_boost
    return score, matched


def build_reason(row: pd.Series, matched: list[str]) -> str:
    if matched:
        return "Matches your search: " + ", ".join(matched[:8])
    matched_keywords = clean(row.get("matched_keywords"))
    if matched_keywords:
        return "Relevant event profile keywords: " + matched_keywords
    hints = category_hints(row)
    if hints:
        return "Relevant categories: " + ", ".join(hints)
    return "Included from the prepared exhibitor profile and event data."


def to_result(row: pd.Series, score: float, rank: int, match_percent: int, matched: list[str]) -> dict[str, Any]:
    pr = label_priority(rank, match_percent)
    x = safe_float(row.get("x"), default=float("nan"))
    y = safe_float(row.get("y"), default=float("nan"))
    return {
        "rank": rank,
        "company": clean(row.get("company")),
        "stand": clean(row.get("stand_or_location")),
        "standCode": clean(row.get("stand_code")),
        "zone": clean(row.get("zone")),
        "profileUrl": clean(row.get("profile_url")),
        "website": clean(row.get("website")),
        "logoUrl": clean(row.get("logo_original_url")),
        "score": round(float(score), 3),
        "matchPercent": match_percent,
        "priority": pr,
        "matchedTerms": matched,
        "reason": build_reason(row, matched),
        "baseRelevance": clean(row.get("relevance")),
        "matchedKeywords": clean(row.get("matched_keywords")),
        "categoryHints": category_hints(row),
        "textPreview": clean(row.get("text"))[:420],
        "x": None if math.isnan(x) else x,
        "y": None if math.isnan(y) else y,
        "mapped": not math.isnan(x) and not math.isnan(y),
    }


def build_route(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remaining = [dict(item) for item in items if isinstance(item.get("x"), (int, float)) and isinstance(item.get("y"), (int, float))]
    current = {"x": ENTRANCE["x"], "y": ENTRANCE["y"]}
    route = []
    step = 1
    while remaining:
        best_i = min(
            range(len(remaining)),
            key=lambda i: (remaining[i]["x"] - current["x"]) ** 2 + (remaining[i]["y"] - current["y"]) ** 2,
        )
        item = remaining.pop(best_i)
        distance = math.hypot(item["x"] - current["x"], item["y"] - current["y"])
        route.append({
            "step": step,
            "rank": item["rank"],
            "company": item["company"],
            "stand": item["stand"],
            "x": item["x"],
            "y": item["y"],
            "distancePx": round(distance, 1),
        })
        current = {"x": item["x"], "y": item["y"]}
        step += 1
    return route


def rank_exhibitors(query: str | None = None, top_n: int = 20, mode: str = "balanced") -> dict[str, Any]:
    df = load_exhibitors()
    query = query or DEFAULT_QUERY
    mode = mode if mode in {"balanced", "strict", "prepared"} else "balanced"
    top_n = max(1, min(int(top_n or 20), 50))
    terms = split_terms(query)
    if not terms and mode != "prepared":
        terms = split_terms(DEFAULT_QUERY)

    scored = []
    for _, row in df.iterrows():
        score, matched = score_row(row, terms, mode)
        if score > 0 or mode == "prepared":
            scored.append((score, matched, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    scored = scored[:top_n]
    max_score = max([s for s, _, _ in scored] + [1.0])

    results = []
    for i, (score, matched, row) in enumerate(scored, start=1):
        match_percent = max(1, min(99, round((score / max_score) * 96)))
        results.append(to_result(row, score, i, match_percent, matched))

    route = build_route(results[:20])
    visit_first = sum(1 for item in results if item["priority"]["key"] == "visit")
    mapped = sum(1 for item in results if item["mapped"])

    return {
        "event": {
            "name": "Hardware Pioneers MAX 26",
            "floorplanImage": "/floorplan_hardware_pioneers_max26.png",
            "imageWidth": IMG_WIDTH,
            "imageHeight": IMG_HEIGHT,
            "entrance": ENTRANCE,
        },
        "query": query,
        "mode": mode,
        "topN": top_n,
        "summary": {
            "exhibitorsAnalysed": int(len(df)),
            "resultsShown": len(results),
            "mappedResults": mapped,
            "visitFirst": visit_first,
            "topCompany": results[0]["company"] if results else "",
            "topStand": results[0]["stand"] if results else "",
        },
        "results": results,
        "route": route,
    }
