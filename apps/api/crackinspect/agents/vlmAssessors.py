from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from ..config import OLLAMA_VL_MODEL
from ..conditionSchema import Assessment
from ..ollamaClient import chat_vision, extract_vietnamese

_GRADE_RE = re.compile(
    r"(nhẹ|nhe|trung\s*bình|trung\s*binh|cao|không\s*rõ|khong\s*ro)",
    re.IGNORECASE,
)

def _normalize_grade(text: str) -> str:
    raw = (text or "").lower()
    if re.search(r"không\s*rõ|khong\s*ro|unclear|unknown", raw):
        return "không rõ"
    if re.search(r"\bcao\b|high|nguy hiểm", raw):
        return "cao"
    if re.search(r"trung\s*bình|trung\s*binh|medium", raw):
        return "trung bình"
    if re.search(r"\bnhẹ\b|\bnhe\b|low|nhẹ nhàng", raw):
        return "nhẹ"
    return "không rõ"

def _parse_assessment_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    grade = _normalize_grade(text)
    evidence: list[str] = []
    for line in re.split(r"[\n;•\-]+", text):
        line = line.strip(" .")
        if 8 <= len(line) <= 120 and not line.lower().startswith("grade"):
            evidence.append(line)
    return {"grade": grade, "evidence": evidence[:3], "confidence": 0.4, "note": text[:400]}

def _build_prompt(agent: dict, detect_ctx: dict, stats: str) -> str:
    ratio = float(detect_ctx.get("crack_ratio") or 0)
    n_inst = len(detect_ctx.get("instances") or [])
    levels = [str(i.get("level") or "") for i in (detect_ctx.get("instances") or []) if i.get("level")]
    hint = (
        f"DeepInspect: crack_ratio={ratio:.4f}, instances={n_inst}"
        + (f", levels={levels[:8]}" if levels else "")
    )
    instruction = agent.get("instruction") or ""
    return (
        f"Bạn là agent đánh giá điều kiện vết nứt ({agent.get('id')}, role={agent.get('role')}).\n"
        f"{instruction}\n"
        f"Gợi ý detector (không chép nguyên): {hint}. Stats: {stats[:240]}\n"
        "Trả về ĐÚNG một JSON (không markdown):\n"
        '{"grade":"nhẹ|trung bình|cao|không rõ","evidence":["..."],"confidence":0.0,"note":"..."}\n'
        "grade bắt buộc một trong bốn giá trị. evidence 1-3 cụm tiếng Việt ngắn. "
        "Cấm tiếng Anh dài, cấm bịa số mm nếu không thấy thước."
    )

def _run_one_agent(
    agent: dict,
    path: Path,
    detect_ctx: dict,
    stats: str,
    model_name: str,
) -> Assessment:
    agent_id = str(agent.get("id") or "agent")
    role = str(agent.get("role") or "assess")
    prompt = _build_prompt(agent, detect_ctx, stats)
    try:
        raw = chat_vision(
            prompt,
            [path],
            model=model_name,
            think=False,
            num_predict=160,
            fallback_short=False,
            extract=False,
        )
        parsed = _parse_assessment_json(raw)
        if parsed.get("grade") == "không rõ" and "{" not in (raw or ""):
            grade_m = _GRADE_RE.search(raw or "")
            if grade_m:
                parsed["grade"] = _normalize_grade(grade_m.group(1))
            note = extract_vietnamese(raw) or raw
            if note and not parsed.get("evidence"):
                parsed["evidence"] = [note[:120]]
        grade = _normalize_grade(str(parsed.get("grade") or ""))
        evidence = parsed.get("evidence") or []
        if isinstance(evidence, str):
            evidence = [evidence]
        evidence = [str(e).strip() for e in evidence if str(e).strip()][:3]
        conf = float(parsed.get("confidence") or 0.5)
        conf = max(0.0, min(1.0, conf))
        return Assessment(
            agent_id=agent_id,
            role=role,
            model=model_name,
            grade=grade,
            evidence=evidence,
            confidence=conf,
            raw=(raw or "")[:1200],
        )
    except Exception as exc:
        return Assessment(
            agent_id=agent_id,
            role=role,
            model=model_name,
            grade="không rõ",
            evidence=[],
            confidence=0.0,
            raw="",
            error=str(exc),
        )

def run_vlm_assessments(
    image_path: Path,
    detect_ctx: dict,
    agents: list[dict],
    *,
    stats: str = "",
    model: str | None = None,
) -> list[Assessment]:
    path = Path(image_path)
    model_name = model or OLLAMA_VL_MODEL
    if not agents:
        return []
    if len(agents) == 1:
        return [_run_one_agent(agents[0], path, detect_ctx, stats, model_name)]
    out: list[Assessment] = []
    with ThreadPoolExecutor(max_workers=min(3, len(agents))) as pool:
        futs = {
            pool.submit(_run_one_agent, agent, path, detect_ctx, stats, model_name): i
            for i, agent in enumerate(agents)
        }
        slots: list[Assessment | None] = [None] * len(agents)
        for fut in as_completed(futs):
            slots[futs[fut]] = fut.result()
        out = [s for s in slots if s is not None]
    return out
