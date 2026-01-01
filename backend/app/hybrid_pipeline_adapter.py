"""
Hybrid Pipeline Adapter - Integrates HybridSearchPipeline with existing SearchService
מחבר את ה-Pipeline החדש ל-SearchService הקיים
"""
from pathlib import Path
from typing import List, Dict, Optional
from app.hybrid_search_pipeline import (
    QueryUnderstandingLayer,
    LexicalSearchEngine,
    SemanticSearchEngine,
    HybridRanker,
    HybridSearchPipeline,
    GraphContextSearch,
    OutputFormatter
)


class HybridPipelineAdapter:
    """
    Adapter that integrates HybridSearchPipeline with SearchService
    מאפשר שימוש ב-Pipeline החדש דרך SearchService הקיים
    """
    
    def __init__(self, search_service):
        """
        Initialize adapter with existing SearchService
        
        Args:
            search_service: Existing SearchService instance
        """
        self.search_service = search_service
        self.pipeline = None
        self._initialized = False
    
    def initialize(self, model_path: Optional[Path] = None, graph_service=None, explanation_service=None):
        """
        Initialize the hybrid pipeline with data from SearchService
        
        Args:
            model_path: Optional path to local embedding model
            graph_service: Optional GraphService for context search
            explanation_service: Optional ExplanationService for summaries
        """
        if self._initialized:
            return
        
        # Initialize components
        query_understanding = QueryUnderstandingLayer()
        lexical_engine = LexicalSearchEngine()
        semantic_engine = SemanticSearchEngine(model_path=model_path)
        ranker = HybridRanker(alpha=0.6, beta=0.3, gamma=0.1)
        
        # Graph context search (if available)
        graph_context = None
        if graph_service:
            graph_context = GraphContextSearch(graph_service)
        
        # Output formatter
        output_formatter = OutputFormatter(explanation_service=explanation_service)
        
        # Create pipeline
        self.pipeline = HybridSearchPipeline(
            lexical_engine=lexical_engine,
            semantic_engine=semantic_engine,
            ranker=ranker,
            preprocessor=query_understanding,
            graph_context=graph_context,
            output_formatter=output_formatter
        )
        
        # Load data from SearchService if indexed
        if hasattr(self.search_service, 'semantic_index_data') and self.search_service.semantic_index_data:
            self._load_from_search_service()
        
        self._initialized = True
    
    def _load_from_search_service(self):
        """Load indexed data from SearchService into pipeline"""
        if not hasattr(self.search_service, 'semantic_index_data'):
            return
        
        index_data = self.search_service.semantic_index_data
        
        # Extract documents and metadata
        documents = []
        metadata = []
        
        for item in index_data:
            # Build text for embedding (same format as used in indexing)
            text = f"{item.get('type', 'code')}: {item.get('name', '')}\n"
            if item.get('docstring'):
                text += f"Description: {item['docstring']}\n"
            elif item.get('context'):
                text += f"{item['context']}\n"
            
            # Add API calls, events, routes
            api_calls = item.get('api_calls', [])
            if api_calls:
                api_info = ", ".join([f"{ac.get('method', 'GET')} {ac.get('endpoint', '')}" 
                                     for ac in api_calls[:3]])
                text += f"API calls: {api_info}\n"
            
            event_listeners = item.get('event_listeners', [])
            if event_listeners:
                event_info = ", ".join([f"{el.get('event', '')} -> {el.get('handler', '')}" 
                                       for el in event_listeners[:3]])
                text += f"Events: {event_info}\n"
            
            routes = item.get('routes', [])
            if routes:
                route_info = ", ".join([f"{r.get('method', 'GET')} {r.get('path', '')}" 
                                       for r in routes[:3]])
                text += f"Routes: {route_info}\n"
            
            text += f"\nCode:\n{item.get('code', '')[:500]}"
            
            documents.append(text)
            metadata.append({
                "file_path": item.get("file_path", ""),
                "name": item.get("name", item.get("full_name", "")),
                "type": item.get("type", "code"),
                "language": item.get("language", ""),
                "start_line": item.get("start_line", 1),
                "end_line": item.get("end_line", 1),
                "code": item.get("code", ""),
                "docstring": item.get("docstring", ""),
                "api_calls": item.get("api_calls", []),
                "event_listeners": item.get("event_listeners", []),
                "routes": item.get("routes", [])
            })
        
        # Index in pipeline
        if documents:
            print(f"📚 Loading {len(documents)} documents into hybrid pipeline...")
            self.pipeline.index(documents, metadata)
            print("✅ Pipeline initialized with SearchService data")
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = None,
        beta: float = None,
        gamma: float = None
    ) -> Dict:
        """
        Search using hybrid pipeline with 4-layer architecture
        
        Args:
            query: Search query
            top_k: Number of results
            alpha: Semantic weight (optional)
            beta: Lexical weight (optional)
            gamma: Context weight (optional)
        
        Returns:
            Search results with metadata, summary, and intent
        """
        if not self._initialized:
            # Get graph_service and explanation_service from search_service if available
            graph_service = getattr(self.search_service, 'graph_service', None) if hasattr(self.search_service, 'graph_service') else None
            explanation_service = getattr(self.search_service, 'explanation_service', None) if hasattr(self.search_service, 'explanation_service') else None
            self.initialize(graph_service=graph_service, explanation_service=explanation_service)
        
        if not self.pipeline:
            # Fallback to SearchService
            return self.search_service.search(query, max_results=top_k)
        
        # Use pipeline
        results = self.pipeline.search(query, top_k=top_k, alpha=alpha, beta=beta, gamma=gamma)
        
        # Convert to SearchService format (preserve new fields)
        formatted_results = []
        for result in results.get('results', []):
            formatted_results.append({
                "file_path": result.get("file_path", ""),
                "name": result.get("name", ""),
                "full_name": result.get("name", ""),
                "type": result.get("type", "code"),
                "language": result.get("language", ""),
                "start_line": result.get("start_line", 1),
                "end_line": result.get("end_line", 1),
                "code": result.get("code", ""),
                "content": result.get("code", ""),  # For backward compatibility
                "score": result.get("score", 0),
                "semantic_score": result.get("semantic_score", 0),
                "lexical_score": result.get("lexical_score", 0),
                "context_score": result.get("context_score", 0),  # New field
                "context": result.get("context", result.get("docstring", "")),  # Enhanced context
                "api_calls": result.get("api_calls", []),
                "event_listeners": result.get("event_listeners", []),
                "routes": result.get("routes", []),
                "has_backend_link": result.get("has_backend_link", False),  # New field
                "has_frontend_link": result.get("has_frontend_link", False)  # New field
            })
        
        return {
            "query": query,
            "intent": results.get("intent", "general"),  # New field
            "summary": results.get("summary", ""),  # New field
            "results": formatted_results,
            "total_matches": results.get("total_matches", len(formatted_results)),
            "preprocessed": results.get("preprocessed", {}),
            "has_flow": results.get("has_flow", False),  # New field
            "search_type": "hybrid_pipeline_4layer"
        }
