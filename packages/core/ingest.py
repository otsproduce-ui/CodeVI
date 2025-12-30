"""
CodeVI Ingest - Extract routes, API calls, and relationships from codebase
Combines route detection with BM25 indexing
"""
from __future__ import annotations
import re
import json
from pathlib import Path
from typing import Iterable, Dict, List, Optional
from pathspec import PathSpec

from .models import Node, Edge

# Patterns for detection
ROUTE_DECORATOR = re.compile(r'@app\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', re.M)
FETCH_CALL = re.compile(r'\b(fetch|axios)\s*\(\s*["\']([^"\']+)["\']', re.M)
JS_LIKE = {".ts", ".tsx", ".js", ".jsx"}
PY = {".py"}

IGNORE_DEFAULT = [
    ".git/", "node_modules/", "dist/", "build/", ".venv/", "__pycache__/",
    ".next/", ".nuxt/", "target/", "bin/", "obj/", ".idea/", ".vscode/", ".vs/",
    "coverage/", ".pytest_cache/"
]


def load_ignore(repo: Path) -> PathSpec:
    """Load .gitignore patterns"""
    patterns = list(IGNORE_DEFAULT)
    gi = repo / ".gitignore"
    if gi.exists():
        patterns += [
            line.strip() 
            for line in gi.read_text().splitlines() 
            if line.strip() and not line.startswith("#")
        ]
    return PathSpec.from_lines("gitwildmatch", patterns)


def walk(repo: Path, spec: PathSpec) -> Iterable[Path]:
    """Walk repository files respecting ignore patterns"""
    for p in repo.rglob("*"):
        rel = str(p.relative_to(repo)).replace("\\", "/")
        if spec.match_file(rel):
            continue
        if p.is_file():
            yield p


def ingest_repo(repo: Path) -> Dict[str, List[Dict]]:
    """
    Extract routes, API calls, and test files from codebase.
    Returns nodes and edges in the format expected by the API.
    """
    nodes: List[Dict] = []
    edges: List[Dict] = []
    node_ids = set()  # Track node IDs to avoid duplicates

    for file in walk(repo, load_ignore(repo)):
        ext = file.suffix.lower()
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel_path = str(file.relative_to(repo)).replace("\\", "/")

        # Detect FastAPI routes
        if ext in PY:
            if "from fastapi import" in text or "import fastapi" in text or "@app." in text:
                for m in ROUTE_DECORATOR.finditer(text):
                    method, path = m.group(1), m.group(2)
                    nid = f"route:{path}"
                    if nid not in node_ids:
                        line_num = text[:m.start()].count('\n') + 1
                        nodes.append(
                            Node(
                                node_id=nid,
                                kind="route",
                                name=f"{method.upper()} {path}",
                                path=rel_path,
                                lang="python",
                                start=line_num,
                                end=text[:m.end()].count('\n') + 1
                            ).model_dump()
                        )
                        node_ids.add(nid)

        # Detect client fetch/axios calls
        if ext in JS_LIKE:
            file_nid = f"file:{rel_path}"
            for m in FETCH_CALL.finditer(text):
                url = m.group(2)
                # Add file node if not already added
                if file_nid not in node_ids:
                    nodes.append(
                        Node(
                            node_id=file_nid,
                            kind="file",
                            name=file.name,
                            path=rel_path,
                            lang="js"
                        ).model_dump()
                    )
                    node_ids.add(file_nid)
                
                # Link to route by path match
                route_nid = f"route:{url}"
                if route_nid in node_ids:
                    edges.append(
                        Edge(
                            src=file_nid,
                            dst=route_nid,
                            type="client_to_route"
                        ).model_dump()
                    )

        # Detect test files
        base = file.name
        if (base.startswith("test_") or 
            base.endswith("_test.py") or 
            base.endswith(".test.ts") or 
            base.endswith(".test.tsx")):
            test_nid = f"test:{rel_path}"
            if test_nid not in node_ids:
                nodes.append(
                    Node(
                        node_id=test_nid,
                        kind="test",
                        name=base,
                        path=rel_path
                    ).model_dump()
                )
                node_ids.add(test_nid)

    return {"nodes": nodes, "edges": edges}

