"""Minima/Mubit model routing — pick the cheapest model that clears the bar.

Returns a default model id when MUBIT_API_KEY is unset so the pipeline runs.
"""

from __future__ import annotations

import os

_DEFAULT = "gemini-2.5-flash"


def recommend_model(task: str) -> tuple[str, str | None]:
    """Return (model_id, recommendation_id). recommendation_id is None in fallback."""
    api_key = os.getenv("MUBIT_API_KEY")
    if not api_key:
        return os.getenv("GEMINI_MODEL", _DEFAULT), None
    try:
        from minima_client import MinimaClient

        with MinimaClient("https://api.minima.sh", api_key=api_key) as minima:
            rec = minima.recommend(task, cost_quality_tradeoff=3)
            return rec.recommended_model.model_id, rec.recommendation_id
    except Exception:
        return os.getenv("GEMINI_MODEL", _DEFAULT), None


def send_feedback(recommendation_id: str | None, model_id: str, **kwargs) -> None:
    if not recommendation_id or not os.getenv("MUBIT_API_KEY"):
        return
    try:
        from minima_client import MinimaClient

        with MinimaClient("https://api.minima.sh", api_key=os.environ["MUBIT_API_KEY"]) as minima:
            minima.feedback(recommendation_id, model_id, "success", **kwargs)
    except Exception:
        pass
