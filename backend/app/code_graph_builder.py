"""
Code Graph Builder - Builds actual graph structure (nodes/edges) from search results
בונה מבנה גרף אמיתי (nodes/edges) מתוצאות חיפוש
"""
from typing import List, Dict, Set, Tuple
from collections import defaultdict


class CodeGraphBuilder:
    """
    Builds graph structure from search results and code relationships.
    Converts search results into nodes and edges for visualization.
    """
    
    def __init__(self, search_service=None):
        self.search_service = search_service
        self.node_map = {}  # id -> node data
        self.edge_map = {}  # (source, target) -> edge data
    
    def build_from_search_results(self, search_results: List[Dict]) -> Dict:
        """
        Build graph from search results.
        
        Args:
            search_results: List of search result dicts with file_path, name, type, etc.
        
        Returns:
            {
                "nodes": [...],
                "edges": [...],
                "flow_chains": [...]
            }
        """
        nodes = []
        edges = []
        node_ids = set()
        
        # Step 1: Create nodes from search results
        for result in search_results:
            node_id = self._get_node_id(result)
            if node_id not in node_ids:
                node = self._create_node(result, node_id)
                nodes.append(node)
                node_ids.add(node_id)
                self.node_map[node_id] = node
        
        # Step 2: Create edges based on relationships
        for result in search_results:
            source_id = self._get_node_id(result)
            
            # Create edges from API calls
            api_calls = result.get("api_calls", [])
            for api_call in api_calls:
                endpoint = api_call.get("endpoint", "")
                if endpoint:
                    # Find backend route that handles this endpoint
                    target_id = self._find_route_node(endpoint, nodes)
                    if target_id:
                        edge = self._create_edge(
                            source_id, 
                            target_id, 
                            "calls_endpoint",
                            {"endpoint": endpoint, "method": api_call.get("method", "GET")}
                        )
                        if edge and edge["id"] not in [e["id"] for e in edges]:
                            edges.append(edge)
            
            # Create edges from event listeners
            event_listeners = result.get("event_listeners", [])
            for listener in event_listeners:
                handler = listener.get("handler", "")
                if handler:
                    # Find JS function that handles this event
                    target_id = self._find_handler_node(handler, nodes)
                    if target_id:
                        edge = self._create_edge(
                            source_id,
                            target_id,
                            "handles_event",
                            {"event": listener.get("event", ""), "handler": handler}
                        )
                        if edge and edge["id"] not in [e["id"] for e in edges]:
                            edges.append(edge)
            
            # Create edges from routes (backend -> function)
            routes = result.get("routes", [])
            for route in routes:
                path = route.get("path", "")
                if path:
                    # Find function that handles this route
                    target_id = self._find_route_handler(path, nodes)
                    if target_id:
                        edge = self._create_edge(
                            source_id,
                            target_id,
                            "handles_route",
                            {"path": path, "method": route.get("method", "GET")}
                        )
                        if edge and edge["id"] not in [e["id"] for e in edges]:
                            edges.append(edge)
            
            # Create edges from function calls (relations)
            relations = result.get("relations", [])
            for relation in relations:
                if isinstance(relation, str):
                    # Find function with this name
                    target_id = self._find_function_node(relation, nodes, result.get("file_path", ""))
                    if target_id:
                        edge = self._create_edge(
                            source_id,
                            target_id,
                            "calls_function",
                            {"function": relation}
                        )
                        if edge and edge["id"] not in [e["id"] for e in edges]:
                            edges.append(edge)
        
        # Step 3: Identify flow chains
        flow_chains = self._identify_flow_chains(nodes, edges)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "flow_chains": flow_chains,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "flow_chains_count": len(flow_chains)
            }
        }
    
    def _get_node_id(self, result: Dict) -> str:
        """Generate unique node ID from result"""
        file_path = result.get("file_path", "")
        name = result.get("name") or result.get("full_name", "")
        start_line = result.get("start_line", 0)
        
        if name:
            return f"{file_path}::{name}::{start_line}"
        return f"{file_path}::{start_line}"
    
    def _normalize_file_path(self, file_path: str) -> str:
        """Convert absolute path to relative path if possible"""
        if not file_path:
            return file_path
        
        try:
            path = Path(file_path)
            # If it's an absolute path and we have a search_service with root_path
            if path.is_absolute() and self.search_service:
                root = self.search_service.root_path.resolve()
                try:
                    # Try to make it relative to root
                    relative = path.relative_to(root)
                    # Convert to forward slashes for web compatibility
                    return str(relative).replace('\\', '/')
                except ValueError:
                    # Path is not within root, return as is but normalize separators
                    return str(path).replace('\\', '/')
            else:
                # Already relative or no root_path, just normalize separators
                return str(path).replace('\\', '/')
        except Exception:
            # If anything fails, just normalize separators
            return str(file_path).replace('\\', '/')
    
    def _create_node(self, result: Dict, node_id: str) -> Dict:
        """Create node dict from result"""
        file_path = result.get("file_path", "")
        # Normalize file path to relative path
        normalized_path = self._normalize_file_path(file_path)
        
        name = result.get("name") or result.get("full_name", "")
        node_type = result.get("type", "code")
        language = result.get("language", "")
        
        # Detect context (use original path for detection)
        context = self._detect_context(file_path, language, node_type)
        
        return {
            "id": node_id,
            "label": name or normalized_path.split("/")[-1],
            "name": name,
            "file_path": normalized_path,  # Use normalized (relative) path
            "file": normalized_path,  # For compatibility
            "type": node_type,
            "language": language,
            "context": context,
            "start_line": result.get("start_line", 0),
            "line": result.get("start_line", 0),  # For compatibility
            "score": result.get("score", 0)
        }
    
    def _detect_context(self, file_path: str, language: str, node_type: str) -> str:
        """Detect if node is frontend or backend"""
        file_lower = file_path.lower()
        
        # Frontend indicators
        if any(indicator in file_lower for indicator in ['.html', '.js', '.jsx', '.ts', '.tsx', 'frontend', 'client']):
            return "frontend"
        if language in ["javascript", "typescript", "html"]:
            return "frontend"
        if node_type in ["button", "element", "form", "input"]:
            return "frontend"
        
        # Backend indicators
        if any(indicator in file_lower for indicator in ['.py', 'backend', 'server', 'api', 'routes']):
            return "backend"
        if language == "python":
            return "backend"
        if node_type == "route":
            return "backend"
        
        return "unknown"
    
    def _create_edge(self, source_id: str, target_id: str, relation_type: str, metadata: Dict = None) -> Dict:
        """Create edge dict"""
        edge_id = f"{source_id}-{target_id}-{relation_type}"
        
        edge = {
            "id": edge_id,
            "source": source_id,
            "target": target_id,
            "type": relation_type,
            "relation_type": relation_type  # For compatibility
        }
        
        if metadata:
            edge.update(metadata)
        
        return edge
    
    def _find_route_node(self, endpoint: str, nodes: List[Dict]) -> str:
        """Find node that represents a route handling this endpoint"""
        # Normalize endpoint
        normalized = self._normalize_endpoint(endpoint)
        
        for node in nodes:
            # Check if node has routes
            if node.get("type") == "route":
                node_path = node.get("file_path", "")
                if normalized in node_path.lower() or endpoint in node_path:
                    return node["id"]
            
            # Check node name/label
            node_name = (node.get("name") or node.get("label", "")).lower()
            if normalized in node_name or endpoint.lower() in node_name:
                return node["id"]
        
        return None
    
    def _find_handler_node(self, handler_name: str, nodes: List[Dict]) -> str:
        """Find JS function node that handles an event"""
        handler_lower = handler_name.lower()
        
        for node in nodes:
            node_name = (node.get("name") or node.get("label", "")).lower()
            if handler_lower in node_name or node_name in handler_lower:
                # Check if it's a JS function
                if node.get("context") == "frontend" or node.get("language") in ["javascript", "typescript"]:
                    return node["id"]
        
        return None
    
    def _find_route_handler(self, path: str, nodes: List[Dict]) -> str:
        """Find function that handles a route"""
        path_lower = path.lower()
        
        for node in nodes:
            # Check if node is a Python function in routes file
            if node.get("context") == "backend" and node.get("type") == "function":
                node_file = node.get("file_path", "").lower()
                if "route" in node_file or "api" in node_file:
                    node_name = (node.get("name") or "").lower()
                    if path_lower in node_name or node_name in path_lower:
                        return node["id"]
        
        return None
    
    def _find_function_node(self, function_name: str, nodes: List[Dict], current_file: str = "") -> str:
        """Find function node by name"""
        func_lower = function_name.lower()
        
        for node in nodes:
            node_name = (node.get("name") or node.get("label", "")).lower()
            if func_lower == node_name or func_lower in node_name:
                # Prefer functions in same file
                if current_file and node.get("file_path") == current_file:
                    return node["id"]
                return node["id"]
        
        return None
    
    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint for matching"""
        if not endpoint:
            return ""
        normalized = endpoint.strip('/').lower()
        if normalized.startswith('api/'):
            normalized = normalized[4:]
        return normalized
    
    def _identify_flow_chains(self, nodes: List[Dict], edges: List[Dict]) -> List[List[str]]:
        """
        Identify complete flow chains: HTML → JS → API → Backend
        """
        chains = []
        
        # Find HTML elements (buttons, forms)
        html_nodes = [n for n in nodes if n.get("type") in ["button", "element", "form", "input"]]
        
        for html_node in html_nodes:
            chain = [html_node["id"]]
            
            # Find JS handlers (handles_event edges)
            event_edges = [e for e in edges if e.get("source") == html_node["id"] and e.get("type") == "handles_event"]
            for event_edge in event_edges:
                js_node_id = event_edge["target"]
                if js_node_id not in chain:
                    chain.append(js_node_id)
                
                # Find API calls from JS (calls_endpoint edges)
                api_edges = [e for e in edges if e.get("source") == js_node_id and e.get("type") == "calls_endpoint"]
                for api_edge in api_edges:
                    api_node_id = api_edge["target"]
                    if api_node_id not in chain:
                        chain.append(api_node_id)
                    
                    # Find backend handlers (handles_route edges)
                    backend_edges = [e for e in edges if e.get("source") == api_node_id and e.get("type") == "handles_route"]
                    for backend_edge in backend_edges:
                        backend_node_id = backend_edge["target"]
                        if backend_node_id not in chain:
                            chain.append(backend_node_id)
                            chains.append(chain.copy())
                            chain.pop()  # Backtrack
                    if api_node_id in chain:
                        chain.pop()  # Backtrack
                if js_node_id in chain:
                    chain.pop()  # Backtrack
        
        return chains[:10]  # Limit to top 10 chains
    
    def build_from_contextual_results(self, contextual_results: List[Dict]) -> Dict:
        """
        Build graph from contextual search results (with related components).
        This is used when we have results with 'related' field.
        """
        nodes = []
        edges = []
        node_ids = set()
        
        for ctx_result in contextual_results:
            base = ctx_result.get("base", {})
            base_id = self._get_node_id(base)
            
            # Add base node
            if base_id not in node_ids:
                node = self._create_node(base, base_id)
                nodes.append(node)
                node_ids.add(base_id)
            
            # Add related nodes and edges
            related = ctx_result.get("related", [])
            for rel in related:
                rel_id = self._get_node_id(rel)
                
                # Add related node
                if rel_id not in node_ids:
                    rel_node = self._create_node(rel, rel_id)
                    nodes.append(rel_node)
                    node_ids.add(rel_id)
                
                # Create edge
                relation_type = rel.get("relation_type", "related")
                edge = self._create_edge(
                    base_id,
                    rel_id,
                    relation_type,
                    {
                        "strength": rel.get("relation_strength", "medium"),
                        "direction": rel.get("direction", "")
                    }
                )
                if edge["id"] not in [e["id"] for e in edges]:
                    edges.append(edge)
        
        # Identify flow chains
        flow_chains = self._identify_flow_chains(nodes, edges)
        
        return {
            "nodes": nodes,
            "edges": edges,
            "flow_chains": flow_chains,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "flow_chains_count": len(flow_chains)
            }
        }

