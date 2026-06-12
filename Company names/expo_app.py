"""
Small local Flask app for the expo prioritiser.

Run this file from VS Code, then open:
http://127.0.0.1:5051

This app uses the existing CSVs in this folder and lets you edit the target profile.
"""

from __future__ import annotations

import html
from pathlib import Path

from flask import Flask, Response, request, send_file

from expo_ranker import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_TARGET_PROFILE,
    ScoreConfig,
    DEFAULT_KEYWORDS,
    CATEGORY_WEIGHTS,
    export_outputs,
    score_exhibitors,
)

app = Flask(__name__)

LAST_RANKED_PATH = DEFAULT_OUTPUT_DIR / "ranked_exhibitors.csv"
LAST_VISIT_PLAN_PATH = DEFAULT_OUTPUT_DIR / "visit_plan.csv"

PAGE_CSS = """
:root { font-family: Inter, Arial, sans-serif; color: #0f172a; background: #f8fafc; }
body { margin: 0; }
.container { max-width: 1180px; margin: 0 auto; padding: 28px; }
.hero { background: #0f172a; color: white; padding: 28px; border-radius: 22px; margin-bottom: 20px; }
.hero h1 { margin: 0 0 8px; font-size: 32px; }
.hero p { margin: 0; color: #cbd5e1; }
.card { background: white; border: 1px solid #e2e8f0; border-radius: 18px; padding: 18px; margin-bottom: 18px; box-shadow: 0 12px 30px rgba(15,23,42,0.05); }
textarea { width: 100%; min-height: 115px; border: 1px solid #cbd5e1; border-radius: 12px; padding: 12px; font-size: 14px; }
button, .btn { background: #0f172a; color: white; padding: 10px 14px; border-radius: 12px; border: 0; text-decoration: none; display: inline-block; cursor: pointer; }
.btn.secondary { background: #334155; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 10px; border-bottom: 1px solid #e2e8f0; vertical-align: top; text-align: left; }
th { background: #f1f5f9; position: sticky; top: 0; }
.badge { padding: 4px 8px; border-radius: 999px; font-weight: 700; font-size: 12px; }
.High { background: #dcfce7; color: #166534; }
.Medium { background: #fef3c7; color: #92400e; }
.Low { background: #e0f2fe; color: #075985; }
.No { background: #f1f5f9; color: #475569; }
.small { color: #64748b; font-size: 12px; }
.actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
"""


def render_page(target_profile: str = DEFAULT_TARGET_PROFILE, table_html: str = "", message: str = "") -> str:
    safe_profile = html.escape(target_profile)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Expo Stand Prioritiser</title>
  <style>{PAGE_CSS}</style>
</head>
<body>
  <div class="container">
    <section class="hero">
      <h1>Expo Stand Prioritiser</h1>
      <p>Ranks exhibitors by relevance to your target skills, then exports a visit plan.</p>
    </section>

    <section class="card">
      <form method="post" action="/rank">
        <label><strong>Your target keywords / career profile</strong></label>
        <p class="small">Edit this depending on the expo. Higher relevance = companies to visit first.</p>
        <textarea name="target_profile">{safe_profile}</textarea>
        <div class="actions">
          <button type="submit">Rank exhibitors</button>
          <a class="btn secondary" href="/download/ranked">Download ranked CSV</a>
          <a class="btn secondary" href="/download/visit-plan">Download visit plan</a>
        </div>
      </form>
    </section>

    {f'<section class="card"><strong>{html.escape(message)}</strong></section>' if message else ''}
    {table_html}
  </div>
</body>
</html>"""


def build_table(ranked) -> str:
    rows = []
    for _, r in ranked.head(50).iterrows():
        relevance_class = str(r["relevance"]).split()[0]
        rows.append(
            "<tr>"
            f"<td><strong>{int(r['rank'])}</strong></td>"
            f"<td><strong>{html.escape(str(r['company']))}</strong><br><span class='small'>{html.escape(str(r['page_title']))}</span></td>"
            f"<td>{html.escape(str(r['stand_or_location']))}</td>"
            f"<td><strong>{float(r['final_score']):.1f}</strong><br><span class='small'>TF-IDF: {float(r['tfidf_similarity_0_100']):.1f}</span></td>"
            f"<td><span class='badge {relevance_class}'>{html.escape(str(r['relevance']))}</span></td>"
            f"<td>{html.escape(str(r['matched_keywords']))}</td>"
            "</tr>"
        )
    return """
    <section class="card">
      <h2>Ranked exhibitors</h2>
      <div style="overflow:auto; max-height: 720px;">
      <table>
        <thead>
          <tr><th>Rank</th><th>Company</th><th>Stand</th><th>Score</th><th>Relevance</th><th>Matched keywords</th></tr>
        </thead>
        <tbody>
    """ + "\n".join(rows) + """
        </tbody>
      </table>
      </div>
    </section>
    """


@app.route("/", methods=["GET"])
def index() -> str:
    return render_page()


@app.route("/rank", methods=["POST"])
def rank() -> str:
    target_profile = request.form.get("target_profile", DEFAULT_TARGET_PROFILE).strip()
    config = ScoreConfig(DEFAULT_KEYWORDS, CATEGORY_WEIGHTS, target_profile=target_profile)
    ranked, keyword_summary = score_exhibitors(config=config)
    export_outputs(ranked, keyword_summary)
    table_html = build_table(ranked)
    return render_page(target_profile, table_html, "Ranking complete. CSV outputs saved in the outputs folder.")


@app.route("/download/<kind>", methods=["GET"])
def download(kind: str):
    path = LAST_VISIT_PLAN_PATH if kind == "visit-plan" else LAST_RANKED_PATH
    if not path.exists():
        ranked, keyword_summary = score_exhibitors()
        export_outputs(ranked, keyword_summary)
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=False, port=5051)
