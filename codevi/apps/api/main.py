from fastapi import FastAPI
from pathlib import Path
import json

app = FastAPI(title="CodeVI API (M0)")

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

def read_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/routes")
def routes():
    nodes = read_jsonl(DATA_DIR / "entities.jsonl")
    return [n for n in nodes if n.get("kind") == "route"]

@app.get("/entities")
def entities():
    return read_jsonl(DATA_DIR / "entities.jsonl")

@app.get("/edges")
def edges():
    return read_jsonl(DATA_DIR / "edges.jsonl")
