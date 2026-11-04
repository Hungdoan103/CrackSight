from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from ..config import OLLAMA_MODEL
from ..condition_schema import Assessment, SupervisorResult
from ..ollama_client import chat

_VALID = {"nhẹ", "trung bình", "cao", "không rõ"}

def _detector_grade_hint(detect_ctx: dict) -> str:
    levels = [str(i.get("level") or "") for i in (detect_ctx.get("instances") or [])]
    if any(lv == "cao" for lv in levels):
        return "cao"
    if any(lv == "trung bình" for lv in levels):
        return "trung bình"
    ratio = float(detect_ctx.get("crack_ratio") or 0)
    if not detect_ctx.get("real_detection") and ratio < 0.001:
        return "không rõ"
    if ratio >= 0.02:
        return "cao"
    if ratio >= 0.005:
        return "trung bình"
    if detect_ctx.get("real_detection") or ratio >= 0.001:
        return "nhẹ"
    return "không rõ"

def _rule_based_decision(
    assessments: list[Assessment],
    detect_ctx: dict,
    rules: dict,
) -> SupervisorResult | None:
    grades = [a.grade for a in assessments if a.grade in _VALID and not a.error]
    if len(grades) < 2:
        return None
    counts = Counter(grades)
    top_grade, top_n = counts.most_common(1)[0]
    with_evidence = [a for a in assessments if a.evidence and a.grade == top_grade]
    det = _detector_grade_hint(detect_ctx)
    real = bool(detect_ctx.get("real_detection"))

    if not real and top_grade in {"cao", "trung bình"} and top_n >= 2:
        return SupervisorResult(
            decision="unresolved",
            grade="không rõ",
            rationale="Detector không thấy nứt rõ nhưng VLM chấm trung bình/cao.",
            rule_ids=["unresolved_detector_vlm_conflict"],
            synthesis="",
        )

    if top_grade == "không rõ" and top_n >= 2:
        return SupervisorResult(
            decision="unresolved",
            grade="không rõ",
            rationale="Đa số assessor trả không rõ.",
            rule_ids=["unresolved_unclear_majority"],
            synthesis="",
        )

    distinct = {g for g in grades if g != "không rõ"}
    if len(distinct) >= 2 and top_n < 2:
        return SupervisorResult(
            decision="unresolved",
            grade="không rõ",
            rationale=f"Assessor xung đột grade: {dict(counts)}.",
            rule_ids=["unresolved_grade_conflict"],
            synthesis="",
        )

    if top_n >= 2 and len(with_evidence) >= 1 and top_grade != "không rõ":
        return SupervisorResult(
            decision="supported",
            grade=top_grade,
            rationale=f"≥2 assessor đồng thuận grade={top_grade} có evidence.",
            rule_ids=["supported_grades_agree"],
            synthesis="",
        )

    if top_n >= 2 and top_grade == det and top_grade != "không rõ":
        return SupervisorResult(
            decision="supported",
            grade=top_grade,
            rationale=f"Majority grade khớp detector hint ({det}).",
            rule_ids=["supported_majority_and_detector"],
            synthesis="",
        )

    _ = rules  # reserved for stricter rule_ids later
    return None

def _llm_supervise(
    assessments: list[Assessment],
    detect_ctx: dict,
    rules: dict,
    stats: str,
) -> SupervisorResult:
    payload = {
        "assessments": [a.to_dict() for a in assessments],
        "detector_hint": _detector_grade_hint(detect_ctx),
        "real_detection": bool(detect_ctx.get("real_detection")),
        "stats": stats[:300],
        "rules_supervisor": rules.get("supervisor") or {},
    }
    prompt = (
        "Bạn là LLM supervisor chấm điều kiện vết nứt theo rules nội bộ.\n"
        "Input JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n\n"
        "Quyết định decision=supported nếu đủ đồng thuận + evidence; "
        "ngược lại decision=unresolved.\n"
        "Trả về ĐÚNG một JSON:\n"
        '{"decision":"supported|unresolved","grade":"nhẹ|trung bình|cao|không rõ",'
        '"rationale":"...","rule_ids":["..."],'
        '"synthesis":"2-4 câu tiếng Việt tóm tắt điều kiện và evidence"}\n'
        "Cấm markdown."
    )
    try:
        raw = chat(prompt, model=OLLAMA_MODEL, think=False, num_predict=320, extract=False)
    except Exception as exc:
        return SupervisorResult(
            decision="unresolved",
            grade="không rõ",
            rationale=f"Supervisor LLM lỗi: {exc}",
            rule_ids=["unresolved_llm_error"],
            synthesis="",
        )
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    data: dict[str, Any] = {}
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
        except Exception:
            data = {}
    decision = str(data.get("decision") or "unresolved").lower()
    if decision not in {"supported", "unresolved"}:
        decision = "unresolved"
    grade = str(data.get("grade") or "không rõ")
    if grade not in _VALID:
        g = grade.lower()
        if "cao" in g:
            grade = "cao"
        elif "trung" in g:
            grade = "trung bình"
        elif "nh" in g:
            grade = "nhẹ"
        else:
            grade = "không rõ"
    rule_ids = data.get("rule_ids") or []
    if isinstance(rule_ids, str):
        rule_ids = [rule_ids]
    return SupervisorResult(
        decision=decision,  # type: ignore[arg-type]
        grade=grade,
        rationale=str(data.get("rationale") or text[:400]),
        rule_ids=[str(r) for r in rule_ids][:8],
        synthesis=str(data.get("synthesis") or ""),
    )

def run_supervisor(
    assessments: list[Assessment],
    detect_ctx: dict,
    rules: dict,
    *,
    stats: str = "",
) -> SupervisorResult:
    fast = _rule_based_decision(assessments, detect_ctx, rules)
    if fast is not None:
        evid = []
        for a in assessments:
            evid.extend(a.evidence[:1])
        evid = evid[:4]
        fast.synthesis = (
            f"Supervisor ({fast.decision}): mức {fast.grade}. {fast.rationale} "
            + ("Evidence: " + "; ".join(evid) if evid else "")
        ).strip()
        return fast
    result = _llm_supervise(assessments, detect_ctx, rules, stats)
    if not result.synthesis:
        result.synthesis = f"Supervisor ({result.decision}): mức {result.grade}. {result.rationale}"
    return result
