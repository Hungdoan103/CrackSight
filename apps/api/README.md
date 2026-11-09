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
| `crackinspect/` | Domain logic — detection, overlays, VLM, LiDAR, agents |
| `../../configs/` | Shared runtime rules (`conditionRules.json`) |
