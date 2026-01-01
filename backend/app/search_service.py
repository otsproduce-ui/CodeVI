"""
Search Service - Manages indexing, persistence and searching
Enhanced with semantic parsing and embeddings
"""
from pathlib import Path
import pickle
import sys
import os
import numpy as np

# Add parent directory to path for search_engine import
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

# Import search_engine from parent directory
from search_engine import SearchEngine
from app.code_parser import CodeParser
from app.semantic_service import SemanticSearchService
from rank_bm25 import BM25Okapi
import re


class SearchService:
    """Service managing indexing, persistence and searching with semantic capabilities."""

    def __init__(self, root_path: str, index_file: str):
        self.root_path = Path(root_path)
        self.index_file = index_file
        self.engine = None  # BM25 engine (legacy)
        
        # New semantic components
        self.parser = CodeParser()
        self.semantic_index_file = str(Path(index_file).parent / "semantic_index.pkl")
        self.semantic_index_data = []
        self.semantic_service = None  # Will be initialized when needed
        self.is_semantic_indexed = False
        
        # BM25 components for hybrid search
        self.bm25 = None
        self.tokenized_corpus = []

    def load_index(self):
        """Load index if exists"""
        if Path(self.index_file).exists():
            try:
                with open(self.index_file, "rb") as f:
                    self.engine = pickle.load(f)
                print(f"[OK] Index loaded from {self.index_file}")
                return True
            except Exception as e:
                print(f"[WARN] Error loading index: {e}")
                return False
        else:
            print("[WARN] No existing index found.")
            return False

    def _init_semantic_service(self):
        """Initialize semantic service if not already initialized"""
        if self.semantic_service is None:
            try:
                self.semantic_service = SemanticSearchService(
                    root_path=str(self.root_path),
                    vector_index_file=str(Path(self.index_file).parent / "vector.index")
                )
            except Exception as e:
                print(f"Warning: Could not initialize semantic service: {e}")
                return False
        return self.semantic_service is not None
    
    def index_codebase(self):
        """Index a new codebase with both BM25 and semantic indexing"""
        # Legacy BM25 indexing
        self.engine = SearchEngine(self.root_path)
        self.engine.index_codebase()
        self.save_index()
        
        # New semantic indexing
        self.scan_semantic()
    
    def scan_semantic(self):
        """
        מבצע סריקה חכמה של הקוד (Python / JS / HTML)
        יוצר אינדקס סמנטי עם embeddings עבור כל רכיב קוד
        """
        print("🔍 Scanning codebase for semantic indexing...")
        
        if not self._init_semantic_service():
            print("⚠️ Semantic service not available, skipping semantic indexing")
            return {"count": 0, "index_path": None}
        
        if not self.semantic_service.embedding_model:
            print("⚠️ Embedding model not loaded, skipping semantic indexing")
            return {"count": 0, "index_path": None}
        
        all_items = []
        ignored_dirs = {'venv', '__pycache__', '.git', 'node_modules', '.venv', 'env'}
        
        # Walk through all files
        for root, dirs, files in os.walk(self.root_path):
            # Skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in self.parser.supported_ext:
                    continue
                
                fpath = Path(root) / fname
                try:
                    parsed = self.parser.parse_file(fpath)
                    if parsed:
                        all_items.extend(parsed)
                except Exception as e:
                    print(f"⚠️ Error parsing {fpath}: {e}")
                    continue
        
        print(f"✅ Extracted {len(all_items)} code components")
        
        if not all_items:
            print("⚠️ No code components found")
            return {"count": 0, "index_path": None}
        
        # Create embeddings and BM25 tokens for each component
        print("📊 Generating embeddings and BM25 tokens...")
        enriched = []
        tokenized_corpus = []  # For BM25
        
        # Prepare texts for batch encoding
        texts_for_embedding = []
        for item in all_items:
            # Build text for embedding (same format as semantic_service)
            text = f"{item.get('type', 'code')}: {item.get('name', '')}\n"
            if item.get('docstring'):
                text += f"Description: {item['docstring']}\n"
            elif item.get('context'):
                text += f"{item['context']}\n"
            
            # Add context: API calls
            api_calls = item.get('api_calls', [])
            if api_calls:
                api_info = ", ".join([f"{ac.get('method', 'GET')} {ac.get('endpoint', '')}" 
                                     for ac in api_calls[:3]])
                text += f"API calls: {api_info}\n"
            
            # Add context: Event listeners
            event_listeners = item.get('event_listeners', [])
            if event_listeners:
                event_info = ", ".join([f"{el.get('event', '')} -> {el.get('handler', '')}" 
                                       for el in event_listeners[:3]])
                text += f"Events: {event_info}\n"
            
            # Add context: Routes
            routes = item.get('routes', [])
            if routes:
                route_info = ", ".join([f"{r.get('method', 'GET')} {r.get('path', '')}" 
                                       for r in routes[:3]])
                text += f"Routes: {route_info}\n"
            
            # Add code
            text += f"\nCode:\n{item.get('code', '')[:500]}"  # First 500 chars
            
            texts_for_embedding.append(text)
            
            # Tokenize for BM25 (same text used for embedding)
            tokens = self._tokenize_for_bm25(text)
            tokenized_corpus.append(tokens)
        
        # Batch encode for efficiency
        try:
            embeddings = self.semantic_service.embedding_model.encode(
                texts_for_embedding, 
                convert_to_numpy=True,
                show_progress_bar=True
            )
            
            # Combine items with embeddings
            for item, embedding in zip(all_items, embeddings):
                item["embedding"] = embedding.tolist()  # Convert to list for pickle
                enriched.append(item)
            
            # Build BM25 index
            self.bm25 = BM25Okapi(tokenized_corpus)
            self.tokenized_corpus = tokenized_corpus
            
            # Save to index (include BM25 corpus)
            with open(self.semantic_index_file, "wb") as f:
                pickle.dump({
                    "data": enriched,
                    "corpus": tokenized_corpus
                }, f)
            
            self.semantic_index_data = enriched
            self.is_semantic_indexed = True
            print(f"💾 Semantic index saved to {self.semantic_index_file}")
            print(f"✅ Indexed {len(enriched)} code components with embeddings and BM25 tokens")
            
            return {
                "count": len(enriched),
                "index_path": self.semantic_index_file
            }
        except Exception as e:
            print(f"❌ Error generating embeddings: {e}")
            import traceback
            traceback.print_exc()
            return {"count": 0, "index_path": None}

    def save_index(self):
        """Save BM25 index to disk"""
        if self.engine:
            try:
                with open(self.index_file, "wb") as f:
                    pickle.dump(self.engine, f)
                print(f"[OK] Index saved to {self.index_file}")
            except Exception as e:
                print(f"[WARN] Error saving index: {e}")

    def _tokenize_for_bm25(self, text: str) -> list:
        """Tokenize text for BM25 indexing"""
        # Split on whitespace and common code delimiters
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def load_semantic_index(self):
        """טעינת אינדקס סמנטי קיים"""
        if not Path(self.semantic_index_file).exists():
            print("⚠️ No semantic_index.pkl found. Run scan_semantic() first.")
            return False
        
        try:
            with open(self.semantic_index_file, "rb") as f:
                payload = pickle.load(f)
                
                # Handle both old format (list) and new format (dict with data and corpus)
                if isinstance(payload, dict) and "data" in payload:
                    self.semantic_index_data = payload["data"]
                    self.tokenized_corpus = payload.get("corpus", [])
                    # Rebuild BM25 index
                    if self.tokenized_corpus:
                        self.bm25 = BM25Okapi(self.tokenized_corpus)
                else:
                    # Old format - just a list
                    self.semantic_index_data = payload
                    self.tokenized_corpus = []
                    # Rebuild corpus from data
                    for item in self.semantic_index_data:
                        # Reconstruct text for tokenization
                        text = f"{item.get('type', 'code')}: {item.get('name', '')}\n"
                        if item.get('docstring'):
                            text += f"{item['docstring']}\n"
                        text += item.get('code', '')
                        self.tokenized_corpus.append(self._tokenize_for_bm25(text))
                    if self.tokenized_corpus:
                        self.bm25 = BM25Okapi(self.tokenized_corpus)
            
            self.is_semantic_indexed = True
            print(f"📦 Loaded semantic index with {len(self.semantic_index_data)} items.")
            if self.bm25:
                print(f"📦 BM25 index ready with {len(self.tokenized_corpus)} tokenized documents.")
            return True
        except Exception as e:
            print(f"⚠️ Error loading semantic index: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def search(self, query, max_results=10, use_hybrid=True, semantic_weight=0.6, lexical_weight=0.4, adaptive=True):
        """
        Perform a search on indexed codebase.
        If use_hybrid=True and semantic index exists, uses hybrid search (BM25 + Semantic).
        Otherwise falls back to BM25 search.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            use_hybrid: Whether to use hybrid search
            semantic_weight: Weight for semantic search (None = adaptive)
            lexical_weight: Weight for lexical search (None = adaptive)
            adaptive: If True, weights adapt based on query length
        """
        # Try hybrid search first
        if use_hybrid:
            hybrid_results = self.hybrid_search(query, max_results, semantic_weight, lexical_weight, adaptive)
            if hybrid_results:
                return hybrid_results
        
        # Fallback to semantic search
        if self.is_semantic_indexed or len(self.semantic_index_data) > 0:
            semantic_results = self.search_semantic(query, max_results)
            if semantic_results:
                return semantic_results
        
        # Fallback to BM25 (legacy)
        if not self.engine:
            raise RuntimeError("Engine not initialized. Please scan first.")
        return self.engine.search(query, max_results)
    
    def _calculate_adaptive_weights(self, query: str) -> tuple:
        """
        Calculate adaptive weights based on query characteristics.
        Short queries (1-2 words) → more lexical weight
        Long queries (3+ words) → more semantic weight
        """
        query_words = len(query.split())
        
        if query_words <= 2:
            # Short queries benefit more from exact matches (BM25)
            return 0.4, 0.6  # semantic_weight, lexical_weight
        elif query_words <= 4:
            # Medium queries - balanced
            return 0.6, 0.4
        else:
            # Long queries benefit more from semantic understanding
            return 0.7, 0.3
    
    def hybrid_search(self, query: str, max_results: int = 10, semantic_weight: float = None, lexical_weight: float = None, adaptive: bool = True):
        """
        מבצע חיפוש היברידי - שילוב של BM25 ו-Embeddings עם משקולות אדפטיביות
        
        Args:
            query: שאילתת חיפוש
            max_results: מספר תוצאות מקסימלי
            semantic_weight: משקל לחיפוש סמנטי (None = adaptive)
            lexical_weight: משקל לחיפוש לקסיקלי (None = adaptive)
            adaptive: אם True, משקולות מתאימות אוטומטית לפי אורך השאילתה
        
        Returns:
            רשימת תוצאות מדורגות לפי ציון משולב
        """
        # Calculate adaptive weights if needed
        if adaptive and (semantic_weight is None or lexical_weight is None):
            semantic_weight, lexical_weight = self._calculate_adaptive_weights(query)
        
        if not self.is_semantic_indexed or len(self.semantic_index_data) == 0:
            loaded = self.load_semantic_index()
            if not loaded:
                return []
        
        if not self.semantic_index_data:
            return []
        
        if not self.bm25 or not self.tokenized_corpus:
            print("⚠️ BM25 index not available, falling back to semantic search only")
            return self.search_semantic(query, max_results)
        
        if not self._init_semantic_service():
            return []
        
        if not self.semantic_service.embedding_model:
            return []
        
        # Normalize weights
        total_weight = semantic_weight + lexical_weight
        if total_weight > 0:
            semantic_weight = semantic_weight / total_weight
            lexical_weight = lexical_weight / total_weight
        
        # 1. BM25 scores
        query_tokens = self._tokenize_for_bm25(query)
        if not query_tokens:
            # If query can't be tokenized, use semantic only
            return self.search_semantic(query, max_results)
        
        bm25_scores = self.bm25.get_scores(query_tokens)
        
        # 2. Semantic scores
        try:
            query_vector = self.semantic_service.embedding_model.encode(
                [query], 
                convert_to_numpy=True
            )[0]
        except Exception as e:
            print(f"⚠️ Error encoding query: {e}")
            return []
        
        semantic_scores = []
        for item in self.semantic_index_data:
            if "embedding" not in item:
                semantic_scores.append(0.0)
                continue
            
            embedding = np.array(item["embedding"])
            # Cosine similarity
            similarity = np.dot(query_vector, embedding) / (
                np.linalg.norm(query_vector) * np.linalg.norm(embedding)
            )
            semantic_scores.append(float(similarity))
        
        semantic_scores = np.array(semantic_scores)
        
        # 3. Normalize scores to 0-1 range
        # BM25 normalization
        bm25_min = np.min(bm25_scores)
        bm25_max = np.max(bm25_scores)
        bm25_range = bm25_max - bm25_min
        if bm25_range > 0:
            bm25_norm = (bm25_scores - bm25_min) / bm25_range
        else:
            bm25_norm = np.zeros_like(bm25_scores)
        
        # Semantic normalization
        sem_min = np.min(semantic_scores)
        sem_max = np.max(semantic_scores)
        sem_range = sem_max - sem_min
        if sem_range > 0:
            sem_norm = (semantic_scores - sem_min) / sem_range
        else:
            sem_norm = np.zeros_like(semantic_scores)
        
        # 4. Combine scores with weights
        combined_scores = semantic_weight * sem_norm + lexical_weight * bm25_norm
        
        # 5. Rank and get top results
        ranked_indices = np.argsort(combined_scores)[::-1][:max_results]
        
        # 6. Format results
        formatted_results = []
        for idx in ranked_indices:
            item = self.semantic_index_data[idx]
            formatted_results.append({
                "score": round(float(combined_scores[idx]), 3),
                "semantic_score": round(float(sem_norm[idx]), 3),
                "bm25_score": round(float(bm25_norm[idx]), 3),
                "file_path": item.get("file_path", ""),
                "name": item.get("name", ""),
                "full_name": item.get("full_name", item.get("name", "")),
                "type": item.get("type", "code"),
                "language": item.get("language", ""),
                "context": item.get("context", item.get("docstring", "")),
                "start_line": item.get("start_line", None),
                "end_line": item.get("end_line", None),
                "line_number": item.get("start_line", None),  # For backward compatibility
                "code": item.get("code", "")[:200],  # Preview
                "content": item.get("code", "")[:200],  # For backward compatibility
                "api_calls": item.get("api_calls", []),
                "event_listeners": item.get("event_listeners", []),
                "routes": item.get("routes", [])
            })
        
        return formatted_results
    
    def search_semantic(self, query: str, max_results: int = 10):
        """
        חיפוש סמנטי בלבד (בהמשך נוסיף שילוב עם BM25)
        """
        if not self.is_semantic_indexed or len(self.semantic_index_data) == 0:
            loaded = self.load_semantic_index()
            if not loaded:
                return []
        
        if not self.semantic_index_data:
            return []
        
        if not self._init_semantic_service():
            return []
        
        if not self.semantic_service.embedding_model:
            return []
        
        # Encode query
        try:
            query_vector = self.semantic_service.embedding_model.encode(
                [query], 
                convert_to_numpy=True
            )[0]
        except Exception as e:
            print(f"⚠️ Error encoding query: {e}")
            return []
        
        # Calculate cosine similarity between query and all components
        results = []
        for item in self.semantic_index_data:
            if "embedding" not in item:
                continue
            
            embedding = np.array(item["embedding"])
            # Cosine similarity
            similarity = np.dot(query_vector, embedding) / (
                np.linalg.norm(query_vector) * np.linalg.norm(embedding)
            )
            results.append((similarity, item))
        
        # Sort by similarity and take top results
        results = sorted(results, key=lambda x: x[0], reverse=True)[:max_results]
        
        # Format results
        formatted_results = []
        for sim, item in results:
            formatted_results.append({
                "score": round(float(sim), 3),
                "file_path": item.get("file_path", ""),
                "name": item.get("name", ""),
                "full_name": item.get("full_name", item.get("name", "")),
                "type": item.get("type", "code"),
                "language": item.get("language", ""),
                "context": item.get("context", item.get("docstring", "")),
                "start_line": item.get("start_line", None),
                "end_line": item.get("end_line", None),
                "code": item.get("code", "")[:200],  # Preview
                "api_calls": item.get("api_calls", []),
                "event_listeners": item.get("event_listeners", []),
                "routes": item.get("routes", [])
            })
        
        return formatted_results

    def get_graph(self):
        """Return relationship graph"""
        if not self.engine:
            raise RuntimeError("Engine not initialized. Please scan first.")
        return self.engine.extract_graph()

    def file_count(self):
        """Return number of indexed files"""
        return self.engine.get_file_count() if self.engine else 0

    def is_indexed(self):
        """Check if codebase is indexed (BM25)"""
        return self.engine and self.engine.is_indexed()
    
    def is_semantic_indexed_check(self):
        """Check if semantic index exists and load if needed"""
        if not self.is_semantic_indexed or len(self.semantic_index_data) == 0:
            loaded = self.load_semantic_index()
            if loaded:
                self.is_semantic_indexed = True
        return len(self.semantic_index_data) > 0

