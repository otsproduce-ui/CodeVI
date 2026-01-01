"""
Explanation Service - Generates flow explanations for code search results
Connects HTML → JS → API → Python components
"""
from typing import List, Dict, Optional
from pathlib import Path
import re


class ExplanationService:
    """Service for explaining code flows and relationships"""
    
    def __init__(self, semantic_service=None, search_service=None):
        self.semantic_service = semantic_service
        self.search_service = search_service
    
    def explain_flow(self, query: str, results: List[Dict], root_path: Optional[Path] = None) -> str:
        """
        Generate a flow explanation connecting multiple code components.
        
        Example:
        "Login flow is triggered by the login-btn in the frontend,
        handled by handleLogin() which calls /login endpoint,
        processed by authenticate_user() in the backend."
        """
        if not results:
            return "No results found to explain."
        
        # Group results by type
        html_elements = []
        js_functions = []
        api_routes = []
        python_functions = []
        other = []
        
        for result in results:
            result_type = result.get("type", "code")
            file_path = result.get("file_path", "")
            
            if result_type == "element" or file_path.endswith(('.html', '.htm')):
                html_elements.append(result)
            elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                js_functions.append(result)
            elif file_path.endswith('.py'):
                # Check if it's a route
                if result.get("routes") or '@app.route' in result.get("code", ""):
                    api_routes.append(result)
                else:
                    python_functions.append(result)
            else:
                other.append(result)
        
        # Build explanation
        explanation_parts = []
        
        # Start with HTML elements
        if html_elements:
            for elem in html_elements[:2]:  # Top 2 elements
                elem_id = elem.get("attributes", {}).get("id", "")
                elem_text = elem.get("attributes", {}).get("text", "")
                explanation_parts.append(
                    f"• **{elem.get('function_name', elem.get('name', 'element'))}** "
                    f"in `{elem.get('file_path', '')}` "
                    f"(line {elem.get('start_line', '?')})"
                )
        
        # Connect to JS handlers
        if js_functions:
            for func in js_functions[:2]:  # Top 2 functions
                func_name = func.get("function_name", func.get("name", ""))
                api_calls = func.get("api_calls", [])
                
                explanation_parts.append(
                    f"• **{func_name}** in `{func.get('file_path', '')}` "
                    f"(line {func.get('start_line', '?')})"
                )
                
                # Mention API calls
                if api_calls:
                    for api_call in api_calls[:1]:  # First API call
                        explanation_parts.append(
                            f"  → Calls API endpoint: `{api_call.get('endpoint', '')}` "
                            f"({api_call.get('method', 'GET')})"
                        )
        
        # Connect to Python routes
        if api_routes:
            for route in api_routes[:2]:  # Top 2 routes
                route_paths = route.get("routes", [])
                func_name = route.get("function_name", route.get("name", ""))
                
                if route_paths:
                    route_info = route_paths[0]
                    explanation_parts.append(
                        f"• **{func_name}** handles `{route_info.get('path', '')}` "
                        f"({route_info.get('method', 'GET')}) in `{route.get('file_path', '')}` "
                        f"(line {route.get('start_line', '?')})"
                    )
                else:
                    explanation_parts.append(
                        f"• **{func_name}** in `{route.get('file_path', '')}` "
                        f"(line {route.get('start_line', '?')})"
                    )
        
        # Add Python functions
        if python_functions:
            for func in python_functions[:2]:  # Top 2 functions
                func_name = func.get("function_name", func.get("name", ""))
                docstring = func.get("docstring", "")
                explanation_parts.append(
                    f"• **{func_name}** in `{func.get('file_path', '')}` "
                    f"(line {func.get('start_line', '?')})"
                )
                if docstring:
                    explanation_parts.append(f"  {docstring[:100]}")
        
        # Build final explanation
        if explanation_parts:
            explanation = f"**Flow explanation for: '{query}'\n\n"
            explanation += "\n".join(explanation_parts)
            
            # Add connection summary
            if len(html_elements) > 0 and len(js_functions) > 0 and len(api_routes) > 0:
                explanation += "\n\n**Connection:** Frontend elements trigger JavaScript handlers, "
                explanation += "which call API endpoints handled by backend Python functions."
            
            return explanation
        else:
            return f"Found {len(results)} relevant code components, but couldn't build a flow explanation."
    
    def find_related_components(self, result: Dict, root_path: Optional[Path] = None) -> List[Dict]:
        """
        Find components related to a search result.
        For example, if result is a button, find its event handler.
        """
        related = []
        
        # If result has API calls, find the route handlers
        api_calls = result.get("api_calls", [])
        for api_call in api_calls:
            endpoint = api_call.get("endpoint", "")
            if endpoint and self.search_service:
                # Search for route definitions
                route_query = f"route {endpoint}"
                route_results = self.search_service.search(route_query, max_results=5)
                related.extend(route_results)
        
        # If result has event listeners, find the handlers
        event_listeners = result.get("event_listeners", [])
        for listener in event_listeners:
            handler = listener.get("handler", "")
            if handler and self.search_service:
                # Search for handler function
                handler_query = f"function {handler}"
                handler_results = self.search_service.search(handler_query, max_results=5)
                related.extend(handler_results)
        
        # If result is an HTML element, find JS handlers
        if result.get("type") == "element":
            elem_id = result.get("attributes", {}).get("id", "")
            if elem_id and self.search_service:
                # Search for getElementById or querySelector
                js_query = f"getElementById {elem_id}"
                js_results = self.search_service.search(js_query, max_results=5)
                related.extend(js_results)
        
        return related[:5]  # Limit to 5 related components
    
    def build_complete_flow(self, query: str, results: List[Dict]) -> Dict:
        """
        Build a complete flow diagram from search results.
        Returns a structure that can be visualized.
        """
        flow = {
            "query": query,
            "components": [],
            "connections": []
        }
        
        for result in results:
            component = {
                "id": result.get("function_name", result.get("name", "")),
                "type": result.get("type", "code"),
                "file": result.get("file_path", ""),
                "line": result.get("start_line", 0),
                "code": result.get("code", "")[:200]  # Preview
            }
            flow["components"].append(component)
            
            # Add connections
            api_calls = result.get("api_calls", [])
            for api_call in api_calls:
                flow["connections"].append({
                    "from": component["id"],
                    "to": api_call.get("endpoint", ""),
                    "type": "api_call",
                    "method": api_call.get("method", "GET")
                })
            
            event_listeners = result.get("event_listeners", [])
            for listener in event_listeners:
                flow["connections"].append({
                    "from": component["id"],
                    "to": listener.get("handler", ""),
                    "type": "event",
                    "event": listener.get("event", "")
                })
        
        return flow

