"""Config loaders for channels and outcome codes."""

from __future__ import annotations

import os
from functools import lru_cache

import yaml

from app.domain.claim import Channel

_DIR = os.path.dirname(__file__)


@lru_cache
def load_channels() -> dict[str, Channel]:
    with open(os.path.join(_DIR, "channels.yaml")) as f:
        raw = yaml.safe_load(f)
    return {c["id"]: Channel(**c) for c in raw["channels"]}


@lru_cache
def load_outcomes() -> dict:
    with open(os.path.join(_DIR, "outcomes.yaml")) as f:
        return yaml.safe_load(f)


def channel_for(channel_id: str) -> Channel:
    return load_channels()[channel_id]
