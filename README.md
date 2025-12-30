# CodeVI

**CodeVI** is a local-first tool that lets developers and QA ask natural-language questions about codebases and get cited answers with visual trace graphs.

## Phase A: MVP Lexical Search

This MVP implements:
- **BM25 lexical search** for codebase indexing
- **FastAPI backend** (recommended) with `/health`, `/scan`, `/search`, `/api/graph`, `/routes`, `/entities`, `/edges` endpoints
- **Flask backend** (legacy) also available for compatibility
- **Simple frontend** with Ask page (`/`) and Results page (`/results`)
- **CLI interface** with `ingest`, `index`, and `query` commands
- **Local-only design** - no external APIs or cloud services

## Setup

### Prerequisites
- Python 3.8+
- A codebase to search

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start both servers (recommended):
```bash
python run_all.py
```
Or on Windows:
```bash
run_all.bat
```

This will start:
- Everything on `http://localhost:8000`
  - Frontend: `http://localhost:8000`
  - API: `http://localhost:8000/api/v1`

**Alternative - FastAPI (recommended):**
```bash
# Terminal 1: FastAPI Backend
cd apps/api
python main.py

# Terminal 2: Frontend
cd frontend
python -m http.server 8000
```

**Alternative - Flask (legacy):**
```bash
# Terminal 1: Flask Backend
cd backend
python main.py

# Terminal 2: Frontend
cd frontend
python -m http.server 8000
```

**CLI Usage:**
```bash
# Extract routes and relationships
python cli.py ingest --repo /path/to/codebase

# Index for search
python cli.py index --repo /path/to/codebase

# Search from CLI
python cli.py query --query "login function" --repo /path/to/codebase
```

**Troubleshooting:** If you get a "port already in use" error:
- Run `kill_port_8000.bat` to free the port, or
- Find and kill the process: `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`

3. Open the frontend:
- If using `run_all.py`: Open `http://127.0.0.1:8000` in your browser
- If running manually: Open `frontend/index.html` directly or use the HTTP server

## Usage

1. **Scan your codebase**:
   - Enter the path to your codebase root directory
   - Click "Scan Codebase"
   - Wait for indexing to complete

2. **Search**:
   - Enter a natural language query (e.g., "Where's the login button handled?")
   - Click "Search"
   - View results with code snippets and file locations

## API Endpoints

All endpoints return JSON. The backend uses Flask with CORS enabled.

### `GET /health` or `GET /healthz`
Check server status and indexing state.

**Response:**
```json
{
  "ok": true,
  "status": "healthy",
  "indexed": true,
  "file_count": 150
}
```

### `POST /scan`
Index a codebase directory.

**Request:**
```json
{
  "root_path": "C:\\path\\to\\codebase"
}
```

**Response (Success):**
```json
{
  "status": "success",
  "files_indexed": 150,
  "message": "Indexed 150 files"
}
```

**Response (Error):**
```json
{
  "error": "Path does not exist: ..."
}
```

### `POST /search`
Search the indexed codebase.

**Request:**
```json
{
  "query": "login button handler",
  "max_results": 10
}
```

**Response (Success):**
```json
{
  "results": [
    {
      "file_path": "src/components/Login.jsx",
      "line_number": 42,
      "content": " 39 | const handleLogin = () => {\n> 42 |   // Login button handler\n 43 |   ...",
      "score": 2.45
    }
  ],
  "total_matches": 10
}
```

**Response (Error):**
```json
{
  "error": "Codebase not indexed. Call /scan first."
}
```

### `GET /routes`
Get detected API routes from codebase.

**Response:**
```json
[
  {
    "node_id": "route:/api/users",
    "kind": "route",
    "name": "GET /api/users",
    "path": "src/api/users.py",
    "lang": "python",
    "start": 15,
    "end": 20
  }
]
```

### `GET /entities`
Get all nodes (files, routes, tests, etc.).

**Response:**
```json
[
  {
    "node_id": "file:src/components/Login.jsx",
    "kind": "file",
    "name": "Login.jsx",
    "path": "src/components/Login.jsx",
    "lang": "js"
  }
]
```

### `GET /edges`
Get all relationships (imports, API calls, etc.).

**Response:**
```json
[
  {
    "src": "file:src/components/Login.jsx",
    "dst": "route:/api/login",
    "type": "client_to_route"
  }
]
```

## Architecture

- **Backend**: FastAPI (recommended) or Flask (legacy) with BM25 search engine
- **Frontend**: Vanilla HTML/CSS/JS (no framework dependencies)
- **Core Package**: `packages/core` with models, ingest logic
- **Search**: rank-bm25 library for lexical search
- **Graph Extraction**: Automatic detection of routes, API calls, imports
- **CLI**: Unified CLI with `ingest`, `index`, `query` commands
- **Local-first**: All processing happens locally, no external services
- **CORS**: Enabled for frontend-backend communication

## Next Steps

See `docs/implementation-plan.md` for Phase B and beyond:
- Semantic search with embeddings
- Visual trace graphs
- Advanced query understanding
- Multi-file context

## License

MIT

