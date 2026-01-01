"""
Test script for contextual search and relationship graph
"""
import os
from pathlib import Path
from app.search_service import SearchService
from app.graph_service import GraphService

def main():
    base_path = Path(__file__).parent.parent  # C:\Users\omert\New folder
    index_file = str(base_path / "backend" / "index.pkl")

    print("=" * 60)
    print("CodeVI Contextual Search & Graph Test")
    print("=" * 60)
    
    # Initialize services
    search_service = SearchService(
        root_path=str(base_path),
        index_file=index_file
    )
    
    graph_service = GraphService(search_service)
    
    print(f"\n📁 Base path: {search_service.root_path}")
    print(f"📄 Index file: {search_service.semantic_index_file}")
    
    # Check if indexed
    if not search_service.is_semantic_indexed_check():
        print("\n⚠️ Semantic index not found. Running scan first...")
        result = search_service.scan_semantic()
        print(f"✅ Scanned {result['count']} components")
    else:
        print(f"\n✅ Semantic index loaded with {len(search_service.semantic_index_data)} components")
    
    print("\n" + "=" * 60)
    print("TEST 1: Adaptive Hybrid Search")
    print("=" * 60)
    
    queries = [
        "search",  # Short query (should favor BM25)
        "how does login work",  # Medium query (balanced)
        "where is user authentication handled in the backend",  # Long query (should favor semantic)
    ]
    
    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        print("-" * 60)
        results = search_service.hybrid_search(query, max_results=3, adaptive=True)
        if results:
            for i, r in enumerate(results, 1):
                print(f"{i}. {r.get('name', 'N/A')} (Score: {r.get('score', 0):.3f})")
                print(f"   Type: {r.get('type', 'N/A')}, File: {r.get('file_path', 'N/A')}")
        else:
            print("   No results found")
    
    print("\n" + "=" * 60)
    print("TEST 2: Contextual Search (with relationships)")
    print("=" * 60)
    
    contextual_query = "search button logic"
    print(f"\n🔍 Contextual Query: '{contextual_query}'")
    print("-" * 60)
    
    contextual_results = graph_service.contextual_search(contextual_query, depth=2)
    
    # Assertions for contextual search
    assert len(contextual_results) > 0, "Contextual search should return at least one result"
    
    has_related = False
    has_frontend_backend_link = False
    has_route_connection = False
    has_search_button = False
    has_api_search = False
    
    for i, ctx_result in enumerate(contextual_results, 1):
        base = ctx_result.get("base", {})
        base_name = base.get('name', '').lower()
        print(f"\n{i}. Base Result: {base.get('name', 'N/A')}")
        print(f"   File: {base.get('file_path', 'N/A')}")
        print(f"   Type: {base.get('type', 'N/A')}")
        print(f"   Context: {graph_service._detect_context(base)}")
        
        # Check for search button
        if "search" in base_name and base.get('type') in ['button', 'element']:
            has_search_button = True
        
        related = ctx_result.get("related", [])
        if related:
            has_related = True
            print(f"   📎 Related Components ({len(related)}):")
            for j, rel in enumerate(related[:5], 1):  # Show top 5
                rel_type = rel.get('relation_type', 'related')
                rel_direction = rel.get('direction', '')
                rel_context = rel.get('context', graph_service._detect_context(rel))
                endpoint_match = rel.get('endpoint_match', '')
                
                print(f"      {j}. {rel.get('name', 'N/A')} ({rel_type})")
                print(f"         File: {rel.get('file_path', 'N/A')}")
                print(f"         Direction: {rel_direction}, Context: {rel_context}, Strength: {rel.get('relation_strength', 'N/A')}")
                if endpoint_match:
                    print(f"         Endpoint: {endpoint_match}")
                
                # Check for frontend↔backend connections
                if rel_type in ["handles_endpoint", "calls_route", "calls_endpoint"]:
                    has_frontend_backend_link = True
                if rel_type in ["handles_route", "endpoint_handler"]:
                    has_route_connection = True
                if "api/search" in endpoint_match.lower() or "api/search" in rel.get('name', '').lower():
                    has_api_search = True
        else:
            print("   📎 No related components found")
    
    # Assertions
    print(f"\n✅ Assertions:")
    print(f"   - Has related components: {has_related}")
    print(f"   - Has frontend↔backend links: {has_frontend_backend_link}")
    print(f"   - Has route connections: {has_route_connection}")
    print(f"   - Found search button: {has_search_button}")
    print(f"   - Found /api/search endpoint: {has_api_search}")
    
    # Detailed assertions
    assert has_related, "Contextual search should find related components"
    
    # Test specific flow: search button → handler → API → backend
    if has_search_button:
        print(f"\n   ✅ Found search button in results")
        if has_api_search:
            print(f"   ✅ Found /api/search endpoint connection")
        if has_frontend_backend_link:
            print(f"   ✅ Found frontend↔backend link")
    
    if not has_related:
        print("   ⚠️ Warning: No related components found - may indicate indexing issue")
    
    print("\n" + "=" * 60)
    print("TEST 3: Flow Graph")
    print("=" * 60)
    
    flow_query = "login authentication"
    print(f"\n🔍 Flow Graph Query: '{flow_query}'")
    print("-" * 60)
    
    flow_data = graph_service.build_flow_graph(flow_query)
    
    # Assertions for flow graph
    assert "nodes" in flow_data, "Flow graph should have nodes"
    assert "edges" in flow_data, "Flow graph should have edges"
    assert len(flow_data.get('nodes', [])) > 0, "Flow graph should have at least one node"
    
    stats = flow_data.get('stats', {})
    print(f"\n📊 Flow Graph:")
    print(f"   Nodes: {len(flow_data.get('nodes', []))}")
    print(f"   Edges: {len(flow_data.get('edges', []))}")
    print(f"   Frontend nodes: {stats.get('frontend_nodes', 0)}")
    print(f"   Backend nodes: {stats.get('backend_nodes', 0)}")
    print(f"   Frontend↔Backend connections: {stats.get('frontend_backend_connections', 0)}")
    
    if flow_data.get('nodes'):
        print("\n   Sample Nodes:")
        for node in flow_data['nodes'][:5]:  # Show top 5
            print(f"      - {node.get('label', 'N/A')} ({node.get('type', 'N/A')}) [{node.get('language', 'N/A')}]")
    
    if flow_data.get('edges'):
        print("\n   Sample Edges:")
        for edge in flow_data['edges'][:5]:  # Show top 5
            edge_type = edge.get('type', 'related')
            direction = edge.get('direction', '')
            endpoint = edge.get('endpoint', '')
            endpoint_str = f" ({endpoint})" if endpoint else ""
            print(f"      - {edge.get('source', 'N/A')[:50]} → {edge.get('target', 'N/A')[:50]}")
            print(f"        Type: {edge_type}, Direction: {direction}{endpoint_str}")
    
    # Check for flow chains
    flow_chains = flow_data.get('flow_chains', [])
    if flow_chains:
        print(f"\n   Flow Chains: {len(flow_chains)}")
        for i, chain in enumerate(flow_chains[:3], 1):
            print(f"      Chain {i}: {' → '.join([n[:30] for n in chain])}")
    
    # Assertions
    print(f"\n✅ Assertions:")
    has_nodes = len(flow_data.get('nodes', [])) > 0
    has_edges = len(flow_data.get('edges', [])) > 0
    has_fb_connections = stats.get('frontend_backend_connections', 0) > 0
    has_flow_chains = len(flow_data.get('flow_chains', [])) > 0
    
    print(f"   - Has nodes: {has_nodes}")
    print(f"   - Has edges: {has_edges}")
    print(f"   - Has frontend↔backend connections: {has_fb_connections}")
    print(f"   - Has flow chains: {has_flow_chains}")
    
    # Detailed assertions
    assert has_nodes, "Flow graph should have at least one node"
    assert has_edges, "Flow graph should have at least one edge"
    
    # Check for specific flow chain patterns
    flow_chains = flow_data.get('flow_chains', [])
    has_html_to_js = False
    has_js_to_api = False
    has_api_to_backend = False
    
    for chain in flow_chains:
        chain_str = " → ".join(chain).lower()
        if "html" in chain_str or "button" in chain_str:
            has_html_to_js = True
        if "js" in chain_str or "javascript" in chain_str:
            if "api" in chain_str or "fetch" in chain_str:
                has_js_to_api = True
        if "api" in chain_str and ("python" in chain_str or "route" in chain_str):
            has_api_to_backend = True
    
    print(f"\n   Flow Chain Analysis:")
    print(f"   - HTML → JS: {has_html_to_js}")
    print(f"   - JS → API: {has_js_to_api}")
    print(f"   - API → Backend: {has_api_to_backend}")
    
    if not has_fb_connections:
        print("   ⚠️ Warning: No frontend↔backend connections found - may indicate missing API calls or routes")
    
    # Test specific flow: search button → handler → API → backend
    if has_search_button and has_api_search:
        print(f"\n   ✅ Found complete flow: search button → API → backend")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()

