# CrackInspect API

FastAPI service for detection, VLM reporting, and Australia LiDAR endpoints.

```bash
# from repo root
pip install -r apps/api/requirements.txt
cd apps/api
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Package layout:

| Path | Role |
|------|------|
| `main.py` | HTTP entry (routes) |
| `crackinspect/core/` | Shared config / paths |
| `crackinspect/detection/` | Scene routing, masks, overlays, analyze pipeline |
| `crackinspect/enhancement/` | Real-ESRGAN / deblur helpers |
| `crackinspect/vlm/` | Ollama, captions, structure, reports, chat |
| `crackinspect/geo/` | EXIF + reverse geocoding |
| `crackinspect/lidar/` | LAS viewers, map overlay, 3D helpers |
| `crackinspect/domain/` | Condition assessment schemas |
| `crackinspect/agents/` | Multi-agent condition workflow |
| `../../configs/` | Shared runtime rules (`conditionRules.json`) |
