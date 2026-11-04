from __future__ import annotations

import json
import re
from typing import Any

from ..config import OLLAMA_MODEL
from ..condition_schema import Assessment, ProjectManagerResult, SupervisorResult
from ..ollama_client import chat

_VALID = {"nhẹ", "trung bình", "cao", "không rõ"}

def run_project_manager(
    assessments: list[Assessment],
    supervisor: SupervisorResult,
    detect_ctx: dict,
    rules: dict,
) -> ProjectManagerResult:
    pm_rules = rules.get("project_manager") or {}
    if not pm_rules.get("enabled", True):
        return ProjectManagerResult(
            action="refer",
            note="PM disabled in rules; escalate to human.",
            grade=None,
            feedback="",
        )

    payload = {
        "supervisor": supervisor.to_dict(),
        "assessments": [a.to_dict() for a in assessments],
        "real_detection": bool(detect_ctx.get("real_detection")),
        "crack_ratio": detect_ctx.get("crack_ratio"),
        "pm_note": pm_rules.get("bounded_note") or "",
    }
    prompt = (
        "Bạn là LLM project manager xử lý case điều kiện vết nứt UNRESOLVED.\n"
        "Chỉ được: resolve (chốt grade có căn cứ) hoặc refer (đẩy người/phiên kiểm tra sau).\n"
        "Không được tự sửa rules production.\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        "Trả về ĐÚNG JSON:\n"
        '{"action":"resolve|refer","grade":"nhẹ|trung bình|cao|không rõ"|null,'
        '"note":"lý do ngắn tiếng Việt","feedback":"gợi ý cải thiện prompt/rules (không áp dụng tự động)"}\n'
        "Cấm markdown."
    )
    try:
        raw = chat(prompt, model=OLLAMA_MODEL, think=False, num_predict=280, extract=False)
    except Exception as exc:
        return ProjectManagerResult(
            action="refer",
            note=f"PM LLM lỗi — refer: {exc}",
            grade=None,
            feedback="",
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

    action = str(data.get("action") or "refer").lower()
    if action not in {"resolve", "refer"}:
        action = "refer"
    grade = data.get("grade")
    if grade is not None:
        grade = str(grade)
        if grade not in _VALID:
            grade = None
    if action == "resolve" and not grade:
        grade = supervisor.grade if supervisor.grade in _VALID else "không rõ"

    return ProjectManagerResult(
        action=action,  # type: ignore[arg-type]
        note=str(data.get("note") or text[:300]),
        grade=grade,
        feedback=str(data.get("feedback") or ""),
    )
