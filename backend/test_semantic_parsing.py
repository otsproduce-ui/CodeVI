"""
Test script demonstrating the full semantic parsing pipeline
Shows how code_parser + semantic_service work together with local model
"""
# SSL Bypass
import os, ssl
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

from pathlib import Path
from app.code_parser import CodeParser
from app.semantic_service import SemanticSearchService

def test_code_parsing():
    """Test code parsing with tree-sitter"""
    print("=" * 60)
    print("Testing Code Parser")
    print("=" * 60)
    
    parser = CodeParser()
    
    # Test with a sample file (use your actual project path)
    test_file = Path(__file__).parent / "app" / "semantic_service.py"
    
    if test_file.exists():
        print(f"\nParsing: {test_file}")
        structures = parser.parse_file(test_file)
        
        print(f"\nFound {len(structures)} code units:")
        for i, struct in enumerate(structures[:3], 1):  # Show first 3
            print(f"\n{i}. Type: {struct.get('type', 'unknown')}")
            print(f"   Name: {struct.get('name', 'unknown')}")
            print(f"   Full name: {struct.get('full_name', 'unknown')}")
            print(f"   Lines: {struct.get('start_line', '?')}-{struct.get('end_line', '?')}")
            
            if struct.get('api_calls'):
                print(f"   API calls: {len(struct['api_calls'])}")
            if struct.get('event_listeners'):
                print(f"   Event listeners: {len(struct['event_listeners'])}")
            if struct.get('routes'):
                print(f"   Routes: {len(struct['routes'])}")
    else:
        print(f"Test file not found: {test_file}")
    
    return structures if 'structures' in locals() else []


def test_semantic_indexing():
    """Test semantic indexing with local model"""
    print("\n" + "=" * 60)
    print("Testing Semantic Indexing with Local Model")
    print("=" * 60)
    
    # Initialize semantic service (will load local model)
    semantic_service = SemanticSearchService(
        root_path=Path(__file__).parent.parent,  # Project root
        vector_index_file="test_vector.index"
    )
    
    if not semantic_service.embedding_model:
        print("ERROR: Embedding model not loaded!")
        return
    
    print(f"\n✓ Model loaded: {type(semantic_service.embedding_model).__name__}")
    
    # Test encoding a single code unit
    test_text = """function: handleLogin
Description: Handles user login authentication
API calls: POST /api/login
Events: click -> handleLogin

Code:
async function handleLogin() {
    const response = await fetch('/api/login', {
        method: 'POST',
        body: JSON.stringify({username, password})
    });
    return response.json();
}"""
    
    print("\nTesting encoding...")
    embedding = semantic_service.embedding_model.encode([test_text])
    print(f"✓ Encoded to vector of shape: {embedding.shape}")
    print(f"  Vector dimension: {embedding.shape[1]}")
    
    return semantic_service


def test_full_pipeline():
    """Test the complete pipeline: parse → encode → index"""
    print("\n" + "=" * 60)
    print("Testing Full Pipeline")
    print("=" * 60)
    
    # Step 1: Parse code
    parser = CodeParser()
    test_file = Path(__file__).parent / "app" / "code_parser.py"
    
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return
    
    print(f"\n1. Parsing: {test_file.name}")
    structures = parser.parse_file(test_file)
    print(f"   Found {len(structures)} code units")
    
    # Step 2: Initialize semantic service
    print("\n2. Initializing semantic service...")
    semantic_service = SemanticSearchService(
        root_path=Path(__file__).parent.parent,
        vector_index_file="test_vector.index"
    )
    
    if not semantic_service.embedding_model:
        print("   ERROR: Model not loaded!")
        return
    
    print(f"   ✓ Model loaded")
    
    # Step 3: Encode each unit
    print("\n3. Encoding code units...")
    texts = []
    for struct in structures[:5]:  # First 5 units
        # Build text for embedding (same format as in semantic_service)
        entry_text = f"{struct.get('type', 'code')}: {struct.get('name', '')}\n"
        if struct.get('docstring'):
            entry_text += f"Description: {struct['docstring']}\n"
        
        api_calls = struct.get('api_calls', [])
        if api_calls:
            api_info = ", ".join([f"{ac.get('method', 'GET')} {ac.get('endpoint', '')}" 
                                 for ac in api_calls[:3]])
            entry_text += f"API calls: {api_info}\n"
        
        entry_text += f"\nCode:\n{struct.get('code', '')[:200]}"
        texts.append(entry_text)
    
    embeddings = semantic_service.embedding_model.encode(texts, show_progress_bar=True)
    print(f"   ✓ Encoded {len(texts)} units to vectors of shape {embeddings.shape}")
    
    print("\n✓ Full pipeline test completed successfully!")
    print("\nExample code unit format:")
    if structures:
        example = structures[0]
        print(f"  Type: {example.get('type')}")
        print(f"  Name: {example.get('name')}")
        print(f"  Path: {example.get('file_path')}")
        print(f"  Lines: {example.get('start_line')}-{example.get('end_line')}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CodeVI Semantic Parsing Test")
    print("=" * 60)
    
    try:
        # Test 1: Code parsing
        structures = test_code_parsing()
        
        # Test 2: Semantic indexing
        semantic_service = test_semantic_indexing()
        
        # Test 3: Full pipeline
        test_full_pipeline()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

