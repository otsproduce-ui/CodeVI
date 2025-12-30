"""
API Routes - All endpoints with error handling
"""
from flask import Blueprint, request, jsonify, current_app
from pathlib import Path
from app.search_service import SearchService
from app.graph_service import GraphService
from app.semantic_service import SemanticSearchService

routes_bp = Blueprint("routes", __name__)

# Initialize services (will be set up in create_app)
search_service = None
graph_service = None
semantic_service = None


def init_services(app):
    """Initialize services with app config"""
    global search_service, graph_service, semantic_service
    search_service = SearchService(".", app.config["INDEX_PATH"])
    search_service.load_index()
    graph_service = GraphService(search_service)
    
    # Initialize semantic service
    semantic_service = SemanticSearchService(
        root_path=".",
        vector_index_file=app.config.get("VECTOR_INDEX_PATH", "vector.index")
    )
    semantic_service.load_index()


@routes_bp.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    is_indexed = False
    file_count = 0
    if search_service:
        is_indexed = search_service.is_indexed()
        file_count = search_service.file_count()
    
    return jsonify({
        "ok": True,
        "status": "healthy",
        "indexed": is_indexed,
        "file_count": file_count
    })


@routes_bp.route("/scan", methods=["POST"])
def scan():
    """Scan and index a codebase"""
    data = request.get_json()
    if not data or "root_path" not in data:
        return jsonify({"error": "root_path is required"}), 400
    
    root_path = data.get("root_path", ".")
    path = Path(root_path)
    
    if not path.exists():
        return jsonify({"error": f"Path does not exist: {root_path}"}), 400
    
    if not path.is_dir():
        return jsonify({"error": f"Path is not a directory: {root_path}"}), 400

    try:
        search_service.root_path = path
        search_service.index_codebase()
        return jsonify({
            "status": "success",
            "files_indexed": search_service.file_count(),
            "message": f"Indexed {search_service.file_count()} files"
        })
    except Exception as e:
        current_app.logger.error(f"Scan error: {e}")
        return jsonify({"error": str(e)}), 500


@routes_bp.route("/search", methods=["POST"])
def search():
    """Search the indexed codebase"""
    if not search_service or not search_service.is_indexed():
        return jsonify({"error": "Codebase not indexed. Call /scan first."}), 400
    
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "query is required"}), 400
    
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400

    try:
        max_results = int(data.get("max_results", 10))
        results = search_service.search(query, max_results=max_results)
        
        return jsonify({
            "results": results,
            "total_matches": len(results)
        })
    except Exception as e:
        current_app.logger.error(f"Search error: {e}")
        return jsonify({"error": str(e)}), 500


@routes_bp.route("/graph", methods=["GET"])
@routes_bp.route("/api/graph", methods=["GET"])
def graph():
    """Get codebase relationship graph"""
    if not search_service:
        return jsonify({"error": "Search service not initialized"}), 500
    
    if not search_service.is_indexed():
        return jsonify({
            "error": "Codebase not indexed. Call /scan first.",
            "nodes": [],
            "links": []
        }), 400
    
    try:
        graph_data = graph_service.get_graph_data()
        # Ensure we always return nodes and links arrays
        if not isinstance(graph_data, dict):
            graph_data = {"nodes": [], "links": []}
        if "nodes" not in graph_data:
            graph_data["nodes"] = []
        if "links" not in graph_data:
            graph_data["links"] = []
        
        current_app.logger.info(f"Returning graph with {len(graph_data.get('nodes', []))} nodes and {len(graph_data.get('links', []))} links")
        return jsonify(graph_data)
    except Exception as e:
        current_app.logger.error(f"Graph error: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "nodes": [], "links": []}), 500


@routes_bp.route("/semantic_search", methods=["POST"])
def semantic_search():
    """Semantic search using embeddings"""
    if not semantic_service:
        return jsonify({"error": "Semantic service not initialized"}), 500
    
    if not semantic_service.is_indexed():
        return jsonify({
            "error": "Vector index not built. Call /build_semantic_index first.",
            "results": [],
            "explanation": ""
        }), 400
    
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "query is required"}), 400
    
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400
    
    try:
        top_k = int(data.get("max_results", 5))
        
        # Perform semantic search
        results = semantic_service.semantic_search(query, top_k=top_k)
        
        # Get file snippets for explanation
        snippets = []
        root_path = search_service.root_path if search_service else Path(".")
        
        for result in results:
            file_path = result["file_path"]
            full_path = root_path / file_path
            try:
                if full_path.exists():
                    content = full_path.read_text(errors="ignore")
                    snippets.append(f"File: {file_path}\n{content[:1000]}")  # First 1000 chars
            except Exception as e:
                current_app.logger.warning(f"Could not read {file_path}: {e}")
        
        # Generate explanation if OpenAI is available
        explanation = ""
        if semantic_service.client and snippets:
            explanation = semantic_service.explain_results(query, snippets)
        
        return jsonify({
            "query": query,
            "results": results,
            "explanation": explanation,
            "total_matches": len(results)
        })
    except Exception as e:
        current_app.logger.error(f"Semantic search error: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@routes_bp.route("/build_semantic_index", methods=["POST"])
def build_semantic_index():
    """Build semantic vector index from codebase"""
    if not semantic_service:
        return jsonify({"error": "Semantic service not initialized"}), 500
    
    data = request.get_json() or {}
    root_path = data.get("root_path", ".")
    path = Path(root_path)
    
    if not path.exists():
        return jsonify({"error": f"Path does not exist: {root_path}"}), 400
    
    if not path.is_dir():
        return jsonify({"error": f"Path is not a directory: {root_path}"}), 400
    
    try:
        semantic_service.set_root_path(root_path)
        semantic_service.build_vector_index()
        semantic_service.save_file_map()
        
        return jsonify({
            "status": "success",
            "files_indexed": semantic_service.file_count(),
            "message": f"Built vector index for {semantic_service.file_count()} files"
        })
    except Exception as e:
        current_app.logger.error(f"Build semantic index error: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

