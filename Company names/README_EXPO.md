# Expo Stand Prioritiser — Built on Your Existing Tool

This adds an expo-specific ranking layer on top of your existing scraper outputs.

It uses:

- `hardware_pioneers_swapcard_links_extracted.csv` — company names, stand numbers, Swapcard profile URLs
- `scraped_results.csv` — scraped profile text from each exhibitor page
- `expo_ranker.py` — scoring engine
- `expo_app.py` — small local browser app
- `floorplan_mapper.py` — optional floorplan overlay once you add stand coordinates

## What it does

It ranks exhibitors based on your target keywords, for example:

- machine learning
- edge AI
- embedded systems
- FPGA
- robotics
- computer vision
- Python/C++
- graduate/internship signals

It exports:

- `outputs/ranked_exhibitors.csv` — all exhibitors ranked
- `outputs/visit_plan.csv` — top 20 stands to visit first
- `outputs/keyword_summary.csv` — which keywords appeared most often

## Recommended VS Code workflow

Open the folder `Company names` in VS Code.

Run `expo_ranker.py` directly using the VS Code Python play button.

That creates the CSV outputs in the `outputs` folder.

For a browser interface, run `expo_app.py`, then open:

```text
http://127.0.0.1:5051
```

## How the scoring works

The score combines two ideas:

1. **Weighted keyword matching**  
   Example: `edge ai`, `fpga`, and `embedded systems` are worth more than generic words like `data`.

2. **TF-IDF similarity**  
   The app compares each exhibitor profile against your target profile using TF-IDF. This helps detect relevant text even when exact keyword matches are not perfect.

So this is not random AI fluff. It is an explainable relevance ranking system.

## What to change first

Open `expo_ranker.py` and edit:

```python
DEFAULT_TARGET_PROFILE
DEFAULT_KEYWORDS
CATEGORY_WEIGHTS
```

That is where you tune the app for different events or roles.

## Floorplan mapping

The ranking works now. The floorplan overlay needs one extra file: coordinates.

Create or edit:

```text
floorplan_stands_template.csv
```

Format:

```csv
company,stand_or_location,x,y,notes
Example Company,Stand A1,100,200,Replace with real coordinates
```

Once you have a floorplan image, call:

```python
from floorplan_mapper import plot_floorplan
plot_floorplan("floorplan.png")
```

This creates:

```text
outputs/floorplan_ranked_overlay.png
```

## Important limitation

The current floorplan is not included in the ZIP, so I cannot accurately map physical stand positions yet. The ranking and visit plan are working; the visual route/floorplan step comes after you provide the floorplan image/PDF or coordinate data.
