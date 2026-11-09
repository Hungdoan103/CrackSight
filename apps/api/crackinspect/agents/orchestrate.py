from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..conditionSchema import ConditionRecord, FinalCondition
from ..config import INSPECT_ROOT, STORE_DIR
from .projectManager import run_project_manager
from .supervisor import _detector_grade_hint, run_supervisor
from .vlmAssessors import run_vlm_assessments

RULES_PATH = INSPECT_ROOT / "configs" / "conditionRules.json"
CONDITION_DIR = STORE_DIR / "condition_sessions"
LAST_PATH = CONDITION_DIR / "last.json"

def load_condition_rules(path: Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else RULES_PATH
    return json.loads(target.read_text(encoding="utf-8"))

def _history_events(record: ConditionRecord) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for a in record.assessments:
        events.append(
            {
                "step": "vlm_assessment",
                "agent_id": a.agent_id,
                "grade": a.grade,
                "evidence": a.evidence,
                "error": a.error,
            }
        )
    events.append(
        {
            "step": "supervisor",
            "decision": record.supervisor.decision,
            "grade": record.supervisor.grade,
            "rationale": record.supervisor.rationale,
            "rule_ids": record.supervisor.rule_ids,
        }
    )
    if record.pm:
        events.append(
            {
                "step": "project_manager",
                "action": record.pm.action,
                "grade": record.pm.grade,
                "note": record.pm.note,
                "feedback": record.pm.feedback,
            }
        )
    events.append(
        {
            "step": "final",
            "status": record.final.status,
            "grade": record.final.grade,
            "evidence": record.final.evidence,
        }
    )
    return events

def run_condition_pipeline(
    image_path: Path | str,
    detect_ctx: dict,
    *,
    stats: str = "",
    rules: dict | None = None,
) -> ConditionRecord:
    from ..config import MULTI_AGENT_MODE

    path = Path(image_path)
    rules_data = rules or load_condition_rules()
    agents = list(rules_data.get("agents") or [])
    if not agents:
        raise RuntimeError("conditionRules.json has no agents")
    if MULTI_AGENT_MODE == "1":
        agents = agents[:1]
    elif MULTI_AGENT_MODE == "0":
        agents = []

    if agents:
        assessments = run_vlm_assessments(path, detect_ctx, agents, stats=stats)
    else:
        from ..conditionSchema import Assessment
        from .supervisor import _detector_grade_hint

        hint = _detector_grade_hint(detect_ctx)
        assessments = [
            Assessment(
                agent_id="detector_hint",
                role="detector",
                model="deeplab",
                grade=hint,
                evidence=[stats[:160]] if stats else [],
                confidence=0.55,
                raw="",
            )
        ]
    supervisor = run_supervisor(assessments, detect_ctx, rules_data, stats=stats)

    pm = None
    final_grade = supervisor.grade
    final_status = "supported"
    if supervisor.decision == "unresolved":
        pm = run_project_manager(assessments, supervisor, detect_ctx, rules_data)
        if pm.action == "resolve" and pm.grade:
            final_grade = pm.grade
            final_status = "resolved"
        else:
            final_status = "refer"
            final_grade = pm.grade or supervisor.grade or "không rõ"

    evidence: list[str] = []
    for a in assessments:
        for e in a.evidence:
            if e not in evidence:
                evidence.append(e)
    evidence = evidence[:6]

    record = ConditionRecord(
        image_name=str(detect_ctx.get("image_name") or path.name),
        image_path=str(path),
        rules_version=str(rules_data.get("version") or "1.0"),
        assessments=assessments,
        supervisor=supervisor,
        pm=pm,
        final=FinalCondition(
            grade=final_grade,
            evidence=evidence,
            status=final_status,
            history=[],
        ),
        detector_hint=_detector_grade_hint(detect_ctx),
        stats=stats,
    )
    record.final.history = _history_events(record)
    persist_condition_record(record)
    return record

def persist_condition_record(record: ConditionRecord) -> Path:
    CONDITION_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(record.image_name).stem or "case"
    path = CONDITION_DIR / f"{stem}.json"
    data = record.to_dict()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    LAST_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

def load_last_condition() -> dict[str, Any] | None:
    if not LAST_PATH.is_file():
        return None
    try:
        return json.loads(LAST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
