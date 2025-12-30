from __future__ import annotations
import re, json, hashlib
from pathlib import Path
from typing import Iterable, Dict, List
import typer
from pathspec import PathSpec
from .models import Node, Edge

app = typer.Typer(help="CodeVI simple ingester (M0)")


IGNORE_DEFAULT = [
    ".git/", "node_modules/", "dist/", "build/", ".venv/", "__pycache__/",
]

ROUTE_DECORATOR = re.compile(r'@app\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', re.M)
FETCH_CALL = re.compile(r'\b(fetch|axios)\s*\(\s*["\']([^"\']+)["\']', re.M)
JS_LIKE = {".ts", ".tsx", ".js", ".jsx"}
PY = {".py"}

def sha1(s:str)->str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]

def load_ignore(repo: Path) -> PathSpec:
    patterns = list(IGNORE_DEFAULT)
    gi = repo / ".gitignore"
    if gi.exists():
        patterns += [line.strip() for line in gi.read_text().splitlines() if line.strip() and not line.startswith("#")]
    return PathSpec.from_lines("gitwildmatch", patterns)

def walk(repo: Path, spec: PathSpec) -> Iterable[Path]:
    for p in repo.rglob("*"):
        rel = str(p.relative_to(repo)).replace("\\","/")
        if spec.match_file(rel):
            continue
        if p.is_file():
            yield p

def ingest_repo(repo: Path) -> Dict[str, List[Dict]]:
    nodes: List[Dict] = []
    edges: List[Dict] = []

    for file in walk(repo, load_ignore(repo)):
        ext = file.suffix.lower()
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Detect FastAPI routes
        if ext in PY:
            if "from fastapi import" in text or "import fastapi" in text or "@app." in text:
                for m in ROUTE_DECORATOR.finditer(text):
                    method, path = m.group(1), m.group(2)
                    nid = f"route:{path}"
                    nodes.append(Node(node_id=nid, kind="route", name=f"{method.upper()} {path}",
                                      path=str(file), lang="python", start=text[:m.start()].count('\\n')+1,
                                      end=text[:m.end()].count('\\n')+1).model_dump())
        # Detect client fetch/axios
        if ext in JS_LIKE:
            for m in FETCH_CALL.finditer(text):
                url = m.group(2)
                nid = f"file:{file}"
                if not any(n["node_id"]==nid for n in nodes):
                    nodes.append(Node(node_id=nid, kind="file", name=file.name, path=str(file),
                                      lang="js", start=None, end=None).model_dump())
                # naive link to route by path match
                edges.append(Edge(src=nid, dst=f"route:{url}", type="client_to_route").model_dump())

        # Tests (heuristic)
        base = file.name
        if base.startswith("test_") or base.endswith("_test.py") or base.endswith(".test.ts") or base.endswith(".test.tsx"):
            nodes.append(Node(node_id=f"test:{file}", kind="test", name=base, path=str(file)).model_dump())

    return {"nodes": nodes, "edges": edges}

@app.command()
def main(repo: str = typer.Option(..., help="Path to your project root"),
         out: str = typer.Option("./data", help="Output folder")):
    repo_p = Path(repo).resolve()
    out_p = Path(out).resolve()
    out_p.mkdir(parents=True, exist_ok=True)

    result = ingest_repo(repo_p)

    (out_p / "entities.jsonl").write_text(
        "\n".join(json.dumps(n, ensure_ascii=False) for n in result["nodes"]), encoding="utf-8")
    (out_p / "edges.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in result["edges"]), encoding="utf-8")
    print(f"Wrote {len(result['nodes'])} nodes and {len(result['edges'])} edges to {out_p}")

if __name__ == "__main__":
    app()
