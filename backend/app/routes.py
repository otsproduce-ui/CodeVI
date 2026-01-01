"""
API Routes - All endpoints with error handling
"""
from flask import Blueprint, request, jsonify, current_app
from pathlib import Path
import re
from app.search_service import SearchService
from app.graph_service import GraphService
from app.semantic_service import SemanticSearchService
from app.explanation_service import ExplanationService
from app.contextual_search import ContextualSearch
from app.hybrid_pipeline_adapter import HybridPipelineAdapter
from app.code_graph_builder import CodeGraphBuilder

routes_bp = Blueprint("routes", __name__)

# Initialize services (will be set up in create_app)
search_service = None
graph_service = None
semantic_service = None
explanation_service = None
contextual_search_engine = None
hybrid_pipeline_adapter = None
graph_builder = None


def init_services(app):
    """Initialize services with app config"""
    global search_service, graph_service, semantic_service, explanation_service, contextual_search_engine, hybrid_pipeline_adapter, graph_builder, graph_builder
    search_service = SearchService(".", app.config["INDEX_PATH"])
    search_service.load_index()
    graph_service = GraphService(search_service)
    graph_builder = CodeGraphBuilder(search_service)
    
    # Initialize semantic service with BM25 service for hybrid search
    semantic_service = SemanticSearchService(
        root_path=".",
        vector_index_file=app.config.get("VECTOR_INDEX_PATH", "vector.index"),
        bm25_service=search_service  # Enable hybrid search
    )
    semantic_service.load_index()
    
    # Initialize explanation service
    explanation_service = ExplanationService(semantic_service, search_service)
    
    # Initialize contextual search engine (unified)
    contextual_search_engine = ContextualSearch(
        search_service=search_service,
        semantic_service=semantic_service,
        graph_service=graph_service,
        explanation_service=explanation_service
    )
    
    # Initialize hybrid pipeline adapter
    hybrid_pipeline_adapter = HybridPipelineAdapter(search_service)
    
    # Initialize code graph builder
    graph_builder = CodeGraphBuilder(search_service)


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
        
        # Also build semantic index if semantic service is available
        semantic_indexed = False
        semantic_snippets = 0
        if semantic_service:
            try:
                semantic_service.set_root_path(root_path)
                semantic_service.build_vector_index()
                semantic_indexed = True
                semantic_snippets = semantic_service.file_count()
            except Exception as e:
                current_app.logger.warning(f"Could not build semantic index: {e}")
        
        message = f"Indexed {search_service.file_count()} files"
        if semantic_indexed:
            message += f" and {semantic_snippets} code snippets"
        
        return jsonify({
            "status": "success",
            "count": search_service.file_count(),  # Frontend expects 'count'
            "files_indexed": search_service.file_count(),  # Keep for backward compatibility
            "semantic_indexed": semantic_indexed,
            "semantic_snippets": semantic_snippets,
            "message": message
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
        use_hybrid = data.get("use_hybrid", True)  # Default to hybrid search
        adaptive = data.get("adaptive", True)  # Default to adaptive weights
        semantic_weight = data.get("semantic_weight")  # None = adaptive
        lexical_weight = data.get("lexical_weight")  # None = adaptive
        
        # Convert to float if provided
        if semantic_weight is not None:
            semantic_weight = float(semantic_weight)
        if lexical_weight is not None:
            lexical_weight = float(lexical_weight)
        
        results = search_service.search(
            query, 
            max_results=max_results,
            use_hybrid=use_hybrid,
            semantic_weight=semantic_weight,
            lexical_weight=lexical_weight,
            adaptive=adaptive
        )
        
        return jsonify({
            "results": results,
            "total_matches": len(results),
            "search_type": "hybrid" if use_hybrid else "semantic"
        })
    except Exception as e:
        current_app.logger.error(f"Search error: {e}")
        return jsonify({"error": str(e)}), 500


@routes_bp.route("/graph", methods=["GET"])
@routes_bp.route("/api/graph", methods=["GET"])
def graph():
    """Get codebase relationship graph - builds actual graph structure from indexed data"""
    if not search_service or not graph_builder:
        return jsonify({"error": "Services not initialized"}), 500
    
    if not search_service.is_indexed():
        return jsonify({
            "error": "Codebase not indexed. Call /scan first.",
            "nodes": [],
            "links": [],
            "edges": []
        }), 400
    
    try:
        # Get all indexed items from search service
        all_items = []
        if hasattr(search_service, 'semantic_index_data') and search_service.semantic_index_data:
            all_items = search_service.semantic_index_data
        elif hasattr(search_service, 'engine') and search_service.engine:
            # Fallback: try to get from BM25 engine if available
            # This is a simplified approach - in production you'd want a better way
            pass
        
        if not all_items:
            # Return empty graph structure
            return jsonify({
                "nodes": [],
                "links": [],
                "edges": [],
                "flow_chains": []
            })
        
        # Build graph from indexed items
        graph_data = graph_builder.build_from_search_results(all_items[:50])  # Limit to first 50 for performance
        
        # Convert edges to links for compatibility
        links = []
        for edge in graph_data.get("edges", []):
            links.append({
                "source": edge.get("source"),
                "target": edge.get("target"),
                "type": edge.get("type", "related")
            })
        
        result = {
            "nodes": graph_data.get("nodes", []),
            "links": links,  # For compatibility with old frontend
            "edges": graph_data.get("edges", []),  # New format
            "flow_chains": graph_data.get("flow_chains", []),
            "stats": graph_data.get("stats", {})
        }
        
        current_app.logger.info(f"Returning graph with {len(result.get('nodes', []))} nodes and {len(result.get('edges', []))} edges")
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Graph error: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "nodes": [], "links": [], "edges": []}), 500


