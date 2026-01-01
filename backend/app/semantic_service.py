"""
Semantic Search Service - Vector-based semantic search using embeddings
"""
# SSL Bypass - MUST be before any imports
# ⚠️ WARNING: This disables SSL certificate verification (NOT recommended for production)
# This forces all modules (requests, urllib3, huggingface_hub) to ignore SSL certificates
import os, ssl
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

# Now safe to import libraries that use HTTPS
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path
from openai import OpenAI
from typing import List, Tuple, Dict, Optional
from app.code_parser import CodeParser

# Troubleshooting tips:
# 1. If model download still fails, clear HuggingFace cache:
#    Delete: C:\Users\<username>\.cache\huggingface
# 
# 2. To run completely offline (no internet, no SSL issues):
#    Download model once:
#      from sentence_transformers import SentenceTransformer
#      model = SentenceTransformer('all-MiniLM-L6-v2')
#      model.save('models/all-MiniLM-L6-v2')
#    Then change line ~40 to: SentenceTransformer('models/all-MiniLM-L6-v2')
# 
# 3. Update certificates (if you want proper SSL):
#    pip install --upgrade certifi
#    python -m certifi


class SemanticSearchService:
    """Service for semantic search using embeddings and FAISS"""
    
    def __init__(self, root_path=None, vector_index_file="vector.index", bm25_service=None):
        self.root_path = Path(root_path) if root_path else None
        self.vector_index_file = vector_index_file
        self.embedding_model = None
        self.faiss_index = None
        self.file_map = []  # List of dicts: {file_path, function_name, start_line, end_line, snippet}
        self.client = None
        self.bm25_service = bm25_service  # Optional BM25 service for hybrid search
        self.code_parser = CodeParser()  # Initialize tree-sitter parser
        
        # Initialize embedding model
        # Try local model first, then fall back to downloading
        try:
            # Check if local model exists (sentence-transformers format)
            # Path: backend/models/all-MiniLM-L6-v2
            local_model_path = Path(__file__).parent.parent / "models" / "all-MiniLM-L6-v2"
            if local_model_path.exists() and (local_model_path / "modules.json").exists():
                print(f"Loading local model from: {local_model_path}")
                # SentenceTransformer can load from this path directly
                self.embedding_model = SentenceTransformer(str(local_model_path))
            else:
                print("Local model not found, downloading from HuggingFace...")
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Warning: Could not load embedding model: {e}")
            print("You may need to download the model manually or check SSL settings.")
            print(f"Error details: {type(e).__name__}: {str(e)}")
        
        # Initialize OpenAI client if API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
            except Exception as e:
                print(f"Warning: Could not initialize OpenAI client: {e}")
    
    def set_root_path(self, root_path):
        """Set the root path for indexing"""
        self.root_path = Path(root_path)
    
    def _extract_code_structures(self, file_path: Path) -> List[Dict]:
        """
        Extract code structures (functions, classes, elements) using tree-sitter.
        Returns list of dictionaries with code structure information.
        Includes context: API calls, event listeners, routes for better embeddings.
        """
        try:
            # Use tree-sitter parser
            structures = self.code_parser.parse_file(file_path)
            
            # Convert to our format with enhanced context
            results = []
            for struct in structures:
                # Build rich text for embedding: type + name + docstring + context + code
                entry_text = f"{struct.get('type', 'code')}: {struct.get('name', '')}\n"
                
                if struct.get('docstring'):
                    entry_text += f"Description: {struct['docstring']}\n"
                
                # Add context: API calls
                api_calls = struct.get('api_calls', [])
                if api_calls:
                    api_info = ", ".join([f"{ac.get('method', 'GET')} {ac.get('endpoint', '')}" 
                                         for ac in api_calls[:3]])
                    entry_text += f"API calls: {api_info}\n"
                
                # Add context: Event listeners
                event_listeners = struct.get('event_listeners', [])
                if event_listeners:
                    event_info = ", ".join([f"{el.get('event', '')} -> {el.get('handler', '')}" 
                                           for el in event_listeners[:3]])
                    entry_text += f"Events: {event_info}\n"
                
                # Add context: Routes
                routes = struct.get('routes', [])
                if routes:
                    route_info = ", ".join([f"{r.get('method', 'GET')} {r.get('path', '')}" 
                                           for r in routes[:3]])
                    entry_text += f"Routes: {route_info}\n"
                
                # Add the actual code
                entry_text += f"\nCode:\n{struct.get('code', '')}"
                
                results.append({
                    "name": struct.get('full_name', struct.get('name', '')),
                    "snippet": entry_text,
                    "start_line": struct.get('start_line', 1),
                    "end_line": struct.get('end_line', 1),
                    "type": struct.get('type', 'code'),
                    "docstring": struct.get('docstring', ''),
                    "code": struct.get('code', ''),
                    "api_calls": api_calls,
                    "event_listeners": event_listeners,
                    "routes": routes,
                    "attributes": struct.get('attributes', {})
                })
            
            return results
        except Exception as e:
            print(f"Error extracting structures from {file_path}: {e}")
            # Fallback: return whole file
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                lines = content.split('\n')
                return [{
                    "name": f"{file_path.name}::<file>",
                    "snippet": content,
                    "start_line": 1,
                    "end_line": len(lines),
                    "type": "file",
                    "docstring": "",
                    "code": content,
                    "api_calls": [],
                    "event_listeners": [],
                    "routes": [],
                    "attributes": {}
                }]
            except:
                return []
    
    def build_vector_index(self, root_path=None):
        """Build FAISS vector index from codebase files at function/class level"""
        if root_path:
            self.root_path = Path(root_path)
        
        if not self.root_path or not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {self.root_path}")
        
        if not self.embedding_model:
            raise RuntimeError("Embedding model not loaded")
        
        docs = []
        self.file_map = []
        
        # Scan Python, JavaScript/TypeScript, and HTML files
        for ext in ["*.py", "*.js", "*.ts", "*.tsx", "*.jsx", "*.html", "*.htm"]:
            for file_path in self.root_path.rglob(ext):
                try:
                    rel_path = str(file_path.relative_to(self.root_path))
                    
                    # Extract code structures using tree-sitter
                    structures = self._extract_code_structures(file_path)
                    
                    # Add each structure to index
                    for struct in structures:
                        snippet = struct.get("snippet", "")
                        if snippet.strip():
                            docs.append(snippet)
                            self.file_map.append({
                                "file_path": rel_path,
                                "function_name": struct.get("name", ""),
                                "start_line": struct.get("start_line", 1),
                                "end_line": struct.get("end_line", 1),
                                "type": struct.get("type", "code"),
                                "docstring": struct.get("docstring", ""),
                                "snippet": snippet[:500],  # Store preview
                                "api_calls": struct.get("api_calls", []),
                                "event_listeners": struct.get("event_listeners", []),
                                "routes": struct.get("routes", []),
                                "attributes": struct.get("attributes", {})
                            })
                except Exception as e:
                    print(f"Skipping {file_path}: {e}")
        
        if not docs:
            print("No code snippets found to index")
            return
        
        print(f"Encoding {len(docs)} code snippets (functions/classes/files)...")
        embeddings = self.embedding_model.encode(docs, convert_to_numpy=True, show_progress_bar=True)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatL2(dimension)
        self.faiss_index.add(embeddings.astype('float32'))
        
        # Save index
        faiss.write_index(self.faiss_index, self.vector_index_file)
        # Save file map
        self.save_file_map()
        print(f"✅ Built vector index for {len(docs)} code snippets. Index saved to {self.vector_index_file}")
    
    def load_index(self):
        """Load existing FAISS index"""
        if not Path(self.vector_index_file).exists():
            return False
        
        try:
            self.faiss_index = faiss.read_index(self.vector_index_file)
            # Load file map if available
            file_map_path = self.vector_index_file.replace(".index", "_map.pkl")
            if Path(file_map_path).exists():
                import pickle
                with open(file_map_path, "rb") as f:
                    loaded_map = pickle.load(f)
                    # Handle both old format (list of strings) and new format (list of dicts)
                    if loaded_map and isinstance(loaded_map[0], str):
                        # Convert old format to new format
                        self.file_map = [
                            {"file_path": path, "function_name": path, "start_line": 1, "end_line": 1, "snippet": ""}
                            for path in loaded_map
                        ]
                    else:
                        self.file_map = loaded_map
            return True
        except Exception as e:
            print(f"Error loading index: {e}")
            return False
    
    def save_file_map(self):
        """Save file map to disk"""
        if self.file_map:
            import pickle
            file_map_path = self.vector_index_file.replace(".index", "_map.pkl")
            with open(file_map_path, "wb") as f:
                pickle.dump(self.file_map, f)
    
    def semantic_search(self, query, top_k=5, use_hybrid=True):
        """
        Perform semantic search and return results.
        If use_hybrid=True and bm25_service is available, combines BM25 and FAISS scores.
        """
        if not self.faiss_index:
            if not self.load_index():
                raise RuntimeError("No vector index available. Build index first.")
        
        if not self.embedding_model:
            raise RuntimeError("Embedding model not loaded")
        
        # Encode query
        query_emb = self.embedding_model.encode([query], convert_to_numpy=True)
        
        # FAISS search - get more results for hybrid scoring
        search_k = top_k * 3 if use_hybrid and self.bm25_service else top_k
        k = min(search_k, len(self.file_map))
        distances, indices = self.faiss_index.search(query_emb.astype('float32'), k)
        
        # Convert distances to similarity scores (lower distance = higher similarity)
        # Normalize to 0-1 range
        max_dist = distances[0].max() if len(distances[0]) > 0 else 1.0
        min_dist = distances[0].min() if len(distances[0]) > 0 else 0.0
        dist_range = max_dist - min_dist if max_dist > min_dist else 1.0
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.file_map):
                item = self.file_map[idx]
                
                # Convert L2 distance to similarity score (0-1, higher is better)
                distance = float(distances[0][i])
                semantic_score = 1.0 - ((distance - min_dist) / dist_range) if dist_range > 0 else 0.5
                
                result = {
                    "file_path": item.get("file_path", item) if isinstance(item, dict) else item,
                    "function_name": item.get("function_name", ""),
                    "start_line": item.get("start_line", 1),
                    "end_line": item.get("end_line", 1),
                    "snippet": item.get("snippet", ""),
                    "semantic_score": semantic_score,
                    "score": semantic_score  # Default score
                }
                
                # Hybrid search: combine with BM25 if available
                if use_hybrid and self.bm25_service:
                    try:
                        # Get BM25 results for the same file
                        bm25_results = self.bm25_service.search(query, max_results=20)
                        # Find matching file in BM25 results
                        bm25_score = 0.0
                        for bm25_result in bm25_results:
                            if bm25_result.get("file_path") == result["file_path"]:
                                # Normalize BM25 score (typically 0-10 range)
                                bm25_score = min(bm25_result.get("score", 0) / 10.0, 1.0)
                                break
                        
                        # Weighted combination: 60% semantic, 40% BM25
                        combined_score = 0.6 * semantic_score + 0.4 * bm25_score
                        result["bm25_score"] = bm25_score
                        result["score"] = combined_score
                    except Exception as e:
                        # If BM25 fails, use semantic score only
                        pass
                
                results.append(result)
        
        # Sort by combined score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top_k results
        return results[:top_k]
    
    def explain_results(self, query, results, include_context=True):
        """
        Use OpenAI to explain the relationship between query and results.
        If OpenAI is not available, returns a simple summary.
        """
        if not results:
            return "No results to explain."
        
        # Build context from results
        context_parts = []
        for i, result in enumerate(results[:5], 1):  # Top 5 results
            file_path = result.get("file_path", "unknown")
            func_name = result.get("function_name", "")
            start_line = result.get("start_line", 1)
            end_line = result.get("end_line", 1)
            snippet = result.get("snippet", "")
            score = result.get("score", 0)
            
            context_parts.append(
                f"Result {i} (score: {score:.2f}):\n"
                f"File: {file_path}\n"
                f"Function: {func_name}\n"
                f"Lines: {start_line}-{end_line}\n"
                f"Code:\n{snippet[:300]}..."  # Limit snippet length
            )
        
        context = "\n\n---\n\n".join(context_parts)
        
        if not self.client:
            # Simple explanation without OpenAI
            summary = f"Found {len(results)} relevant code snippets for '{query}':\n\n"
            for i, result in enumerate(results[:3], 1):
                summary += f"{i}. {result.get('function_name', result.get('file_path', 'unknown'))} "
                summary += f"(score: {result.get('score', 0):.2f})\n"
            return summary
        
        prompt = f"""Question: {query}

Code Context:
{context}

Explain the relevant logic and reasoning behind where and how this happens in the code.
Be concise and specific. Focus on the connection between the question and the code snippets.
If multiple results are shown, explain how they relate to each other."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional code analyst. Explain code relationships clearly and concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            # Fallback to simple summary
            summary = f"Found {len(results)} relevant code snippets for '{query}':\n\n"
            for i, result in enumerate(results[:3], 1):
                summary += f"{i}. {result.get('function_name', result.get('file_path', 'unknown'))} "
                summary += f"(score: {result.get('score', 0):.2f})\n"
            return summary
    
    def is_indexed(self):
        """Check if vector index exists"""
        return self.faiss_index is not None or Path(self.vector_index_file).exists()
    
    def file_count(self):
        """Get number of indexed code snippets (functions/classes/files)"""
        return len(self.file_map) if self.file_map else 0
    
    def get_code_snippet(self, file_path: str, start_line: int, end_line: int) -> Optional[str]:
        """Get code snippet from file at specified lines"""
        try:
            full_path = self.root_path / file_path if self.root_path else Path(file_path)
            if not full_path.exists():
                return None
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Extract lines (1-indexed to 0-indexed)
            snippet_lines = lines[start_line-1:end_line]
            return ''.join(snippet_lines)
        except Exception:
            return None

