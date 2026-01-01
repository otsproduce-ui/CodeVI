"""
Hybrid Search Pipeline - Complete architecture for intelligent code search
ארכיטקטורה משופרת עם 4 שכבות אינטליגנציה

Architecture:
1. Query Understanding Layer - NLP + Intent Detection (functionality/location/configuration/ui-interaction)
2. Multi-Modal Search Layer - BM25 + Embeddings + Graph Context
3. Hybrid Reranking Layer - Score Fusion (α, β, γ) עם Domain-Aware Boosting
4. Output Formatter & Explanation Layer - Natural Language Summary + Frontend↔Backend Links
"""
import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, util
from pathlib import Path
import pickle
import json


class QueryUnderstandingLayer:
    """
    Query Understanding Layer - NLP + Intent Detection
    מבין את הכוונה של המשתמש: functionality, location, configuration, ui-interaction
    """
    
    def __init__(self):
        # Synonyms dictionary for code-related terms
        self.synonyms = {
            "search": ["find", "query", "lookup", "seek"],
            "button": ["btn", "trigger", "click", "element"],
            "function": ["func", "method", "procedure", "handler"],
            "api": ["endpoint", "route", "url", "request"],
            "login": ["auth", "authenticate", "signin"],
            "error": ["exception", "fail", "issue", "problem"],
            "database": ["db", "sql", "data", "storage"],
            "config": ["configuration", "settings", "options"]
        }
        
        # Intent patterns
        self.intent_patterns = {
            "functionality": [
                "how", "how does", "how do", "how is", "how are",
                "what does", "what is", "explain", "describe", "work", "works"
            ],
            "location": [
                "where", "where is", "where are", "find", "locate",
                "which file", "which function", "in which"
            ],
            "configuration": [
                "config", "configuration", "settings", "options",
                "define", "defined", "path", "url", "database"
            ],
            "ui-interaction": [
                "button", "click", "form", "input", "ui", "interface",
                "frontend", "user", "interaction"
            ]
        }
    
    def preprocess(self, query: str) -> Dict[str, any]:
        """
        Preprocess query: normalize, expand, detect intent
        
        Returns:
            {
                "normalized": "normalized query",
                "tokens": ["list", "of", "tokens"],
                "expanded": "expanded query with synonyms",
                "intent": "function" | "api" | "ui" | "general"
            }
        """
        # 1. Normalize text
        normalized = self._normalize_text(query)
        
        # 2. Tokenize
        tokens = self._tokenize(normalized)
        
        # 3. Expand with synonyms
        expanded = self._expand_synonyms(normalized, tokens)
        
        # 4. Detect intent
        intent = self._detect_intent(normalized, tokens)
        
        return {
            "original": query,
            "normalized": normalized,
            "tokens": tokens,
            "expanded": expanded,
            "intent": intent
        }
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text: lowercase, remove special chars"""
        text = text.lower().strip()
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        return [word for word in text.split() if len(word) > 1]
    
    def _expand_synonyms(self, query: str, tokens: List[str]) -> str:
        """Expand query with synonyms"""
        expanded_tokens = []
        
        for token in tokens:
            expanded_tokens.append(token)
            # Add synonyms if available
            if token in self.synonyms:
                expanded_tokens.extend(self.synonyms[token][:2])  # Add top 2 synonyms
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tokens = []
        for token in expanded_tokens:
            if token not in seen:
                seen.add(token)
                unique_tokens.append(token)
        
        return " ".join(unique_tokens)
    
    def _detect_intent(self, query: str, tokens: List[str]) -> str:
        """
        Detect query intent with advanced pattern matching
        Returns: "functionality" | "location" | "configuration" | "ui-interaction" | "general"
        """
        query_lower = query.lower()
        
        # Check each intent category
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in query_lower:
                    score += 1
            intent_scores[intent] = score
        
        # Find intent with highest score
        if intent_scores:
            max_intent = max(intent_scores.items(), key=lambda x: x[1])
            if max_intent[1] > 0:
                return max_intent[0]
        
        # Fallback: check for specific keywords
        if any(kw in tokens for kw in ["function", "func", "method", "def", "procedure", "handler"]):
            return "functionality"
        
        if any(kw in tokens for kw in ["api", "endpoint", "route", "url", "request"]):
            return "functionality"  # API is usually about functionality
        
        if any(kw in tokens for kw in ["button", "btn", "click", "element", "form", "input", "ui"]):
            return "ui-interaction"
        
        if any(kw in tokens for kw in ["config", "configuration", "settings", "path", "database"]):
            return "configuration"
        
        return "general"


class LexicalSearchEngine:
    """
    Lexical Search Layer (BM25)
    חיפוש טקסט מדויק ומהיר
    """
    
    def __init__(self):
        self.bm25 = None
        self.tokenized_corpus = []
        self.docs = []
        self.doc_metadata = []  # Metadata for each document
    
    def index(self, documents: List[str], metadata: List[Dict] = None):
        """
        Index documents for BM25 search
        
        Args:
            documents: List of document texts
            metadata: Optional list of metadata dicts (one per document)
        """
        self.docs = documents
        self.doc_metadata = metadata or [{}] * len(documents)
        
        # Tokenize documents
        self.tokenized_corpus = [self._tokenize(doc) for doc in documents]
        
        # Build BM25 index
        self.bm25 = BM25Okapi(self.tokenized_corpus)
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[Dict, float]]:
        """
        Search using BM25
        
        Returns:
            List of (metadata_dict, score) tuples
        """
        if not self.bm25:
            return []
        
        # Tokenize query
        tokenized_query = self._tokenize(query)
        
        if not tokenized_query:
            return []
        
        # Get BM25 scores
        scores = self.bm25.get_scores(tokenized_query)
        
        # Rank results
        ranked_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in ranked_indices:
            if scores[idx] > 0:  # Only include results with positive scores
                results.append((self.doc_metadata[idx], float(scores[idx])))
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for BM25"""
        # Simple tokenization: split on whitespace and keep alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def save_index(self, file_path: Path):
        """Save BM25 index to disk"""
        index_data = {
            "tokenized_corpus": self.tokenized_corpus,
            "docs": self.docs,
            "doc_metadata": self.doc_metadata
        }
        with open(file_path, "wb") as f:
            pickle.dump(index_data, f)
    
    def load_index(self, file_path: Path):
        """Load BM25 index from disk"""
        with open(file_path, "rb") as f:
            index_data = pickle.load(f)
        
        self.tokenized_corpus = index_data["tokenized_corpus"]
        self.docs = index_data["docs"]
        self.doc_metadata = index_data["doc_metadata"]
        
        # Rebuild BM25 index
        self.bm25 = BM25Okapi(self.tokenized_corpus)


