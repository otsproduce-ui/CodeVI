"""
Graph Service - Contextual relationships and graph processing
Enhanced with relationship finding and contextual search
"""
from typing import List, Dict, Optional


class GraphService:
    """Service for finding relationships and building contextual graphs"""
    
    def __init__(self, search_service):
        self.search_service = search_service
    
    def _normalize_endpoint(self, endpoint: str) -> str:
        """
        Normalize endpoint for matching (remove /api/, leading/trailing slashes).
        Example: '/api/search' -> 'search', '/api/users/123' -> 'users/123'
        """
        if not endpoint:
            return ""
        
        # Remove leading/trailing slashes
        normalized = endpoint.strip('/')
        
        # Remove /api/ prefix if present
        if normalized.startswith('api/'):
            normalized = normalized[4:]
        elif normalized.startswith('/api/'):
            normalized = normalized[5:]
        
        return normalized.lower()
    
    def _detect_context(self, item: Dict) -> str:
        """
        Detect context (frontend/backend) based on file path and language.
        """
        file_path = item.get("file_path", "").lower()
        language = item.get("language", "").lower()
        
        # Frontend indicators
        if any(indicator in file_path for indicator in ['frontend', 'client', 'src', 'public', 'static']):
            return "frontend"
        if language in ["javascript", "typescript", "html", "css"]:
            return "frontend"
        
        # Backend indicators
        if any(indicator in file_path for indicator in ['backend', 'server', 'api', 'routes', 'app']):
            return "backend"
        if language == "python":
            return "backend"
        
        # Default based on type
        item_type = item.get("type", "").lower()
        if item_type in ["route", "api_call"]:
            if "api" in file_path or "route" in file_path:
                return "backend"
            return "frontend"
        
        return "unknown"
    
    def get_graph_data(self):
        """Get graph data from search service"""
        return self.search_service.get_graph()
    
    def find_related(self, base_item: Dict) -> List[Dict]:
        """
        Find components related to a base item with bidirectional relationships.
        Looks for:
        - Function calls (relations) - bidirectional
        - API endpoint matches (frontend ↔ backend)
        - Event handler connections (HTML ↔ JS)
        - Import relationships
        """
        related = []
        base_name = base_item.get("name", "")
        base_type = base_item.get("type", "")
        base_file = base_item.get("file_path", "")
        base_language = base_item.get("language", "")
        
        # Get all indexed items
        all_items = []
        if hasattr(self.search_service, 'semantic_index_data'):
            all_items = self.search_service.semantic_index_data
        elif hasattr(self.search_service, 'engine') and self.search_service.engine:
            # Fallback to BM25 engine data if available
            pass
        
        for item in all_items:
            # Skip self
            if item.get("file_path") == base_file and item.get("name") == base_name:
                continue
            
            item_language = item.get("language", "")
            
            # 1. Function call relationships (bidirectional)
            # Check if base function is called by this item
            relations = item.get("relations", [])
            if base_name in relations or any(base_name in rel for rel in relations):
                related.append({
                    **item,
                    "relation_type": "calls_function",
                    "relation_strength": "strong",
                    "direction": "outgoing"
                })
            
            # Check if base function calls this item
            base_relations = base_item.get("relations", [])
            if item.get("name", "") in base_relations or any(item.get("name", "") in rel for rel in base_relations):
                related.append({
                    **item,
                    "relation_type": "called_by_function",
                    "relation_strength": "strong",
                    "direction": "incoming"
                })
            
            # 2. API endpoint matches (frontend ↔ backend) - CRITICAL for linking
            # If base is a frontend API call, find backend route
            base_context = self._detect_context(base_item)
            item_context = self._detect_context(item)
            
            if base_type == "api_call" and base_context == "frontend":
                base_endpoint = ""
                base_endpoint_normalized = ""
                
                # Get endpoint from api_calls array
                for api_call in base_item.get("api_calls", []):
                    endpoint = api_call.get("endpoint", "")
                    if endpoint:
                        base_endpoint = endpoint
                        # Use normalized endpoint if available, otherwise normalize
                        base_endpoint_normalized = api_call.get("endpoint_normalized", self._normalize_endpoint(endpoint))
                        break
                
                if base_endpoint and base_endpoint_normalized:
                    # Check if item is a route handler (backend)
                    if item_context == "backend":
                        routes = item.get("routes", [])
                        for route in routes:
                            route_path = route.get("path", "")
                            route_normalized = self._normalize_endpoint(route_path)
                            
                            # Match normalized endpoints
                            if base_endpoint_normalized == route_normalized or \
                               base_endpoint_normalized in route_normalized or \
                               route_normalized in base_endpoint_normalized:
                                related.append({
                                    **item,
                                    "relation_type": "handles_endpoint",
                                    "relation_strength": "strong",
                                    "direction": "backend",
                                    "endpoint_match": base_endpoint,
                                    "context": item_context
                                })
                                break
                        
                        # Also check if item name matches endpoint
                        item_name_normalized = self._normalize_endpoint(item.get("name", ""))
                        if base_endpoint_normalized == item_name_normalized or \
                           base_endpoint_normalized in item_name_normalized:
                            related.append({
                                **item,
                                "relation_type": "endpoint_handler",
                                "relation_strength": "medium",
                                "direction": "backend",
                                "context": item_context
                            })
            
            # If base is a backend route, find frontend calls
            if base_type == "route" and base_context == "backend":
                route_path = base_item.get("name", "")
                normalized_route = self._normalize_endpoint(route_path)
                
                # Check if item calls this route (frontend)
                if item_context == "frontend":
                    api_calls = item.get("api_calls", [])
                    for api_call in api_calls:
                        endpoint = api_call.get("endpoint", "")
                        endpoint_normalized = api_call.get("endpoint_normalized", self._normalize_endpoint(endpoint))
                        
                        # Match normalized endpoints
                        if normalized_route == endpoint_normalized or \
                           normalized_route in endpoint_normalized or \
                           endpoint_normalized in normalized_route:
                            related.append({
                                **item,
                                "relation_type": "calls_route",
                                "relation_strength": "strong",
                                "direction": "frontend",
                                "endpoint_match": endpoint,
                                "context": item_context
                            })
                            break
            
            # 3. Event handler connections (HTML ↔ JS)
            if base_type in ["button", "element", "input"] and base_language == "html":
                elem_id = base_item.get("attributes", {}).get("id", "")
                elem_class = " ".join(base_item.get("attributes", {}).get("class", []))
                
                # Check if item has event listener for this element
                event_listeners = item.get("event_listeners", [])
                for listener in event_listeners:
                    handler = listener.get("handler", "").lower()
                    if elem_id and elem_id.lower() in handler:
                        related.append({
                            **item,
                            "relation_type": "handles_event",
                            "relation_strength": "strong",
                            "direction": "js_handler"
                        })
                        break
                    if elem_class and any(cls.lower() in handler for cls in elem_class.split()):
                        related.append({
                            **item,
                            "relation_type": "handles_event",
                            "relation_strength": "medium",
                            "direction": "js_handler"
                        })
                        break
            
            # 4. Import relationships
            imports = item.get("imports", [])
            if base_name in imports or any(base_name in imp for imp in imports):
                related.append({
                    **item,
                    "relation_type": "imports",
                    "relation_strength": "weak",
                    "direction": "depends_on"
                })
        
        # Remove duplicates based on file_path + name
        seen = set()
        unique_related = []
        for item in related:
            key = (item.get("file_path"), item.get("name"), item.get("relation_type"))
            if key not in seen:
                seen.add(key)
                unique_related.append(item)
        
        # Sort by strength (strong > medium > weak)
        strength_order = {"strong": 3, "medium": 2, "weak": 1}
        unique_related.sort(key=lambda x: strength_order.get(x.get("relation_strength", "weak"), 0), reverse=True)
        
        return unique_related[:15]  # Increased limit for better context
    
    def contextual_search(self, query: str, depth: int = 2) -> List[Dict]:
        """
        Perform contextual search that returns base results with related components.
        
        Args:
            query: Search query
            depth: How many levels of relationships to include (1 = direct, 2 = one hop away)
        
        Returns:
            List of result nodes with their related components
        """
        # Get base search results
        if hasattr(self.search_service, 'hybrid_search'):
            base_results = self.search_service.hybrid_search(query, max_results=5)
        elif hasattr(self.search_service, 'search_semantic'):
            base_results = self.search_service.search_semantic(query, max_results=5)
        else:
            base_results = self.search_service.search(query, max_results=5)
        
        graph = []
        
        for result in base_results:
            node = {
                "base": result,
                "related": [],
                "depth": 0
            }
            
            # Find direct relationships
            if depth >= 1:
                related = self.find_related(result)
                node["related"] = related
                
                # If depth > 1, find relationships of relationships
                if depth >= 2:
                    for rel_item in related[:3]:  # Limit to avoid explosion
                        rel_related = self.find_related(rel_item)
                        # Add to related with depth marker
                        for rr in rel_related[:2]:  # Limit second level
                            rr["depth"] = 2
                            node["related"].append(rr)
            
            graph.append(node)
        
        return graph
    
    def build_flow_graph(self, query: str) -> Dict:
        """
        Build a complete flow graph showing how components connect.
        Example: HTML button → JS handler → API call → Python route → Python function
        
        Returns a graph with nodes and edges, including bidirectional relationships
        and frontend↔backend connections.
        """
        contextual_results = self.contextual_search(query, depth=2)
        
        nodes = []
        edges = []
        node_ids = set()
        
        # Add base nodes
        for ctx_result in contextual_results:
            base = ctx_result["base"]
            base_id = f"{base.get('file_path')}::{base.get('name')}"
            base_language = base.get("language", "")
            
            if base_id not in node_ids:
                nodes.append({
                    "id": base_id,
                    "label": base.get("name", ""),
                    "type": base.get("type", "code"),
                    "file": base.get("file_path", ""),
                    "line": base.get("start_line"),
                    "score": base.get("score", 0),
                    "language": base_language,
                    "context": base.get("context", "")
                })
                node_ids.add(base_id)
            
            # Add related nodes and edges
            for related in ctx_result.get("related", []):
                rel_id = f"{related.get('file_path')}::{related.get('name')}"
                rel_language = related.get("language", "")
                
                if rel_id not in node_ids:
                    nodes.append({
                        "id": rel_id,
                        "label": related.get("name", ""),
                        "type": related.get("type", "code"),
                        "file": related.get("file_path", ""),
                        "line": related.get("start_line"),
                        "score": related.get("score", 0),
                        "language": rel_language,
                        "context": related.get("context", "")
                    })
                    node_ids.add(rel_id)
                
                # Determine edge direction based on relationship
                relation_type = related.get("relation_type", "related")
                direction = related.get("direction", "")
                
                # Create bidirectional edges for frontend↔backend connections
                if relation_type in ["handles_endpoint", "calls_route", "calls_endpoint"]:
                    # Frontend → Backend or Backend → Frontend
                    edges.append({
                        "source": base_id if direction == "frontend" else rel_id,
                        "target": rel_id if direction == "frontend" else base_id,
                        "type": relation_type,
                        "strength": related.get("relation_strength", "strong"),
                        "direction": direction,
                        "endpoint": related.get("endpoint_match", "")
                    })
                else:
                    # Unidirectional edge
                    edges.append({
                        "source": base_id,
                        "target": rel_id,
                        "type": relation_type,
                        "strength": related.get("relation_strength", "weak"),
                        "direction": direction
                    })
        
        # Add flow chains (HTML → JS → API → Backend)
        flow_chains = self._identify_flow_chains(nodes, edges)
        
        return {
            "query": query,
            "nodes": nodes,
            "edges": edges,
            "flow_chains": flow_chains,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "frontend_nodes": len([n for n in nodes if n.get("language") in ["javascript", "typescript", "html"]]),
                "backend_nodes": len([n for n in nodes if n.get("language") == "python"]),
                "frontend_backend_connections": len([e for e in edges if e.get("type") in ["handles_endpoint", "calls_route"]])
            }
        }
    
    def _identify_flow_chains(self, nodes: List[Dict], edges: List[Dict]) -> List[List[str]]:
        """
        Identify complete flow chains from HTML → JS → API → Backend.
        Returns list of node ID chains.
        """
        chains = []
        
        # Find HTML elements
        html_nodes = [n for n in nodes if n.get("type") in ["button", "element", "input"]]
        
        for html_node in html_nodes:
            chain = [html_node["id"]]
            
            # Find JS handlers
            js_edges = [e for e in edges if e.get("source") == html_node["id"] and e.get("type") == "handles_event"]
            for js_edge in js_edges:
                js_node_id = js_edge["target"]
                chain.append(js_node_id)
                
                # Find API calls from JS
                api_edges = [e for e in edges if e.get("source") == js_node_id and e.get("type") in ["calls_endpoint", "calls_route"]]
                for api_edge in api_edges:
                    api_node_id = api_edge["target"]
                    chain.append(api_node_id)
                    
                    # Find backend handlers
                    backend_edges = [e for e in edges if e.get("source") == api_node_id and e.get("type") == "handles_endpoint"]
                    for backend_edge in backend_edges:
                        backend_node_id = backend_edge["target"]
                        chain.append(backend_node_id)
                        chains.append(chain.copy())
                        chain.pop()  # Backtrack
                    chain.pop()  # Backtrack
                chain.pop()  # Backtrack
        
        return chains[:10]  # Limit to top 10 chains

