"""
CodeVI API - FastAPI server combining BM25 search, graph extraction, and route detection
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional
import sys
import json

# Add project root to path for imports
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from backend.search_engine import SearchEngine
from packages.core.ingest import ingest_repo
from packages.core.models import Node, Edge

app = FastAPI(title="CodeVI API", version="0.1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global search engine instance
search_engine: Optional[SearchEngine] = None
data_dir = Path(__file__).resolve().parents[2] / "data"
data_dir.mkdir(exist_ok=True)


def read_jsonl(path: Path):
    """Read JSONL file"""
    if not path.exists():
        return []
    return [
        json.loads(line) 
        for line in path.read_text(encoding="utf-8").splitlines() 
        if line.strip()
    ]


# Request/Response models
class ScanRequest(BaseModel):
    root_path: str


class SearchRequest(BaseModel):
    query: str
    max_results: int = 10


class SnippetResult(BaseModel):
    file_path: str
    line_number: int
    content: str
    score: float


class SearchResponse(BaseModel):
    results: List[SnippetResult]
    total_matches: int


@app.get("/")
def index():
    """API information endpoint"""
    return {
        "name": "CodeVI API",
        "version": "0.1.0",
        "endpoints": {
            "health": "GET /health - Check server status",
            "healthz": "GET /healthz - Health check (compat)",
            "scan": "POST /scan - Index a codebase",
            "search": "POST /search - Search indexed codebase",
            "graph": "GET /api/graph - Get codebase relationship graph",
            "routes": "GET /routes - Get detected API routes",
            "entities": "GET /entities - Get all nodes",
            "edges": "GET /edges - Get all edges"
        },
        "status": "running"
    }


@app.get("/health")
@app.get("/healthz")
def health():
    """Health check endpoint"""
    return {
        "ok": True,
        "status": "healthy",
        "indexed": search_engine is not None and search_engine.is_indexed(),
        "file_count": search_engine.get_file_count() if search_engine else 0
    }


@app.post("/scan")
def scan_codebase(request: ScanRequest):
    """Scan and index a codebase directory"""
    global search_engine
    
    root_path = Path(request.root_path)
    if not root_path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {root_path}")
    
    if not root_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {root_path}")
    
    try:
        # Index for BM25 search
        search_engine = SearchEngine(root_path)
        search_engine.index_codebase()
        
        # Extract routes and relationships
        result = ingest_repo(root_path)
        
        # Save to JSONL files
        (data_dir / "entities.jsonl").write_text(
            "\n".join(json.dumps(n, ensure_ascii=False) for n in result["nodes"]),
            encoding="utf-8"
        )
        (data_dir / "edges.jsonl").write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in result["edges"]),
            encoding="utf-8"
        )
        
        return {
            "status": "success",
            "files_indexed": search_engine.get_file_count(),
            "nodes_extracted": len(result["nodes"]),
            "edges_extracted": len(result["edges"]),
            "message": f"Indexed {search_engine.get_file_count()} files, extracted {len(result['nodes'])} nodes and {len(result['edges'])} edges"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error indexing codebase: {str(e)}")


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """Search the indexed codebase using BM25"""
    if search_engine is None:
        raise HTTPException(status_code=400, detail="Codebase not indexed. Call /scan first.")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        results = search_engine.search(request.query, max_results=request.max_results)
        
        snippet_results = [
            SnippetResult(
                file_path=result["file_path"],
                line_number=result["line_number"],
                content=result["content"],
                score=result["score"]
            )
            for result in results
        ]
        
        return SearchResponse(
            results=snippet_results,
            total_matches=len(snippet_results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")


@app.get("/api/graph")
def get_graph():
    """Get codebase relationship graph"""
    if search_engine is None:
        raise HTTPException(status_code=400, detail="Codebase not indexed. Call /scan first.")
    
    try:
        graph_data = search_engine.extract_graph()
        return graph_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting graph: {str(e)}")


@app.get("/routes")
def routes():
    """Get detected API routes"""
    return read_jsonl(data_dir / "entities.jsonl")


@app.get("/entities")
def entities():
    """Get all nodes"""
    return read_jsonl(data_dir / "entities.jsonl")


@app.get("/edges")
def edges():
    """Get all edges"""
    return read_jsonl(data_dir / "edges.jsonl")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

