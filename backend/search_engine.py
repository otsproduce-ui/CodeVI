"""
BM25-based search engine for codebase indexing and search
"""
from pathlib import Path
from typing import List, Dict, Optional
import re
from rank_bm25 import BM25Okapi
from collections import defaultdict


class SearchEngine:
    """Local-first BM25 search engine for codebases"""
    
    # File extensions to index
    CODE_EXTENSIONS = {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
        '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r',
        '.sql', '.html', '.css', '.scss', '.sass', '.vue', '.svelte', '.dart',
        '.sh', '.bash', '.zsh', '.yaml', '.yml', '.json', '.xml', '.toml',
        '.md', '.txt', '.m', '.mm', '.pl', '.pm', '.lua', '.clj', '.cljs'
    }
    
    # Directories to ignore
    IGNORE_DIRS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
        'dist', 'build', '.next', '.nuxt', 'target', 'bin', 'obj',
        '.idea', '.vscode', '.vs', 'coverage', '.pytest_cache'
    }
    
    def __init__(self, root_path: Path):
        self.root_path = Path(root_path).resolve()
        self.indexed_files: List[Path] = []
        self.file_contents: Dict[str, List[str]] = {}  # file_path -> lines
        self.file_line_map: Dict[str, Dict[int, str]] = {}  # file_path -> {line_num: full_line}
        self.bm25: Optional[BM25Okapi] = None
        self.tokenized_corpus: List[List[str]] = []
        
    def _should_index_file(self, file_path: Path) -> bool:
        """Check if a file should be indexed"""
        # Check extension
        if file_path.suffix.lower() not in self.CODE_EXTENSIONS:
            return False
        
        # Check if in ignored directory
        parts = file_path.parts
        for part in parts:
            if part in self.IGNORE_DIRS:
                return False
        
        return True
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25 indexing"""
        # Split on whitespace and common code delimiters
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def _extract_snippets(self, file_path: Path, content: str) -> Dict[int, str]:
        """Extract line-by-line content with context"""
        lines = content.split('\n')
        line_map = {}
        for i, line in enumerate(lines, start=1):
            line_map[i] = line
        return line_map
    
    def index_codebase(self):
        """Scan and index the entire codebase"""
        self.indexed_files = []
        self.file_contents = {}
        self.file_line_map = {}
        self.tokenized_corpus = []
        
        print(f"Scanning codebase at: {self.root_path}")
        
        # Walk through all files
        for file_path in self.root_path.rglob('*'):
            if file_path.is_file() and self._should_index_file(file_path):
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Store relative path
                    rel_path = str(file_path.relative_to(self.root_path))
                    
                    # Store file contents
                    lines = content.split('\n')
                    self.file_contents[rel_path] = lines
                    self.file_line_map[rel_path] = self._extract_snippets(file_path, content)
                    
                    # Tokenize for BM25
                    tokenized = self._tokenize(content)
                    self.tokenized_corpus.append(tokenized)
                    self.indexed_files.append(file_path)
                    
                except Exception as e:
                    print(f"Warning: Could not index {file_path}: {e}")
                    continue
        
        # Build BM25 index
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            print(f"Indexed {len(self.indexed_files)} files")
        else:
            print("Warning: No files indexed")
    
    def search(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search the indexed codebase and return ranked snippets"""
        if not self.bm25 or not self.tokenized_corpus:
            return []
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        # Get BM25 scores
        scores = self.bm25.get_scores(query_tokens)
        
        # Create results with file info
        results = []
        for idx, score in enumerate(scores):
            if score > 0:  # Only include files with positive scores
                file_path = self.indexed_files[idx]
                rel_path = str(file_path.relative_to(self.root_path))
                
                # Find best matching line in file
                file_lines = self.file_contents[rel_path]
                best_line_idx = self._find_best_line(file_lines, query_tokens)
                
                # Extract snippet with context (3 lines before and after)
                snippet_lines = self._extract_context_snippet(
                    file_lines, best_line_idx, context_lines=3
                )
                
                results.append({
                    "file_path": rel_path,
                    "line_number": best_line_idx + 1,
                    "content": '\n'.join(snippet_lines),
                    "score": float(score)
                })
        
        # Sort by score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top results
        return results[:max_results]
    
    def _find_best_line(self, lines: List[str], query_tokens: List[str]) -> int:
        """Find the line in a file that best matches the query"""
        best_score = 0
        best_idx = 0
        
        for idx, line in enumerate(lines):
            line_tokens = self._tokenize(line)
            # Simple overlap score
            overlap = len(set(query_tokens) & set(line_tokens))
            if overlap > best_score:
                best_score = overlap
                best_idx = idx
        
        return best_idx
    
    def _extract_context_snippet(self, lines: List[str], center_line: int, context_lines: int = 3) -> List[str]:
        """Extract a snippet with context around the center line"""
        start = max(0, center_line - context_lines)
        end = min(len(lines), center_line + context_lines + 1)
        
        snippet = []
        for i in range(start, end):
            prefix = "  " if i != center_line else "> "
            snippet.append(f"{prefix}{i+1:4d} | {lines[i]}")
        
        return snippet
    
    def is_indexed(self) -> bool:
        """Check if codebase is indexed"""
        return self.bm25 is not None and len(self.indexed_files) > 0
    
    def get_file_count(self) -> int:
        """Get number of indexed files"""
        return len(self.indexed_files)
    
    def extract_graph(self) -> Dict:
        """
        Extract file relationships graph from the codebase.
        Returns a JSON-serializable dictionary with nodes and links.
        """
        if not self.is_indexed():
            return {"nodes": [], "links": []}
        
        nodes = []
        links = []
        node_set = set()  # Track nodes to avoid duplicates
        link_set = set()  # Track links to avoid duplicates and self-references
        
        # File type to color mapping
        file_type_colors = {
            '.py': '#3776ab',      # Python blue
            '.js': '#f7df1e',      # JavaScript yellow
            '.jsx': '#61dafb',     # React blue
            '.ts': '#3178c6',      # TypeScript blue
            '.tsx': '#3178c6',     # TypeScript React
            '.css': '#563d7c',     # CSS purple
            '.html': '#e34c26',    # HTML orange
            '.java': '#ed8b00',    # Java orange
            '.cpp': '#00599c',     # C++ blue
            '.c': '#a8b9cc',       # C gray
            '.go': '#00add8',      # Go cyan
            '.rs': '#000000',      # Rust black
            '.rb': '#cc342d',      # Ruby red
            '.php': '#777bb4',     # PHP purple
            '.swift': '#fa7343',   # Swift orange
            '.kt': '#0095d5',      # Kotlin blue
            '.cs': '#239120',      # C# green
        }
        
        # Create nodes for all indexed files
        for file_path in self.indexed_files:
            rel_path = str(file_path.relative_to(self.root_path))
            if rel_path not in node_set:
                file_ext = file_path.suffix.lower()
                file_type = file_ext if file_ext in file_type_colors else 'file'
                color = file_type_colors.get(file_ext, '#6b7280')  # Default gray
                
                nodes.append({
                    "id": rel_path,
                    "type": file_type,
                    "color": color,
                    "label": file_path.name
                })
                node_set.add(rel_path)
        
        # Extract relationships from file contents
        for rel_path, lines in self.file_contents.items():
            source_file = rel_path
            content = '\n'.join(lines)
            file_ext = Path(rel_path).suffix.lower()
            
            # Python imports
            if file_ext == '.py':
                # Match: import module, from module import, from package.module import
                import_patterns = [
                    r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
                    r'^from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import',
                ]
                for pattern in import_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        module_name = match.group(1)
                        target_file = self._resolve_python_import(module_name, rel_path)
                        if target_file and target_file != source_file:
                            link_key = (source_file, target_file, 'import')
                            if link_key not in link_set and target_file in node_set:
                                links.append({
                                    "source": source_file,
                                    "target": target_file,
                                    "type": "import"
                                })
                                link_set.add(link_key)
            
            # JavaScript/TypeScript imports
            elif file_ext in ['.js', '.jsx', '.ts', '.tsx']:
                # Match: import ... from '...', require('...')
                js_patterns = [
                    r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
                    r"require\(['\"]([^'\"]+)['\"]\)",
                    r"import\(['\"]([^'\"]+)['\"]\)",
                ]
                for pattern in js_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        import_path = match.group(1)
                        target_file = self._resolve_js_import(import_path, rel_path)
                        if target_file and target_file != source_file:
                            link_key = (source_file, target_file, 'import')
                            if link_key not in link_set and target_file in node_set:
                                links.append({
                                    "source": source_file,
                                    "target": target_file,
                                    "type": "import"
                                })
                                link_set.add(link_key)
            
            # API calls detection
            api_patterns = [
                r'fetch\s*\([^)]*[\'"]([^\'"]+)[\'"]',
                r'axios\.(?:get|post|put|delete)\s*\([^)]*[\'"]([^\'"]+)[\'"]',
                r'@app\.route\s*\([\'"]([^\'"]+)[\'"]',
                r'@app\.(?:get|post|put|delete)\s*\([\'"]([^\'"]+)[\'"]',
            ]
            for pattern in api_patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    api_path = match.group(1)
                    # Create a virtual API node or link to related files
                    # For now, we'll skip API edges as they're more complex
                    pass
        
        return {
            "nodes": nodes,
            "links": links
        }
    
    def _resolve_python_import(self, module_name: str, source_file: str) -> Optional[str]:
        """Resolve Python import to actual file path"""
        # Remove relative imports (starting with .)
        if module_name.startswith('.'):
            return None
        
        # Try to find the module file
        parts = module_name.split('.')
        base_name = parts[0]
        
        # Search in the same directory and parent directories
        source_path = Path(self.root_path) / source_file
        search_dirs = [
            source_path.parent,
            self.root_path,
            self.root_path / base_name,
        ]
        
        # Try different file extensions
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            
            # Try __init__.py or .py file
            for ext in ['/__init__.py', '.py']:
                candidate = search_dir / f"{base_name}{ext}"
                if candidate.exists():
                    rel_path = str(candidate.relative_to(self.root_path))
                    if rel_path in [str(f.relative_to(self.root_path)) for f in self.indexed_files]:
                        return rel_path
        
        return None
    
    def _resolve_js_import(self, import_path: str, source_file: str) -> Optional[str]:
        """Resolve JavaScript/TypeScript import to actual file path"""
        # Skip node_modules and external packages
        if import_path.startswith('node_modules') or not import_path.startswith('.'):
            return None
        
        source_path = Path(self.root_path) / source_file
        source_dir = source_path.parent
        
        # Remove leading ./ or ../
        clean_path = import_path.lstrip('./')
        
        # Try different extensions
        extensions = ['', '.js', '.jsx', '.ts', '.tsx', '/index.js', '/index.ts']
        
        for ext in extensions:
            candidate = source_dir / f"{clean_path}{ext}"
            if candidate.exists():
                rel_path = str(candidate.relative_to(self.root_path))
                if rel_path in [str(f.relative_to(self.root_path)) for f in self.indexed_files]:
                    return rel_path
        
        # Try with ../ for parent directory
        if import_path.startswith('../'):
            parent_dir = source_dir.parent
            clean_path = import_path.replace('../', '')
            for ext in extensions:
                candidate = parent_dir / f"{clean_path}{ext}"
                if candidate.exists():
                    rel_path = str(candidate.relative_to(self.root_path))
                    if rel_path in [str(f.relative_to(self.root_path)) for f in self.indexed_files]:
                        return rel_path
        
        return None

