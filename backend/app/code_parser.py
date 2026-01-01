"""
Code Parser - Extracts semantic code structures from Python, JavaScript, and HTML
Uses AST for Python, regex for JavaScript, and BeautifulSoup for HTML
"""
import ast
import re
import os
from pathlib import Path
from typing import List, Dict, Optional

try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    print("Warning: beautifulsoup4 not installed. HTML parsing will be limited.")


class CodeParser:
    """Parser for extracting semantic code structures from multiple languages"""
    
    def __init__(self):
        self.supported_ext = [".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm"]
    
    def parse_file(self, file_path: Path) -> List[Dict]:
        """
        Parse a file and extract semantic structures.
        Returns list of dictionaries with structure information.
        
        Format:
        {
            "type": "function" | "class" | "route" | "button" | "form" | etc,
            "name": "function_name",
            "language": "python" | "javascript" | "html",
            "file_path": "path/to/file.py",
            "start_line": 23,
            "end_line": 45,
            "context": "Description and code",
            "code": "full code snippet",
            "api_calls": [...],
            "event_listeners": [...],
            "routes": [...],
            "attributes": {...}
        }
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        
        if ext not in self.supported_ext:
            return []
        
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")
            return []
        
        if ext == ".py":
            return self.parse_python_code(content, file_path)
        elif ext in [".js", ".jsx"]:
            return self.parse_js_code(content, file_path)
        elif ext in [".ts", ".tsx"]:
            return self.parse_js_code(content, file_path)  # TypeScript parsed same as JS
        elif ext in [".html", ".htm"]:
            return self.parse_html_code(content, file_path)
        
        return []
    
    # 🐍 ---------------------- PYTHON PARSER ----------------------
    def parse_python_code(self, code: str, file_path: Path) -> List[Dict]:
        """Parse Python code using AST"""
        results = []
        lines = code.split('\n')
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            print(f"⚠ Syntax error in {file_path}: {e}")
            return []
        except Exception as e:
            print(f"⚠ Error parsing {file_path}: {e}")
            return []
        
        # Extract functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node) or ""
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", start_line)
                snippet = "\n".join(lines[start_line-1:end_line])
                
                # Extract decorators (for routes)
                decorators = []
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if isinstance(decorator.func, ast.Attribute):
                            decorator_name = f"{decorator.func.attr}"
                            if decorator.args:
                                # Extract route path from decorator
                                if isinstance(decorator.args[0], (ast.Str, ast.Constant)):
                                    route_path = decorator.args[0].s if hasattr(decorator.args[0], 's') else str(decorator.args[0].value)
                                    decorators.append({
                                        "type": "route",
                                        "path": route_path,
                                        "method": decorator_name.upper() if decorator_name in ['get', 'post', 'put', 'delete'] else "GET"
                                    })
                
                # Extract API calls (requests, httpx, etc.)
                api_calls = self._extract_python_api_calls(node, code)
                
                # Extract function calls (relations)
                relations = self._extract_function_calls(node)
                
                # Extract imports
                imports = self._extract_imports_from_node(node, tree)
                
                # Extract function signature
                args = []
                for arg in node.args.args:
                    arg_name = arg.arg
                    # Add type hints if available
                    if arg.annotation:
                        if isinstance(arg.annotation, ast.Name):
                            arg_type = arg.annotation.id
                        else:
                            arg_type = "Any"
                        args.append(f"{arg_name}: {arg_type}")
                    else:
                        args.append(arg_name)
                
                # Return type annotation
                return_type = None
                if node.returns:
                    if isinstance(node.returns, ast.Name):
                        return_type = node.returns.id
                    elif isinstance(node.returns, ast.Attribute):
                        return_type = f"{node.returns.value.id}.{node.returns.attr}" if isinstance(node.returns.value, ast.Name) else node.returns.attr
                
                signature = f"{node.name}({', '.join(args)})"
                if return_type:
                    signature += f" -> {return_type}"
                
                results.append({
                    "type": "function",
                    "name": node.name,
                    "full_name": f"{file_path.name}::{node.name}()",
                    "language": "python",
                    "file_path": str(file_path),
                    "start_line": start_line,
                    "end_line": end_line,
                    "context": docstring.strip() or f"Python function {node.name}",
                    "code": snippet,
                    "docstring": docstring.strip(),
                    "signature": signature,  # Function signature with type hints
                    "routes": decorators,
                    "api_calls": api_calls,
                    "relations": relations,  # Function calls within this function
                    "imports": imports  # Imports used by this function
                })
            
            elif isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node) or ""
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", start_line)
                snippet = "\n".join(lines[start_line-1:end_line])
                
                # Extract class hierarchy (base classes)
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        # Handle cases like module.Class
                        attr_chain = []
                        temp = base
                        while isinstance(temp, ast.Attribute):
                            attr_chain.insert(0, temp.attr)
                            temp = temp.value
                        if isinstance(temp, ast.Name):
                            attr_chain.insert(0, temp.id)
                            bases.append(".".join(attr_chain))
                
                # Extract class methods and their signatures
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        # Get method signature
                        args = []
                        for arg in item.args.args:
                            arg_name = arg.arg
                            if arg_name != 'self':
                                args.append(arg_name)
                        signature = f"{item.name}({', '.join(args)})"
                        methods.append({
                            "name": item.name,
                            "signature": signature,
                            "docstring": ast.get_docstring(item) or ""
                        })
                
                results.append({
                    "type": "class",
                    "name": node.name,
                    "full_name": f"{file_path.name}::{node.name}",
                    "language": "python",
                    "file_path": str(file_path),
                    "start_line": start_line,
                    "end_line": end_line,
                    "context": docstring.strip() or f"Python class {node.name}",
                    "code": snippet,
                    "docstring": docstring.strip(),
                    "bases": bases,  # Inheritance hierarchy
                    "methods": methods,  # Class methods with signatures
                    "relations": [],  # Will be populated if class calls other functions
                    "imports": self._extract_imports_from_node(None, tree)  # Get all imports from file
                })
        
        # Find Flask/FastAPI routes using regex (backup method)
        route_patterns = [
            (r'@app\.route\(["\'](.*?)["\']', "GET"),
            (r'@app\.get\(["\'](.*?)["\']', "GET"),
            (r'@app\.post\(["\'](.*?)["\']', "POST"),
            (r'@app\.put\(["\'](.*?)["\']', "PUT"),
            (r'@app\.delete\(["\'](.*?)["\']', "DELETE"),
            (r'@router\.(get|post|put|delete)\(["\'](.*?)["\']', None),  # FastAPI
        ]
        
        for pattern, method in route_patterns:
            for match in re.finditer(pattern, code):
                if method:
                    route_path = match.group(1)
                    route_method = method
                else:
                    route_method = match.group(1).upper()
                    route_path = match.group(2)
                
                # Find line number
                line_num = code[:match.start()].count('\n') + 1
                
                results.append({
                    "type": "route",
                    "name": route_path,
                    "full_name": f"{file_path.name}::{route_method} {route_path}",
                    "language": "python",
                    "file_path": str(file_path),
                    "start_line": line_num,
                    "end_line": line_num,
                    "context": f"Flask/FastAPI {route_method} route {route_path}",
                    "code": match.group(0),
                    "routes": [{"path": route_path, "method": route_method}]
                })
        
        # If no structures found, return whole file
        if not results:
            results.append({
                "type": "file",
                "name": file_path.name,
                "full_name": f"{file_path.name}::<file>",
                "language": "python",
                "file_path": str(file_path),
                "start_line": 1,
                "end_line": len(lines),
                "context": "Python file",
                "code": code
            })
        
        return results
    
    def _extract_function_calls(self, node: ast.FunctionDef) -> List[str]:
        """
        Extract function calls from a Python function node using AST.
        Handles complex attribute chains like obj.attr.method().
        Returns list of function names being called within this function.
        """
        relations = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = ""
                
                if isinstance(child.func, ast.Attribute):
                    # Handle attribute chains: obj.attr.method()
                    chain = []
                    temp = child.func
                    while isinstance(temp, ast.Attribute):
                        chain.append(temp.attr)
                        temp = temp.value
                    
                    # Get the base (Name, Call, etc.)
                    if isinstance(temp, ast.Name):
                        chain.append(temp.id)
                        func_name = ".".join(reversed(chain))
                    elif isinstance(temp, ast.Call):
                        # Handle cases like func().method()
                        if isinstance(temp.func, ast.Name):
                            func_name = f"{temp.func.id}.{'.'.join(reversed(chain))}"
                    else:
                        # Just use the attribute chain if we can't resolve base
                        func_name = ".".join(reversed(chain))
                
                elif isinstance(child.func, ast.Name):
                    # Direct function call: function_name()
                    func_name = child.func.id
                
                elif isinstance(child.func, ast.Subscript):
                    # Handle cases like func[key]()
                    if isinstance(child.func.value, ast.Name):
                        func_name = child.func.value.id
                
                # Filter out built-ins and add to relations
                if func_name and func_name not in dir(__builtins__):
                    # Additional filtering for common built-ins
                    built_ins = {'print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 
                                'set', 'tuple', 'range', 'enumerate', 'zip', 'map', 'filter', 
                                'sorted', 'max', 'min', 'sum', 'abs', 'round', 'isinstance', 
                                'type', 'hasattr', 'getattr', 'setattr', 'delattr', 'super', 
                                'self', 'open', 'file', 'iter', 'next', 'all', 'any'}
                    
                    if func_name not in built_ins and not func_name.startswith('__'):
                        relations.append(func_name)
        
        return list(set(relations))  # Remove duplicates
    
    def _extract_imports_from_node(self, node: ast.FunctionDef, tree: ast.AST) -> List[str]:
        """
        Extract imports from the entire file (not just the function).
        This helps understand dependencies between files.
        """
        imports = []
        
        # Get all imports from the file
        for item in ast.walk(tree):
            if isinstance(item, ast.Import):
                for alias in item.names:
                    # Store both the imported name and the alias if different
                    imports.append(alias.name)
                    if alias.asname:
                        imports.append(f"{alias.name} as {alias.asname}")
            elif isinstance(item, ast.ImportFrom):
                if item.module:
                    # Store the module name
                    imports.append(item.module)
                    for alias in item.names:
                        # Store both module.function and just function
                        full_name = f"{item.module}.{alias.name}"
                        imports.append(full_name)
                        imports.append(alias.name)
                        if alias.asname:
                            imports.append(f"{full_name} as {alias.asname}")
        
        return list(set(imports))
    
    def _extract_python_api_calls(self, node: ast.FunctionDef, code: str) -> List[Dict]:
        """Extract API calls from Python function (requests, httpx, etc.)"""
        api_calls = []
        func_code = ast.get_source_segment(code, node) or ""
        
        # Pattern for requests library
        requests_pattern = r'requests\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(requests_pattern, func_code):
            api_calls.append({
                "type": "api_call",
                "method": match.group(1).upper(),
                "endpoint": match.group(2),
                "line": node.lineno
            })
        
        # Pattern for httpx
        httpx_pattern = r'httpx\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(httpx_pattern, func_code):
            api_calls.append({
                "type": "api_call",
                "method": match.group(1).upper(),
                "endpoint": match.group(2),
                "line": node.lineno
            })
        
        return api_calls
    
    # ⚡ ---------------------- JAVASCRIPT PARSER ----------------------
    def parse_js_code(self, code: str, file_path: Path) -> List[Dict]:
        """Parse JavaScript/TypeScript code using regex"""
        results = []
        lines = code.split('\n')
        language = "typescript" if file_path.suffix in ['.ts', '.tsx'] else "javascript"
        
        # Regular functions: function name() {}
        for match in re.finditer(r'function\s+(\w+)\s*\([^)]*\)\s*\{', code, re.MULTILINE):
            name = match.group(1)
            start_line = code[:match.start()].count('\n') + 1
            # Try to find end of function
            brace_count = 0
            end_pos = match.end()
            found_start = False
            for i, char in enumerate(code[match.end():], start=match.end()):
                if char == '{':
                    brace_count += 1
                    found_start = True
                elif char == '}':
                    brace_count -= 1
                    if found_start and brace_count == 0:
                        end_pos = i + 1
                        break
            end_line = code[:end_pos].count('\n') + 1
            snippet = code[match.start():end_pos]
            
            # Extract API calls and event listeners from function
            api_calls = self._extract_js_api_calls(snippet)
            event_listeners = self._extract_js_event_listeners(snippet)
            relations = self._extract_js_function_calls(snippet)
            
            results.append({
                "type": "function",
                "name": name,
                "full_name": f"{file_path.name}::{name}()",
                "language": language,
                "file_path": str(file_path),
                "start_line": start_line,
                "end_line": end_line,
                "context": f"{language.capitalize()} function {name}",
                "code": snippet,
                "api_calls": api_calls,
                "event_listeners": event_listeners,
                "relations": relations
            })
        
        # Arrow functions: const name = () => {}
        for match in re.finditer(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>', code, re.MULTILINE):
            name = match.group(1)
            start_line = code[:match.start()].count('\n') + 1
            # Find the arrow function body
            arrow_pos = match.end()
            # Try to find end (simplified)
            end_line = start_line + 10  # Approximate
            snippet = code[match.start():match.end() + 100]  # First 100 chars
            
            api_calls = self._extract_js_api_calls(snippet)
            event_listeners = self._extract_js_event_listeners(snippet)
            relations = self._extract_js_function_calls(snippet)
            
            results.append({
                "type": "arrow_function",
                "name": name,
                "full_name": f"{file_path.name}::{name}()",
                "language": language,
                "file_path": str(file_path),
                "start_line": start_line,
                "end_line": end_line,
                "context": f"{language.capitalize()} arrow function {name}",
                "code": snippet,
                "api_calls": api_calls,
                "event_listeners": event_listeners,
                "relations": relations
            })
        
        # Event listeners: addEventListener('event', handler)
        for match in re.finditer(r'\.addEventListener\s*\(\s*["\'](\w+)["\']\s*,\s*(\w+)', code, re.MULTILINE):
            event = match.group(1)
            handler = match.group(2)
            line_num = code[:match.start()].count('\n') + 1
            
            results.append({
                "type": "event_listener",
                "name": f"{event}_{handler}",
                "full_name": f"{file_path.name}::addEventListener('{event}')",
                "language": language,
                "file_path": str(file_path),
                "start_line": line_num,
                "end_line": line_num,
                "context": f"Event listener for '{event}' calling {handler}",
                "code": match.group(0),
                "event_listeners": [{"event": event, "handler": handler}]
            })
        
        # API calls: fetch('url') or axios.get('url')
        for match in re.finditer(r'(fetch|axios\.(get|post|put|delete|patch))\s*\([^)]*["\']([^"\']+)["\']', code, re.MULTILINE):
            api_type = match.group(1)
            endpoint = match.group(3)
            method = "GET"
            if 'axios.' in api_type:
                method = match.group(2).upper() if match.group(2) else "GET"
            line_num = code[:match.start()].count('\n') + 1
            
            results.append({
                "type": "api_call",
                "name": endpoint,
                "full_name": f"{file_path.name}::{method} {endpoint}",
                "language": language,
                "file_path": str(file_path),
                "start_line": line_num,
                "end_line": line_num,
                "context": f"{language.capitalize()} API call to {endpoint}",
                "code": match.group(0),
                "api_calls": [{"method": method, "endpoint": endpoint}]
            })
        
        # If no structures found, return whole file
        if not results:
            results.append({
                "type": "file",
                "name": file_path.name,
                "full_name": f"{file_path.name}::<file>",
                "language": language,
                "file_path": str(file_path),
                "start_line": 1,
                "end_line": len(lines),
                "context": f"{language.capitalize()} file",
                "code": code
            })
        
        return results
    
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
    
    def _extract_js_api_calls(self, code: str) -> List[Dict]:
        """
        Extract API calls from JavaScript code snippet with enhanced regex.
        Supports fetch() and axios with method detection and endpoint normalization.
        """
        api_calls = []
        
        # Pattern 1: fetch('url') or fetch('url', {method: 'POST', ...})
        # Enhanced regex to capture method from options object
        fetch_pattern = r"fetch\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*\{[^}]*method\s*:\s*['\"](\w+)['\"][^}]*\})?"
        for match in re.finditer(fetch_pattern, code, re.IGNORECASE):
            endpoint = match.group(1)
            method = match.group(2).upper() if match.group(2) else "GET"  # Default for fetch
            
            normalized_endpoint = self._normalize_endpoint(endpoint)
            
            api_calls.append({
                "type": "api_call",
                "method": method,
                "endpoint": endpoint,
                "endpoint_normalized": normalized_endpoint,  # For matching
                "context": "frontend"
            })
        
        # Pattern 2: axios.get/post/put/delete('url')
        for match in re.finditer(r"axios\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]", code, re.IGNORECASE):
            endpoint = match.group(2)
            normalized_endpoint = self._normalize_endpoint(endpoint)
            
            api_calls.append({
                "type": "api_call",
                "method": match.group(1).upper(),
                "endpoint": endpoint,
                "endpoint_normalized": normalized_endpoint,
                "context": "frontend"
            })
        
        # Pattern 3: axios({method: 'POST', url: '...'})
        for match in re.finditer(r"axios\s*\(\s*\{[^}]*url\s*:\s*['\"]([^'\"]+)['\"]", code, re.IGNORECASE):
            endpoint = match.group(1)
            normalized_endpoint = self._normalize_endpoint(endpoint)
            method = "GET"  # Default
            
            # Try to find method in the same object (look in wider context)
            start_pos = match.start()
            end_pos = min(match.end() + 200, len(code))  # Look ahead 200 chars
            context_snippet = code[start_pos:end_pos]
            
            method_match = re.search(
                r"method\s*:\s*['\"](\w+)['\"]",
                context_snippet,
                re.IGNORECASE
            )
            if method_match:
                method = method_match.group(1).upper()
            
            api_calls.append({
                "type": "api_call",
                "method": method,
                "endpoint": endpoint,
                "endpoint_normalized": normalized_endpoint,
                "context": "frontend"
            })
        
        return api_calls
    
    def _extract_js_event_listeners(self, code: str) -> List[Dict]:
        """Extract event listeners from JavaScript code snippet"""
        event_listeners = []
        
        # addEventListener('event', handler)
        for match in re.finditer(r"\.addEventListener\s*\(\s*['\"](\w+)['\"]\s*,\s*(\w+)", code):
            event_listeners.append({
                "type": "event_listener",
                "event": match.group(1),
                "handler": match.group(2)
            })
        
        return event_listeners
    
    def _extract_js_function_calls(self, code: str) -> List[str]:
        """Extract function calls from JavaScript code"""
        relations = []
        
        # Pattern: functionName(...) or obj.method(...)
        # Match function calls but exclude declarations
        pattern = r'(\w+)\s*\('
        for match in re.finditer(pattern, code):
            func_name = match.group(1)
            # Skip common keywords and built-ins
            skip_keywords = {
                'if', 'for', 'while', 'switch', 'catch', 'function',
                'return', 'new', 'typeof', 'instanceof', 'console',
                'document', 'window', 'this', 'super', 'async', 'await',
                'setTimeout', 'setInterval', 'addEventListener', 'removeEventListener'
            }
            if func_name not in skip_keywords and func_name not in relations:
                relations.append(func_name)
        
        return relations
    
    # 🧱 ---------------------- HTML PARSER ----------------------
    def parse_html_code(self, code: str, file_path: Path) -> List[Dict]:
        """Parse HTML code using BeautifulSoup"""
        results = []
        
        if not BEAUTIFULSOUP_AVAILABLE:
            return results
        
        try:
            soup = BeautifulSoup(code, "html.parser")
        except Exception as e:
            print(f"⚠ HTML parsing error in {file_path}: {e}")
            return results
        
        lines = code.split('\n')
        
        # Buttons
        for btn in soup.find_all("button"):
            button_id = btn.get("id", "")
            button_text = btn.get_text(strip=True)
            button_classes = btn.get("class", [])
            button_onclick = btn.get("onclick", "")
            
            # Find line number
            line_num = 1
            btn_str = str(btn)
            for i, line in enumerate(lines, 1):
                if button_id in line or button_text[:20] in line:
                    line_num = i
                    break
            
            event_listeners = []
            if button_onclick:
                event_listeners.append({"event": "click", "handler": button_onclick})
            
            results.append({
                "type": "button",
                "name": button_id or button_text[:30] or "button",
                "full_name": f"{file_path.name}::<button id='{button_id}'>",
                "language": "html",
                "file_path": str(file_path),
                "start_line": line_num,
                "end_line": line_num,
                "context": button_text or f"Button {button_id}",
                "code": str(btn),
                "attributes": {
                    "id": button_id,
                    "classes": button_classes,
                    "text": button_text,
                    "onclick": button_onclick
                },
                "event_listeners": event_listeners
            })
        
        # Inline event handlers (onclick, onchange, etc.)
        for tag in soup.find_all(attrs={"onclick": True}):
            tag_id = tag.get("id", "")
            onclick_value = tag.get("onclick", "")
            line_num = 1
            for i, line in enumerate(lines, 1):
                if tag_id in line or onclick_value[:20] in line:
                    line_num = i
                    break
            
            results.append({
                "type": "event_inline",
                "name": tag_id or tag.name,
                "full_name": f"{file_path.name}::<{tag.name} onclick>",
                "language": "html",
                "file_path": str(file_path),
                "start_line": line_num,
                "end_line": line_num,
                "context": f"Inline event handler: {onclick_value[:50]}",
                "code": str(tag),
                "attributes": {"onclick": onclick_value},
                "event_listeners": [{"event": "click", "handler": onclick_value}]
            })
        
        # Forms
        for form in soup.find_all("form"):
            form_id = form.get("id", "")
            form_action = form.get("action", "")
            line_num = 1
            for i, line in enumerate(lines, 1):
                if form_id in line or form_action in line:
                    line_num = i
                    break
            
            results.append({
                "type": "form",
                "name": form_id or form_action or "form",
                "full_name": f"{file_path.name}::<form id='{form_id}'>",
                "language": "html",
                "file_path": str(file_path),
                "start_line": line_num,
                "end_line": line_num,
                "context": f"Form with action: {form_action}",
                "code": str(form),
                "attributes": {
                    "id": form_id,
                    "action": form_action,
                    "method": form.get("method", "GET")
                }
            })
        
        # Input fields
        for input_elem in soup.find_all(["input", "select", "textarea"]):
            input_id = input_elem.get("id", "")
            input_name = input_elem.get("name", "")
            input_type = input_elem.get("type", input_elem.name)
            
            if input_id or input_name:  # Only index if has identifier
                line_num = 1
                for i, line in enumerate(lines, 1):
                    if input_id in line or input_name in line:
                        line_num = i
                        break
                
                results.append({
                    "type": "input",
                    "name": input_id or input_name or input_type,
                    "full_name": f"{file_path.name}::<{input_elem.name} id='{input_id}'>",
                    "language": "html",
                    "file_path": str(file_path),
                    "start_line": line_num,
                    "end_line": line_num,
                    "context": f"Input field: {input_type}",
                    "code": str(input_elem),
                    "attributes": {
                        "id": input_id,
                        "name": input_name,
                        "type": input_type
                    }
                })
        
        # If no structures found, return whole file
        if not results:
            results.append({
                "type": "file",
                "name": file_path.name,
                "full_name": f"{file_path.name}::<file>",
                "language": "html",
                "file_path": str(file_path),
                "start_line": 1,
                "end_line": len(lines),
                "context": "HTML file",
                "code": code
            })
        
        return results
