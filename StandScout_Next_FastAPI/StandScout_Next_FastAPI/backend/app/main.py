from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .ranker import DATA_DIR, PRESETS, rank_exhibitors, load_exhibitors

app = FastAPI(
    title="StandScout API",
    version="1.0.0",
    description="Python ranking API for the StandScout expo visit planner.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RankRequest(BaseModel):
    query: str = Field(default="", description="Plain-English interests or comma-separated keywords.")
    top_n: int = Field(default=20, ge=1, le=50)
    mode: str = Field(default="balanced", pattern="^(balanced|strict|prepared)$")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "StandScout API"}


@app.get("/api/presets")
def presets() -> dict[str, str]:
    return PRESETS


@app.get("/api/exhibitors")
def exhibitors(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, object]:
    df = load_exhibitors().head(limit)
    cols = ["company", "stand_or_location", "website", "matched_keywords", "x", "y"]
    return {"count": len(df), "items": df[cols].to_dict(orient="records")}


@app.post("/api/rank")
def rank(payload: RankRequest) -> dict[str, object]:
    return rank_exhibitors(query=payload.query, top_n=payload.top_n, mode=payload.mode)


@app.get("/api/rank")
def rank_get(
    query: str = "",
    top_n: int = Query(default=20, ge=1, le=50),
    mode: str = Query(default="balanced", pattern="^(balanced|strict|prepared)$"),
) -> dict[str, object]:
    return rank_exhibitors(query=query, top_n=top_n, mode=mode)


@app.get("/floorplan_hardware_pioneers_max26.png")
def floorplan() -> FileResponse:
    path = Path(DATA_DIR) / "floorplan_hardware_pioneers_max26.png"
    return FileResponse(path)
