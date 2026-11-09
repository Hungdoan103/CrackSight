from __future__ import annotations

import base64
import io
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

from ..core.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_VL_MODEL, VL_MAX_SIDE

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_VI_RE = re.compile(
    r"[àáạảãăằắặẳẵâầấậẩẫèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)
_EN_START_RE = re.compile(
    r"^(okay|first|next|then|wait|so|the|let|also|maybe|alternatively|"
    r"position|second|third|this|that|now|for|wait)\b",
    re.IGNORECASE,
)
_EN_LEAK_RE = re.compile(
    r"\b(now,?\s*translating|translating\s+into|wait,?\s*maybe|for\s+shape|"
    r"for\s+location|should\s+be|the\s+subject|in\s+vietnamese|"
    r"here'?s|let'?s|i\s+will|i\s+need|the\s+image|okay[,.]|alright|like)\b",
    re.IGNORECASE,
)
_VI_LEAD_RE = re.compile(
    r"^(\d+[\.\)]\s*)?(hình|vết|vị|mức|ảnh|chi|mô|có |không |đường|nứt|tổng|phân|đánh|hành)",
    re.IGNORECASE,
)
_DETAIL_KEEP_RE = re.compile(
    r"(?m)^\s*[123][\.\)]\s+|Tổng quan vị trí|Phân tích chi tiết|Đánh giá sơ bộ",
    re.IGNORECASE,
)

def _strip_think(text: str) -> str:
    raw = text or ""
    if "</think>" in raw.lower():
        raw = re.split(r"</think>", raw, flags=re.IGNORECASE)[-1]
    raw = _THINK_RE.sub("", raw).strip()
    if re.match(r"^\s*<think>", raw, flags=re.IGNORECASE):
        return ""
    return raw

def _is_vi_line(line: str) -> bool:
    if _EN_START_RE.match(line) or _EN_LEAK_RE.search(line):
        return False
    vi = len(_VI_RE.findall(line))
    if vi < 2:
        return False
    words = re.findall(r"[A-Za-zÀ-ỹđĐ]+", line)
    if not words:
        return False
    ascii_words = [w for w in words if w.isascii()]
    return (len(ascii_words) / len(words)) <= 0.45

def extract_vietnamese(text: str) -> str:
    stripped = _strip_think(text or "")
    if _DETAIL_KEEP_RE.search(stripped):
        kept: list[str] = []
        for raw in re.split(r"\n+", stripped):
            line = raw.strip()
            if not line or _EN_LEAK_RE.search(line) or _EN_START_RE.match(line):
                continue
            if re.match(r"^\d+[\.\)]\s+", line) or _is_vi_line(line):
                kept.append(line)
        if kept:
            return "\n".join(kept).strip()
    quotes = re.findall(r"[\"“”«»]([^\"“”«»]{10,})[\"“”«»]", stripped)
    from_quotes = [q.strip().rstrip(" .") + "." for q in quotes if _is_vi_line(q.strip())]
    if from_quotes:
        return _uniq_join(from_quotes)
    parts: list[str] = []
    for raw in re.split(r"(?<=[.!?…])\s+|[\n;]+", stripped):
        line = raw.strip().lstrip("-*• ").strip().strip('"“”')
        if not line or line.lower().startswith("<think"):
            continue
        if _is_vi_line(line):
            parts.append(line.rstrip(":"))
    if not parts:
        return ""
    finals = [ln for ln in parts if _VI_LEAD_RE.match(ln)]
    return _uniq_join(finals[-5:] if finals else parts[-4:])

def _uniq_join(lines: list[str]) -> str:
    seen: set[str] = set()
    uniq: list[str] = []
    for ln in lines:
        key = re.sub(r"\s+", " ", ln.lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(ln)
    return " ".join(uniq).strip()

def _extract_answer(text: str) -> str:
    return extract_vietnamese(text)

def _encode_image(path: Path, max_side: int = VL_MAX_SIDE) -> str:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    scale = max_side / max(w, h)
    if scale < 1:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BILINEAR)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")

def _post_chat(payload: dict, timeout: int, think: bool, extract: bool = True) -> str:
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_HOST}. Start it first."
        ) from exc
    message = data.get("message") or {}
    content = (message.get("content") or "").strip()
    thinking = (message.get("thinking") or "").strip()
    raw = content or thinking
    if extract:
        text = _extract_answer(content) if (think or content) else ""
        if not text:
            text = _extract_answer(thinking or content)
        if text:
            return text
    text = _strip_think(raw)
    if not text:
        raise RuntimeError(f"Empty Ollama response: {data}")
    return text

