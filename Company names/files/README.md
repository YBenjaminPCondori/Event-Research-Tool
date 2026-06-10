# Site Scraper & Relevance Ranker

A local web app that scrapes URLs from a CSV or paste-in list, crawls up to 5 layers deep, scores each page against keyword categories, and ranks sites by relevance.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open **http://localhost:5050** in your browser.

## Usage

1. Paste URLs (one per line) into the sidebar — or read from a CSV and paste the column
2. Set crawl depth (0 = homepage only, up to 5 layers)
3. Hit **Start scraping**
4. Watch results populate and rank in real time
5. Click any site card to expand individual pages
6. Export to CSV when done

## Keyword categories

Defined in `app.py` under `DEFAULT_KEYWORDS`. Four categories out of the box:

- **role_fit** — graduate, internship, junior, entry level, etc.
- **tech_stack** — AI, ML, Python, PyTorch, LLM, etc.
- **hardware** — semiconductor, FPGA, embedded, PCB, etc.
- **company_signals** — hiring, careers, open positions, etc.

Edit the lists in `app.py` to match your search.

## Notes

- Max 80 pages per site (configurable via `MAX_PAGES_PER_SITE` in `app.py`)
- 0.4s delay between requests to be polite to servers
- Stays within the same domain per starting URL
- Scoring is pure keyword frequency — no ML, no LLM
