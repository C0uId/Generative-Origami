from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class TargetSpec:
    query: str
    canonical_name: str
    family: str
    parameters: dict[str, float]
    semantic_confidence: float
    semantic_source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class ValidationReport:
    passed: bool
    level: str
    checks: list[dict[str, Any]]
    certified_finished_model: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)