def chat(
    prompt: str,
    model: str = OLLAMA_MODEL,
    think: bool = False,
    num_predict: int = 160,
    keep_alive: str = "10m",
    extract: bool = True,
) -> str:
    content = prompt if think else prompt.rstrip() + "\n/no_think"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "think": bool(think),
        "keep_alive": keep_alive,
        "options": {
            "temperature": 0.2,
            "num_predict": num_predict,
            "num_ctx": 2048,
        },
    }
    return _post_chat(payload, timeout=90, think=think, extract=extract)

def chat_vision(
    prompt: str,
    image_paths: list[str | Path],
    model: str = OLLAMA_VL_MODEL,
    think: bool = False,
    num_predict: int | None = None,
    fallback_short: bool = True,
    keep_alive: str = "5m",
    system: str | None = None,
    extract: bool = True,
    json_format: bool = False,
) -> str:
    paths = [Path(p) for p in image_paths if p and Path(p).exists()]
    if not paths:
        return chat(prompt, think=think, extract=extract)
    qwen3_vl = "qwen3" in model.lower() and "vl" in model.lower()
    use_no_think = (not think) and ("qwen3" in model.lower()) and (not qwen3_vl)
    content = prompt if not use_no_think else prompt.rstrip() + "\n/no_think"
    predict = num_predict if num_predict is not None else (850 if qwen3_vl else 220)
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append(
        {
            "role": "user",
            "content": content,
            "images": [_encode_image(p) for p in paths],
        }
    )
    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": bool(think),
        "keep_alive": keep_alive,
        "options": {
            "temperature": 0.2,
            "num_predict": predict,
            "num_ctx": 3072 if qwen3_vl else 4096,
        },
    }
    if json_format:
        payload["format"] = "json"
    try:
        text = _post_chat(payload, timeout=180, think=think, extract=extract)
    except RuntimeError:
        text = ""
    if fallback_short and qwen3_vl and len(text) < 80:
        payload["messages"][-1]["content"] = (
            "Chỉ tiếng Việt, đúng 2 câu. Cấm tiếng Anh và cấm giải thích cách dịch. Câu 1 hiện trường. Câu 2 hình dạng vết."
        )
        payload["options"]["num_predict"] = 850
        text = _post_chat(payload, timeout=180, think=think, extract=extract)
    return text

def _size_route(path: Path) -> str:
    from ..detection.sceneClassify import classify_scene_cv

    name, _ = classify_scene_cv(path)
    return name

def _parse_scene_code(text: str) -> str | None:
    cleaned = _strip_think(text or "")
    raw = re.sub(r"\s+", " ", cleaned).strip().lower()
    if not raw:
        return None
    if ("lcw =" in raw or "lcw=" in raw) and ("close =" in raw or "close=" in raw):
        return None
    token = re.match(r"^\s*(lcw|close)\s*[.\]]?\s*$", raw)
    if token:
        return "lcw" if token.group(1) == "lcw" else "conglomerate"
    m = re.search(r"(?<![a-z])(lcw|close)(?![a-z\-])", raw)
    if m:
        return "lcw" if m.group(1) == "lcw" else "conglomerate"
    if len(raw) <= 40:
        if re.search(r"hiện\s*trường|hientruong|cảnh\s*rộng", raw):
            return "lcw"
        if re.search(r"cận\s*cảnh|cancanh|gần\s*bề\s*mặt|sát\s*vết", raw):
            return "conglomerate"
    return None

def classify_scene(path: Path) -> tuple[str, str]:
    prompt = (
        "Classify this photo. Reply with EXACTLY one token: LCW or CLOSE.\n"
        "LCW = wide field/site view (road, structure, surroundings visible).\n"
        "CLOSE = tight surface close-up (concrete fills the frame, crack detail).\n"
        "Do not explain. Answer:"
    )
    try:
        text = chat_vision(
            prompt,
            [path],
            think=False,
            num_predict=32,
            fallback_short=False,
            keep_alive="0",
            extract=False,
        )
    except Exception as exc:
        from ..detection.sceneClassify import classify_scene_cv as _cv

        name, why = _cv(path)
        return name, f"CV ({why}; VLM lỗi: {exc})"
    text = _strip_think(text or "")
    code = _parse_scene_code(text)
    if code == "lcw":
        return "lcw", f"VLM: hiện trường ({text[:80]})"
    if code == "conglomerate":
        return "conglomerate", f"VLM: cận cảnh ({text[:80]})"
    from ..detection.sceneClassify import classify_scene_cv as _cv

    name, why = _cv(path)
    return name, f"CV ({why}; VLM không rõ: {text[:80]})"
