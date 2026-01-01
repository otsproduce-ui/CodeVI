"""
Test script for hybrid search functionality
Demonstrates BM25 + Semantic search combination
"""
# SSL Bypass
import os, ssl
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

from pathlib import Path
from app.search_service import SearchService

def main():
    print("=" * 60)
    print("CodeVI Hybrid Search Test")
    print("=" * 60)
    
    base_path = Path(__file__).parent.parent
    index_file = str(base_path / "backend" / "index.pkl")
    
    search_service = SearchService(
        root_path=str(base_path),
        index_file=index_file
    )
    
    # Load existing index if available
    print("\n📦 Loading existing index...")
    search_service.load_semantic_index()
    
    if not search_service.is_semantic_indexed_check():
        print("\n⚠️ No semantic index found. Run scan_semantic() first.")
        print("   You can run: python test_scan_and_search.py")
        return
    
    # Test queries
    test_queries = [
        "show me where the search button logic is handled",
        "how does login work",
        "API endpoint handler",
        "event listener for click",
        "form submission"
    ]
    
    print("\n" + "=" * 60)
    print("Testing Hybrid Search (60% Semantic + 40% BM25)")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 60)
        
        # Hybrid search
        results = search_service.hybrid_search(
            query, 
            max_results=5,
            semantic_weight=0.6,
            lexical_weight=0.4
        )
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Combined Score: {result['score']:.3f}")
                print(f"   Semantic: {result.get('semantic_score', 'N/A'):.3f} | BM25: {result.get('bm25_score', 'N/A'):.3f}")
                print(f"   Type: {result['type']}")
                print(f"   Name: {result['name']}")
                print(f"   File: {result['file_path']}")
                if result.get('start_line'):
                    print(f"   Lines: {result['start_line']}-{result.get('end_line', '?')}")
        else:
            print("   No results found")
    
    # Compare with semantic-only search
    print("\n" + "=" * 60)
    print("Comparison: Hybrid vs Semantic-only")
    print("=" * 60)
    
    test_query = "search button logic"
    
    print(f"\nQuery: '{test_query}'")
    print("\n1. Hybrid Search (60% semantic + 40% BM25):")
    hybrid_results = search_service.hybrid_search(test_query, max_results=3, semantic_weight=0.6, lexical_weight=0.4)
    for i, r in enumerate(hybrid_results, 1):
        print(f"   {i}. {r['name']} (score: {r['score']:.3f})")
    
    print("\n2. Semantic-only Search:")
    semantic_results = search_service.search_semantic(test_query, max_results=3)
    for i, r in enumerate(semantic_results, 1):
        print(f"   {i}. {r['name']} (score: {r['score']:.3f})")
    
    print("\n" + "=" * 60)
    print("✅ Hybrid search test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

