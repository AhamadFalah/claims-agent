"""Dependency container — one object holds every external client + the repo."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.integrations.attio import AttioClient
from app.persistence.repo import ClaimRepo


@dataclass
class Deps:
    repo: ClaimRepo = field(default_factory=ClaimRepo)
    attio: AttioClient = field(default_factory=AttioClient)


_deps: Deps | None = None


def get_deps() -> Deps:
    global _deps
    if _deps is None:
        _deps = Deps()
    return _deps
