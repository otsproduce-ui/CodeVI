"""
Test script for semantic scanning and searching
Demonstrates the complete workflow: scan → index → search
"""
# SSL Bypass
import os, ssl
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

from pathlib import Path
from app.search_service import SearchService

def main():
    # Initialize search service
    base_path = Path(__file__).parent.parent  # Project root
    index_file = str(base_path / "backend" / "index.pkl")
    
    print("=" * 60)
    print("CodeVI Semantic Scanning and Search Test")
    print("=" * 60)
    
    search_service = SearchService(
        root_path=str(base_path),
        index_file=index_file
    )
    
    print(f"\n📁 Base path: {base_path}")
    print(f"📄 Index file: {index_file}")
    
    # Step 1: Scan and index
    print("\n" + "=" * 60)
    print("STEP 1: SCANNING CODEBASE")
    print("=" * 60)
    
    try:
        result = search_service.scan_semantic()
        print(f"\n✅ Scan completed!")
        print(f"   Components indexed: {result.get('count', 0)}")
        print(f"   Index path: {result.get('index_path', 'N/A')}")
    except Exception as e:
        print(f"\n❌ Error during scan: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: Test search
    print("\n" + "=" * 60)
    print("STEP 2: TESTING SEMANTIC SEARCH")
    print("=" * 60)
    
    test_queries = [
        "search button logic",
        "how does login work",
        "API endpoint handler",
        "event listener",
        "form submission"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 60)
        
        try:
            results = search_service.search_semantic(query, max_results=3)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. Score: {result['score']:.3f}")
                    print(f"   Type: {result['type']}")
                    print(f"   Name: {result['name']}")
                    print(f"   File: {result['file_path']}")
                    if result.get('start_line'):
                        print(f"   Lines: {result['start_line']}-{result.get('end_line', '?')}")
                    if result.get('api_calls'):
                        print(f"   API calls: {len(result['api_calls'])}")
                    if result.get('event_listeners'):
                        print(f"   Event listeners: {len(result['event_listeners'])}")
            else:
                print("   No results found")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Step 3: Show statistics
    print("\n" + "=" * 60)
    print("STEP 3: INDEX STATISTICS")
    print("=" * 60)
    
    if search_service.is_semantic_indexed_check():
        index_data = search_service.semantic_index_data
        print(f"\n📊 Total components: {len(index_data)}")
        
        # Count by type
        type_counts = {}
        language_counts = {}
        for item in index_data:
            item_type = item.get('type', 'unknown')
            language = item.get('language', 'unknown')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            language_counts[language] = language_counts.get(language, 0) + 1
        
        print("\n📈 By type:")
        for item_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {item_type}: {count}")
        
        print("\n📈 By language:")
        for language, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {language}: {count}")
    else:
        print("\n⚠️ Semantic index not available")
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

