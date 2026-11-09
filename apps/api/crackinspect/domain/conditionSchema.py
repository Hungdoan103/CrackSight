from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Decision = Literal["supported", "unresolved"]
PmAction = Literal["resolve", "refer"]
GradeLabel = Literal["nhẹ", "trung bình", "cao", "không rõ"]

@dataclass
class Assessment:
    agent_id: str
    role: str
    model: str
    grade: str
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    raw: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class SupervisorResult:
    decision: Decision
    grade: str
    rationale: str
    rule_ids: list[str] = field(default_factory=list)
    synthesis: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class ProjectManagerResult:
    action: PmAction
    note: str
    grade: str | None = None
    feedback: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class FinalCondition:
    grade: str
    evidence: list[str]
    status: str
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class ConditionRecord:
    image_name: str
    image_path: str
    rules_version: str
    assessments: list[Assessment]
    supervisor: SupervisorResult
    pm: ProjectManagerResult | None
    final: FinalCondition
    detector_hint: str = ""
    stats: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_name": self.image_name,
            "image_path": self.image_path,
            "rules_version": self.rules_version,
            "assessments": [a.to_dict() for a in self.assessments],
            "supervisor": self.supervisor.to_dict(),
            "pm": self.pm.to_dict() if self.pm else None,
            "final": self.final.to_dict(),
            "detector_hint": self.detector_hint,
            "stats": self.stats,
        }
