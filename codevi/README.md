# CodeVI Starter (M0)
A tiny walking skeleton you can drop into your existing repo. It ingests FastAPI routes and basic client fetch calls, writes entities/edges JSONL, and exposes a FastAPI stub to inspect results.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r apps/api/requirements.txt

# Ingest your project (point to your project root)
python -m packages.core.ingest --repo /path/to/your/project --out ./data

# Run API
uvicorn apps.api.main:app --reload
```

Then open http://127.0.0.1:8000/docs
- GET /routes     -> list detected FastAPI routes
- GET /entities   -> raw entities
- GET /edges      -> raw edges
```
