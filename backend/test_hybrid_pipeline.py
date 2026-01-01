"""
Test script for Hybrid Search Pipeline
"""
from pathlib import Path
from app.hybrid_search_pipeline import (
    QueryPreprocessor,
    LexicalSearchEngine,
    SemanticSearchEngine,
    HybridRanker,
    HybridSearchPipeline
)

def main():
    print("=" * 60)
    print("Hybrid Search Pipeline Test")
    print("=" * 60)
    
    # Initialize components
    preprocessor = QueryPreprocessor()
    lexical_engine = LexicalSearchEngine()
    semantic_engine = SemanticSearchEngine()
    ranker = HybridRanker(alpha=0.7, beta=0.3)
    
    # Create pipeline
    pipeline = HybridSearchPipeline(
        lexical_engine=lexical_engine,
        semantic_engine=semantic_engine,
        ranker=ranker,
        preprocessor=preprocessor
    )
    
    # Example documents (in real usage, these come from codebase)
    documents = [
        "def search_handler(query):\n    results = engine.search(query)\n    return jsonify(results)",
        "function handleSearch() {\n    const query = document.getElementById('search-input').value;\n    fetch('/api/search', {method: 'POST', body: JSON.stringify({query})})",
        "<button id='search-btn' onclick='handleSearch()'>Search</button>",
        "@app.route('/api/search', methods=['POST'])\ndef search_api():\n    query = request.json.get('query')\n    return search_handler(query)"
    ]
    
    metadata = [
        {"file_path": "backend/routes.py", "name": "search_handler", "type": "function", "start_line": 10},
        {"file_path": "frontend/app.js", "name": "handleSearch", "type": "function", "start_line": 20},
        {"file_path": "frontend/index.html", "name": "search-btn", "type": "button", "start_line": 35},
        {"file_path": "backend/routes.py", "name": "/api/search", "type": "route", "start_line": 5}
    ]
    
    print("\n📚 Indexing documents...")
    pipeline.index(documents, metadata)
    
    print("\n" + "=" * 60)
    print("Testing Queries")
    print("=" * 60)
    
    queries = [
        "search button",
        "how does search work",
        "API endpoint for search",
        "function that handles search"
    ]
    
    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 60)
        
        results = pipeline.search(query, top_k=3)
        
        print(f"Preprocessed: {results['preprocessed']}")
        print(f"Intent: {results['preprocessed']['intent']}")
        print(f"Results ({results['total_matches']}):")
        
        for i, result in enumerate(results['results'], 1):
            print(f"\n{i}. {result.get('name', 'N/A')}")
            print(f"   File: {result.get('file_path', 'N/A')}")
            print(f"   Type: {result.get('type', 'N/A')}")
            print(f"   Score: {result.get('score', 0):.3f} (Semantic: {result.get('semantic_score', 0):.3f}, Lexical: {result.get('lexical_score', 0):.3f})")
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

