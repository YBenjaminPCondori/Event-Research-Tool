"""
Optional floorplan overlay tool.

Use this after you have a floorplan image and a stand coordinate CSV.
The coordinate CSV should contain:
company, stand_or_location, x, y

This script outputs outputs/floorplan_ranked_overlay.png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"


def plot_floorplan(
    floorplan_image: str | Path,
    ranked_csv: str | Path = OUTPUT_DIR / "ranked_exhibitors.csv",
    coordinates_csv: str | Path = BASE_DIR / "floorplan_stands_template.csv",
    output_path: str | Path = OUTPUT_DIR / "floorplan_ranked_overlay.png",
    top_n: int = 20,
):
    floorplan_image = Path(floorplan_image)
    ranked_csv = Path(ranked_csv)
    coordinates_csv = Path(coordinates_csv)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not floorplan_image.exists():
        raise FileNotFoundError(f"Floorplan image not found: {floorplan_image}")
    if not ranked_csv.exists():
        raise FileNotFoundError(f"Ranked CSV not found: {ranked_csv}. Run expo_ranker.py first.")
    if not coordinates_csv.exists():
        raise FileNotFoundError(f"Coordinates CSV not found: {coordinates_csv}")

    ranked = pd.read_csv(ranked_csv)
    coords = pd.read_csv(coordinates_csv)

    required = {"company", "stand_or_location", "x", "y"}
    missing = required - set(coords.columns)
    if missing:
        raise ValueError(f"coordinates CSV missing columns: {missing}")

    # Prefer matching by stand. Company names can vary slightly.
    merged = ranked.merge(coords, on="stand_or_location", how="inner", suffixes=("", "_coord"))
    merged = merged.sort_values("rank").head(top_n)

    img = plt.imread(str(floorplan_image))
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.imshow(img)
    ax.axis("off")

    for _, row in merged.iterrows():
        rank = int(row["rank"])
        x, y = float(row["x"]), float(row["y"])
        score = float(row["final_score"])
        label = f"{rank}. {row['stand_or_location']}"

        # Marker size scales with relevance score but stays readable.
        size = max(80, min(450, score * 5))
        ax.scatter([x], [y], s=size, alpha=0.75)
        ax.text(x + 8, y - 8, label, fontsize=9, weight="bold")

    ax.set_title(f"Top {top_n} ranked expo stands", fontsize=16, weight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


if __name__ == "__main__":
    print("This is optional. Add your floorplan image path, then call plot_floorplan('floorplan.png').")