@routes_bp.route("/contextual_search", methods=["POST"])
def contextual_search():
    """Contextual search with relationship graph"""
    if not search_service or not graph_service:
        return jsonify({"error": "Services not initialized"}), 500
    
    if not search_service.is_indexed():
        return jsonify({"error": "Codebase not indexed. Call /scan first."}), 400
    
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "query is required"}), 400
    
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400
    
    try:
        depth = int(data.get("depth", 2))  # Default depth of 2
        contextual_results = graph_service.contextual_search(query, depth=depth)
        
        return jsonify({
            "query": query,
            "results": contextual_results,
            "total_matches": len(contextual_results)
        })
    except Exception as e:
        current_app.logger.error(f"Contextual search error: {e}")
        return jsonify({"error": str(e)}), 500


@routes_bp.route("/hybrid-search", methods=["POST"])
def hybrid_search_pipeline():
    """
    Hybrid Search Pipeline endpoint - Complete architecture with preprocessing, lexical, semantic, and ranking
    """
    if not hybrid_pipeline_adapter:
        return jsonify({"error": "Hybrid pipeline adapter not initialized"}), 500
    
    if not search_service or not search_service.is_indexed():
        return jsonify({"error": "Codebase not indexed. Call /scan first."}), 400
    
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "query is required"}), 400
    
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400
    
    try:
        top_k = int(data.get("max_results", 10))
        alpha = data.get("alpha")  # Semantic weight
        beta = data.get("beta")  # Lexical weight
        gamma = data.get("gamma")  # Context weight
        
        # Convert to float if provided
        if alpha is not None:
            alpha = float(alpha)
        if beta is not None:
            beta = float(beta)
        if gamma is not None:
            gamma = float(gamma)
        
        # Initialize adapter if needed (with graph and explanation services)
        hybrid_pipeline_adapter.initialize(
            graph_service=graph_service,
            explanation_service=explanation_service
        )
        
        # Search using pipeline
        results = hybrid_pipeline_adapter.search(
            query,
            top_k=top_k,
            alpha=alpha,
            beta=beta,
            gamma=gamma
        )
        
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Hybrid search pipeline error: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@routes_bp.route("/flow_graph", methods=["GET", "POST"])
def flow_graph():
    """Build a complete flow graph for a query - returns actual nodes/edges structure"""
    if not search_service or not graph_service or not graph_builder:
        return jsonify({"error": "Services not initialized"}), 500
    
    if not search_service.is_indexed():
        return jsonify({"error": "Codebase not indexed. Call /scan first."}), 400
    
    # Support both GET (query param) and POST (JSON body)
    if request.method == "GET":
        query = request.args.get("query", "").strip()
    else:
        data = request.get_json() or {}
        query = data.get("query", "").strip()
    
    if not query:
        return jsonify({"error": "Query cannot be empty"}), 400
    
    try:
        # Get contextual search results (with related components)
        if contextual_search_engine:
            contextual_results = contextual_search_engine.search(
                query=query,
                top_k=10,
                include_related=True,
                include_flow=False,  # We'll build flow ourselves
                include_explanation=False,
                depth=2
            )
            
            # Build graph from contextual results using graph_builder
            graph_data = graph_builder.build_from_contextual_results(contextual_results)
        else:
            # Fallback: use regular search
            search_results = search_service.search(query, max_results=20)
            graph_data = graph_builder.build_from_search_results(search_results)
        
        # Ensure we return the correct structure with nodes and edges
        result = {
            "query": query,
            "nodes": graph_data.get("nodes", []),
            "edges": graph_data.get("edges", []),  # Use 'edges' not 'links' for flow_graph
            "flow_chains": graph_data.get("flow_chains", []),
            "stats": graph_data.get("stats", {})
        }
        
        current_app.logger.info(f"Flow graph for '{query}': {len(result['nodes'])} nodes, {len(result['edges'])} edges")
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Flow graph error: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@routes_bp.route("/file", methods=["GET"])
@routes_bp.route("/api/v1/file", methods=["GET"])
def get_file_content():
    """
    Serves the content of a specific file.
    Accepts a path relative to the codebase root or absolute path.
    """
    file_path_str = request.args.get("path")
    if not file_path_str:
        return jsonify({"error": "File path is required"}), 400

    try:
        # Get codebase root from search_service
        base_dir = Path(search_service.root_path).resolve() if search_service else Path(".").resolve()
        
        # Normalize the path string - handle Windows paths that lost backslashes
        # Example: "C:UsersomertNew folderappsapimain.py" -> try to find "main.py" in codebase
        normalized_path_str = file_path_str
        
        # If it looks like a Windows absolute path without backslashes (C:Users...)
        # or if it's a malformed path, try to find the file by name
        if re.match(r'^[A-Za-z]:[^\\/]', normalized_path_str) or '\\' not in normalized_path_str and '/' not in normalized_path_str:
            # Extract filename from the path
            file_name = Path(normalized_path_str).name
            
            # Search for the file in the codebase by name
            found_paths = list(base_dir.rglob(file_name))
            
            if len(found_paths) == 1:
                # Only one file with this name - use it
                final_path = found_paths[0]
            elif len(found_paths) > 1:
                # Multiple files with same name - try to match by path segments
                # Extract path segments from the malformed path
                # Try to match the last few segments
                path_segments = [s for s in normalized_path_str.split('/') if s]
                if len(path_segments) >= 2:
                    # Try to match last 2-3 segments
                    last_segments = path_segments[-2:]
                    for candidate in found_paths:
                        candidate_str = str(candidate).replace('\\', '/').lower()
                        if all(seg.lower() in candidate_str for seg in last_segments):
                            final_path = candidate
                            break
                    else:
                        # No match found, use first one
                        final_path = found_paths[0]
                else:
                    # Can't match, use first one
                    final_path = found_paths[0]
            else:
                # File not found - try to construct path from base_dir
                # Remove drive letter and try as relative path
                relative_part = re.sub(r'^[A-Za-z]:', '', normalized_path_str).lstrip('/')
                final_path = (base_dir / relative_part).resolve()
        else:
            # Try to resolve the path normally
            requested_path = Path(file_path_str)
            
            # If it's an absolute path, check if it's within the codebase
            if requested_path.is_absolute():
                resolved = requested_path.resolve()
                if not str(resolved).startswith(str(base_dir)):
                    return jsonify({"error": "Access denied: Path is outside the allowed codebase directory"}), 403
                final_path = resolved
            else:
                # Relative path - resolve relative to codebase root
                final_path = (base_dir / requested_path).resolve()
        
        # Security check: ensure resolved path is still within base_dir
        if not str(final_path.resolve()).startswith(str(base_dir)):
            return jsonify({"error": "Access denied: Path is outside the allowed codebase directory"}), 403
        
        if not final_path.exists():
            return jsonify({"error": f"File not found: {file_path_str}"}), 404
        
        if not final_path.is_file():
            return jsonify({"error": f"Path is not a file: {file_path_str}"}), 400

        # Read file content
        with open(final_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        return jsonify({
            "content": content,
            "lines": content.splitlines()
        })
    except Exception as e:
        current_app.logger.error(f"Error reading file {file_path_str}: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Could not read file: {str(e)}"}), 500