class SemanticSearchEngine:
    """
    Semantic Search Layer (Embeddings)
    חיפוש לפי משמעות ולא רק מילים
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", model_path: Optional[Path] = None):
        """
        Initialize semantic search engine
        
        Args:
            model_name: HuggingFace model name
            model_path: Optional local path to model
        """
        if model_path and Path(model_path).exists():
            print(f"Loading local model from: {model_path}")
            self.model = SentenceTransformer(str(model_path))
        else:
            print(f"Loading model: {model_name}")
            self.model = SentenceTransformer(model_name)
        
        self.embeddings = None
        self.docs = []
        self.doc_metadata = []
    
    def index(self, documents: List[str], metadata: List[Dict] = None, batch_size: int = 32):
        """
        Index documents with embeddings
        
        Args:
            documents: List of document texts
            metadata: Optional list of metadata dicts
            batch_size: Batch size for encoding
        """
        self.docs = documents
        self.doc_metadata = metadata or [{}] * len(documents)
        
        print(f"Encoding {len(documents)} documents...")
        # Encode documents
        self.embeddings = self.model.encode(
            documents,
            convert_to_tensor=True,
            show_progress_bar=True,
            batch_size=batch_size
        )
        print("✅ Encoding complete")
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[Dict, float]]:
        """
        Search using semantic similarity
        
        Returns:
            List of (metadata_dict, score) tuples
        """
        if self.embeddings is None:
            return []
        
        # Encode query
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        
        # Semantic search
        hits = util.semantic_search(query_embedding, self.embeddings, top_k=top_k)[0]
        
        results = []
        for hit in hits:
            idx = hit['corpus_id']
            score = hit['score']
            results.append((self.doc_metadata[idx], float(score)))
        
        return results
    
    def save_index(self, embeddings_path: Path, metadata_path: Path):
        """Save embeddings and metadata to disk"""
        # Save embeddings as numpy array
        if self.embeddings is not None:
            np.save(embeddings_path, self.embeddings.cpu().numpy())
        
        # Save metadata as JSON
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.doc_metadata, f, indent=2)
    
    def load_index(self, embeddings_path: Path, metadata_path: Path):
        """Load embeddings and metadata from disk"""
        # Load embeddings
        embeddings_array = np.load(embeddings_path)
        # Convert to tensor format
        import torch
        self.embeddings = torch.from_numpy(embeddings_array)
        
        # Load metadata
        with open(metadata_path, "r", encoding="utf-8") as f:
            self.doc_metadata = json.load(f)
        
        # Reconstruct docs from metadata (if needed)
        self.docs = [m.get("snippet", m.get("code", "")) for m in self.doc_metadata]


class HybridRanker:
    """
    Hybrid Ranker Layer
    מאחד תוצאות מ-Lexical ו-Semantic search עם משקולות
    """
    
    def __init__(self, alpha: float = 0.7, beta: float = 0.3):
        """
        Initialize hybrid ranker
        
        Args:
            alpha: Weight for semantic search (default 0.7 = 70%)
            beta: Weight for lexical search (default 0.3 = 30%)
        """
        self.alpha = alpha
        self.beta = beta
    
    def combine_results(
        self,
        lexical_results: List[Tuple[Dict, float]],
        semantic_results: List[Tuple[Dict, float]],
        context_results: List[Tuple[Dict, float]] = None,
        intent: str = "general",
        top_k: int = 10
    ) -> List[Dict]:
        """
        Combine lexical, semantic, and context results with weighted scoring
        
        Args:
            lexical_results: List of (metadata, score) from BM25
            semantic_results: List of (metadata, score) from embeddings
            context_results: List of (metadata, score) from graph context (optional)
            intent: Query intent for adaptive weights
            top_k: Number of final results
        
        Returns:
            List of result dicts with combined scores
        """
        # Get adaptive weights based on intent
        alpha, beta, gamma = self.get_adaptive_weights(intent)
        
        # Normalize scores to [0, 1] range
        lex_scores_dict = self._normalize_scores(lexical_results)
        sem_scores_dict = self._normalize_scores(semantic_results)
        ctx_scores_dict = self._normalize_scores(context_results or [])
        
        # Get all unique documents
        all_docs = set(lex_scores_dict.keys()) | set(sem_scores_dict.keys()) | set(ctx_scores_dict.keys())
        
        # Combine scores with three weights
        combined_scores = {}
        for doc_key in all_docs:
            lex_score = lex_scores_dict.get(doc_key, 0.0)
            sem_score = sem_scores_dict.get(doc_key, 0.0)
            ctx_score = ctx_scores_dict.get(doc_key, 0.0)
            
            # Weighted combination: α * semantic + β * lexical + γ * context
            combined_score = alpha * sem_score + beta * lex_score + gamma * ctx_score
            combined_scores[doc_key] = combined_score
        
        # Rank by combined score
        ranked = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Build result list
        results = []
        for doc_key, score in ranked[:top_k]:
            # Get metadata from either source
            metadata = lex_scores_dict.get(doc_key, (None, 0))[0] if doc_key in lex_scores_dict else \
                      sem_scores_dict.get(doc_key, (None, 0))[0] if doc_key in sem_scores_dict else None
            
            if metadata:
                result = dict(metadata)
                result["score"] = score
                result["lexical_score"] = lex_scores_dict.get(doc_key, (None, 0))[1] if doc_key in lex_scores_dict else 0.0
                result["semantic_score"] = sem_scores_dict.get(doc_key, (None, 0))[1] if doc_key in sem_scores_dict else 0.0
                result["context_score"] = ctx_scores_dict.get(doc_key, (None, 0))[1] if doc_key in ctx_scores_dict else 0.0
                results.append(result)
        
        return results
    
    def _normalize_scores(self, results: List[Tuple[Dict, float]]) -> Dict[str, Tuple[Dict, float]]:
        """
        Normalize scores to [0, 1] and create dict keyed by document identifier
        
        Returns:
            Dict mapping doc_key -> (metadata, normalized_score)
        """
        if not results:
            return {}
        
        # Extract scores
        scores = [score for _, score in results]
        
        # Normalize to [0, 1]
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 1
        
        if max_score == min_score:
            normalized_scores = [1.0] * len(scores)
        else:
            normalized_scores = [(s - min_score) / (max_score - min_score) for s in scores]
        
        # Create dict keyed by document identifier
        result_dict = {}
        for (metadata, _), norm_score in zip(results, normalized_scores):
            # Use file_path + name as unique key
            doc_key = self._get_doc_key(metadata)
            result_dict[doc_key] = (metadata, norm_score)
        
        return result_dict
    
    def _get_doc_key(self, metadata: Dict) -> str:
        """Generate unique key for document"""
        file_path = metadata.get("file_path", "")
        name = metadata.get("name", metadata.get("full_name", ""))
        start_line = metadata.get("start_line", 0)
        return f"{file_path}::{name}::{start_line}"


class GraphContextSearch:
    """
    Graph Context Search - Multi-Modal Search Layer component
    מחפש לפי קשרים גרפיים בין רכיבי קוד (frontend ↔ backend)
    """
    
    def __init__(self, graph_service=None):
        """
        Initialize graph context search
        
        Args:
            graph_service: Optional GraphService instance for finding relationships
        """
        self.graph_service = graph_service
    
    def expand_related(
        self,
        base_results: List[Tuple[Dict, float]],
        depth: int = 2
    ) -> List[Tuple[Dict, float]]:
        """
        Expand search results with graph-based related components
        
        Args:
            base_results: List of (metadata, score) from semantic/lexical search
            depth: Depth of relationship expansion
        
        Returns:
            List of (metadata, context_score) tuples
        """
        if not self.graph_service:
            return []
        
        context_results = []
        seen_docs = set()
        
        for metadata, base_score in base_results[:10]:  # Limit to top 10 for expansion
            doc_key = self._get_doc_key(metadata)
            if doc_key in seen_docs:
                continue
            seen_docs.add(doc_key)
            
            # Find related components
            try:
                related = self.graph_service.find_related(metadata)
                
                # Add base result with context boost
                context_results.append((metadata, base_score * 1.2))  # Boost for being in base results
                
                # Add related components with context scores
                for rel in related[:5]:  # Top 5 related
                    rel_key = self._get_doc_key(rel)
                    if rel_key not in seen_docs:
                        seen_docs.add(rel_key)
                        # Context score based on relation strength
                        strength_scores = {"strong": 0.8, "medium": 0.5, "weak": 0.2}
                        context_score = strength_scores.get(rel.get("relation_strength", "weak"), 0.2)
                        context_results.append((rel, context_score))
            except Exception as e:
                # If graph service fails, just use base result
                context_results.append((metadata, base_score))
        
        return context_results
    
    def _get_doc_key(self, metadata: Dict) -> str:
        """Generate unique key for document"""
        file_path = metadata.get("file_path", "")
        name = metadata.get("name", metadata.get("full_name", ""))
        start_line = metadata.get("start_line", 0)
        return f"{file_path}::{name}::{start_line}"


class OutputFormatter:
    """
    Output Formatter & Explanation Layer
    יוצר Natural Language Summary ומקשר frontend↔backend
    """
    
    def __init__(self, explanation_service=None):
        """
        Initialize output formatter
        
        Args:
            explanation_service: Optional ExplanationService for generating summaries
        """
        self.explanation_service = explanation_service
    
    def format_results(
        self,
        query: str,
        intent: str,
        results: List[Dict]
    ) -> Dict:
        """
        Format search results with natural language summary and links
        
        Args:
            query: Original query
            intent: Detected intent
            results: List of result dicts
        
        Returns:
            Formatted output with summary and enhanced results
        """
        # Generate summary
        summary = self._generate_summary(query, intent, results)
        
        # Enhance results with context
        enhanced_results = []
        for result in results:
            enhanced = dict(result)
            
            # Add context description
            enhanced["context"] = self._generate_context_description(result)
            
            # Add frontend↔backend links if applicable
            if result.get("api_calls") or result.get("routes"):
                enhanced["has_backend_link"] = True
            if result.get("event_listeners"):
                enhanced["has_frontend_link"] = True
            
            enhanced_results.append(enhanced)
        
        return {
            "query": query,
            "intent": intent,
            "summary": summary,
            "results": enhanced_results,
            "total_matches": len(enhanced_results),
            "has_flow": self._has_complete_flow(enhanced_results)
        }
    
    def _generate_summary(self, query: str, intent: str, results: List[Dict]) -> str:
        """Generate natural language summary of results"""
        if not results:
            return f"No results found for '{query}'"
        
        # Group results by type
        html_elements = [r for r in results if r.get("type") in ["button", "element", "form"]]
        js_functions = [r for r in results if r.get("language") in ["javascript", "typescript"]]
        python_functions = [r for r in results if r.get("language") == "python"]
        routes = [r for r in results if r.get("type") == "route"]
        
        summary_parts = []
        
        if intent == "functionality":
            # Build flow explanation
            if html_elements and js_functions and (routes or python_functions):
                html_name = html_elements[0].get("name", "element")
                js_name = js_functions[0].get("name", "function") if js_functions else None
                route_name = routes[0].get("name", "endpoint") if routes else python_functions[0].get("name", "function") if python_functions else None
                
                summary = f"The {html_name} triggers "
                if js_name:
                    summary += f"{js_name}() which "
                if route_name:
                    summary += f"calls {route_name} handled in the backend"
                else:
                    summary += "processes the request"
                
                summary_parts.append(summary)
            else:
                summary_parts.append(f"Found {len(results)} components related to '{query}'")
        
        elif intent == "location":
            locations = [f"{r.get('file_path', 'N/A')} (line {r.get('start_line', 'N/A')})" for r in results[:3]]
            summary_parts.append(f"Found in: {', '.join(locations)}")
        
        elif intent == "configuration":
            config_items = [r.get("name", "N/A") for r in results[:3]]
            summary_parts.append(f"Configuration items: {', '.join(config_items)}")
        
        else:
            summary_parts.append(f"Found {len(results)} relevant components")
        
        # Add component count summary
        if html_elements:
            summary_parts.append(f"{len(html_elements)} UI element(s)")
        if js_functions:
            summary_parts.append(f"{len(js_functions)} JavaScript function(s)")
        if python_functions:
            summary_parts.append(f"{len(python_functions)} Python function(s)")
        if routes:
            summary_parts.append(f"{len(routes)} API route(s)")
        
        return ". ".join(summary_parts) + "."
    
    def _generate_context_description(self, result: Dict) -> str:
        """Generate context description for a result"""
        result_type = result.get("type", "code")
        name = result.get("name", "")
        file_path = result.get("file_path", "")
        
        context = f"{result_type.capitalize()} '{name}'"
        
        if result.get("api_calls"):
            api_count = len(result.get("api_calls", []))
            context += f" with {api_count} API call(s)"
        
        if result.get("event_listeners"):
            event_count = len(result.get("event_listeners", []))
            context += f" with {event_count} event listener(s)"
        
        if result.get("routes"):
            route_count = len(result.get("routes", []))
            context += f" handling {route_count} route(s)"
        
        return context
    
    def _has_complete_flow(self, results: List[Dict]) -> bool:
        """Check if results contain a complete flow (HTML → JS → Backend)"""
        has_html = any(r.get("type") in ["button", "element"] for r in results)
        has_js = any(r.get("language") in ["javascript", "typescript"] for r in results)
        has_backend = any(r.get("language") == "python" or r.get("type") == "route" for r in results)
        
        return has_html and has_js and has_backend


class HybridSearchPipeline:
    """
    Complete Hybrid Search Pipeline - 4-Layer Architecture
    מאחד את כל השכבות: Query Understanding → Multi-Modal Search → Hybrid Reranking → Output Formatting
    """
    
    def __init__(
        self,
        lexical_engine: LexicalSearchEngine,
        semantic_engine: SemanticSearchEngine,
        ranker: HybridRanker,
        preprocessor: QueryUnderstandingLayer,
        graph_context: GraphContextSearch = None,
        output_formatter: OutputFormatter = None
    ):
        self.lexical_engine = lexical_engine
        self.semantic_engine = semantic_engine
        self.ranker = ranker
        self.preprocessor = preprocessor
        self.graph_context = graph_context
        self.output_formatter = output_formatter or OutputFormatter()
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
        gamma: Optional[float] = None
    ) -> Dict:
        """
        Complete hybrid search pipeline with 4 layers
        
        Returns:
            {
                "query": original query,
                "intent": detected intent,
                "preprocessed": preprocessed query info,
                "summary": natural language summary,
                "results": list of result dicts with context,
                "total_matches": number of results,
                "has_flow": whether complete flow was found
            }
        """
        # Layer 1: Query Understanding
        preprocessed = self.preprocessor.preprocess(query)
        intent = preprocessed["intent"]
        
        # Update ranker weights if provided
        if alpha is not None and beta is not None and gamma is not None:
            self.ranker.alpha = alpha
            self.ranker.beta = beta
            self.ranker.gamma = gamma
        
        # Layer 2: Multi-Modal Search
        # 2a. Lexical search
        lexical_results = self.lexical_engine.search(
            preprocessed["expanded"],
            top_k=top_k * 2  # Get more results for better combination
        )
        
        # 2b. Semantic search
        semantic_results = self.semantic_engine.search(
            preprocessed["normalized"],
            top_k=top_k * 2
        )
        
        # 2c. Graph context expansion
        context_results = []
        if self.graph_context:
            # Expand semantic results with graph context
            context_results = self.graph_context.expand_related(
                semantic_results,
                depth=2
            )
        
        # Layer 3: Hybrid Reranking
        combined_results = self.ranker.combine_results(
            lexical_results,
            semantic_results,
            context_results,
            intent=intent,
            top_k=top_k
        )
        
        # Layer 4: Output Formatting & Explanation
        formatted_output = self.output_formatter.format_results(
            query,
            intent,
            combined_results
        )
        
        return formatted_output
    
    def index(
        self,
        documents: List[str],
        metadata: List[Dict],
        save_path: Optional[Path] = None
    ):
        """
        Index documents in both lexical and semantic engines
        
        Args:
            documents: List of document texts
            metadata: List of metadata dicts
            save_path: Optional path to save indices
        """
        print("📚 Indexing documents...")
        
        # Index in lexical engine
        print("  → Building BM25 index...")
        self.lexical_engine.index(documents, metadata)
        
        # Index in semantic engine
        print("  → Building semantic embeddings...")
        self.semantic_engine.index(documents, metadata)
        
        # Save indices if path provided
        if save_path:
            save_path = Path(save_path)
            save_path.mkdir(parents=True, exist_ok=True)
            
            # Save BM25 index
            self.lexical_engine.save_index(save_path / "bm25_index.pkl")
            
            # Save semantic index
            self.semantic_engine.save_index(
                save_path / "embeddings.npy",
                save_path / "doc_metadata.json"
            )
            
            print(f"✅ Indices saved to {save_path}")
        
        print("✅ Indexing complete")
    
    def load_indices(self, load_path: Path):
        """Load indices from disk"""
        load_path = Path(load_path)
        
        # Load BM25 index
        if (load_path / "bm25_index.pkl").exists():
            self.lexical_engine.load_index(load_path / "bm25_index.pkl")
            print("✅ Loaded BM25 index")
        
        # Load semantic index
        if (load_path / "embeddings.npy").exists() and (load_path / "doc_metadata.json").exists():
            self.semantic_engine.load_index(
                load_path / "embeddings.npy",
                load_path / "doc_metadata.json"
            )
            print("✅ Loaded semantic index")