@routes_bp.route("/related_files", methods=["POST"])
def related_files():
    """Get files related to a specific file path"""
    if not search_service or not graph_service:
        return jsonify({"error": "Services not initialized"}), 500
    
    if not search_service.is_indexed():
        return jsonify({"error": "Codebase not indexed. Call /scan first."}), 400
    
    data = request.get_json()
    if not data or "file_path" not in data:
        return jsonify({"error": "file_path is required"}), 400
    
    file_path = data.get("file_path", "").strip()
    if not file_path:
        return jsonify({"error": "File path cannot be empty"}), 400
    
    try:
        # First, find the file in the index
        if not hasattr(search_service, 'semantic_index_data') or not search_service.semantic_index_data:
            search_service.load_semantic_index()
        
        # Find items matching this file path
        matching_items = []
        for item in search_service.semantic_index_data:
            if file_path in item.get("file_path", "") or item.get("file_path", "") in file_path:
                matching_items.append(item)
        
        if not matching_items:
            return jsonify({
                "file_path": file_path,
                "related_files": [],
                "related_components": [],
                "message": "File not found in index"
            })
        
        # Get related components for the first matching item (or all if multiple)
        all_related = []
        seen_files = set()
        
        for item in matching_items[:3]:  # Limit to first 3 items to avoid too many results
            related = graph_service.find_related(item)
            for rel in related:
                rel_file = rel.get("file_path", "")
                if rel_file and rel_file not in seen_files:
                    seen_files.add(rel_file)
                    all_related.append({
                        "file_path": rel_file,
                        "name": rel.get("name", ""),
                        "type": rel.get("type", ""),
                        "relation_type": rel.get("relation_type", "related"),
                        "relation_strength": rel.get("relation_strength", "weak"),
                        "direction": rel.get("direction", ""),
                        "start_line": rel.get("start_line"),
                        "context": rel.get("context", "")
                    })
        
        # Group by file path
        files_dict = {}
        for rel in all_related:
            file_path_key = rel["file_path"]
            if file_path_key not in files_dict:
                files_dict[file_path_key] = {
                    "file_path": file_path_key,
                    "components": [],
                    "relation_count": 0
                }
            files_dict[file_path_key]["components"].append(rel)
            files_dict[file_path_key]["relation_count"] += 1
        
        related_files_list = list(files_dict.values())
        
        return jsonify({
            "file_path": file_path,
            "related_files": related_files_list,
            "related_components": all_related,
            "total_related": len(related_files_list)
        })
    except Exception as e:
        current_app.logger.error(f"Related files error: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


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
        use_hybrid = data.get("use_hybrid", True)  # Default to hybrid search
        adaptive = data.get("adaptive", True)  # Default to adaptive weights
        semantic_weight = data.get("semantic_weight")
        lexical_weight = data.get("lexical_weight")
        
        # Convert to float if provided
        if semantic_weight is not None:
            semantic_weight = float(semantic_weight)
        if lexical_weight is not None:
            lexical_weight = float(lexical_weight)
        
        # Use SearchService hybrid search if available, otherwise fall back to semantic_service
        if use_hybrid and search_service and search_service.is_semantic_indexed_check():
            # Use hybrid search from SearchService with adaptive weights
            results = search_service.hybrid_search(
                query, 
                max_results=top_k,
                semantic_weight=semantic_weight,
                lexical_weight=lexical_weight,
                adaptive=adaptive
            )
            search_type = "hybrid"
        else:
            # Fall back to semantic service only
            results = semantic_service.semantic_search(query, top_k=top_k, use_hybrid=False)
            search_type = "semantic"
        
        # Generate flow explanation
        flow_explanation = ""
        if explanation_service:
            flow_explanation = explanation_service.explain_flow(query, results)
        
        # Also get simple explanation from semantic service
        simple_explanation = semantic_service.explain_results(query, results, include_context=True)
        
        return jsonify({
            "query": query,
            "results": results,
            "explanation": simple_explanation,
            "flow_explanation": flow_explanation,
            "total_matches": len(results),
            "search_type": search_type
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

