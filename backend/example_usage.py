"""
Example usage of CodeVI semantic parsing and indexing
Demonstrates the complete workflow as described in the requirements
"""
# SSL Bypass
import os, ssl
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

from pathlib import Path
from sentence_transformers import SentenceTransformer
from app.code_parser import CodeParser
from app.semantic_service import SemanticSearchService

# Step 1: Load local model (already exists)
print("Step 1: Loading local model...")
model_path = Path(__file__).parent / "models" / "all-MiniLM-L6-v2"
if model_path.exists():
    model = SentenceTransformer(str(model_path))
    print(f"✓ Model loaded from: {model_path}")
else:
    print("⚠ Model not found, using default...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

# Step 2: Parse repository to extract code units
print("\nStep 2: Parsing repository...")
parser = CodeParser()
repo_path = Path(__file__).parent.parent  # Project root

code_units = []
for ext in ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.html"]:
    for file_path in repo_path.rglob(ext):
        # Skip venv and other ignored dirs
        if any(ignore in str(file_path) for ignore in ['venv', '__pycache__', '.git', 'node_modules']):
            continue
        
        try:
            units = parser.parse_file(file_path)
            code_units.extend(units)
        except Exception as e:
            print(f"  ⚠ Error parsing {file_path}: {e}")

print(f"✓ Extracted {len(code_units)} code units")

# Step 3: Generate embeddings for each unit
print("\nStep 3: Generating embeddings...")
embeddings_list = []
for i, unit in enumerate(code_units[:10], 1):  # First 10 for demo
    # Build text for embedding (same format as semantic_service)
    text = f"{unit.get('type', 'code')}: {unit.get('name', '')}\n"
    if unit.get('docstring'):
        text += f"{unit['docstring']}\n"
    text += unit.get('context', unit.get('code', ''))
    
    vector = model.encode(text)
    embeddings_list.append({
        'unit': unit,
        'vector': vector,
        'text': text[:100]  # Preview
    })
    
    if i % 5 == 0:
        print(f"  Encoded {i}/{min(10, len(code_units))} units...")

print(f"✓ Generated {len(embeddings_list)} embeddings")

# Step 4: Example search query
print("\nStep 4: Example semantic search...")
query = "how does search work?"
query_vector = model.encode([query])

# Simple similarity search (in real usage, use FAISS)
import numpy as np
similarities = []
for emb_data in embeddings_list:
    similarity = np.dot(query_vector[0], emb_data['vector']) / (
        np.linalg.norm(query_vector[0]) * np.linalg.norm(emb_data['vector'])
    )
    similarities.append((similarity, emb_data))

# Sort by similarity
similarities.sort(reverse=True, key=lambda x: x[0])

print(f"\nTop 3 results for: '{query}'")
for i, (score, emb_data) in enumerate(similarities[:3], 1):
    unit = emb_data['unit']
    print(f"\n{i}. Score: {score:.3f}")
    print(f"   Type: {unit.get('type')}")
    print(f"   Name: {unit.get('name')}")
    print(f"   File: {unit.get('file_path')}")
    print(f"   Lines: {unit.get('start_line')}-{unit.get('end_line')}")

# Step 5: Show example code unit format
print("\n" + "=" * 60)
print("Example Code Unit Format:")
print("=" * 60)
if code_units:
    example = code_units[0]
    print(f"""
Type: {example.get('type')}
Language: {example.get('language')}
Name: {example.get('name')}
Full name: {example.get('full_name')}
File: {example.get('file_path')}
Lines: {example.get('start_line')}-{example.get('end_line')}
Context: {example.get('context', '')[:100]}...
API calls: {len(example.get('api_calls', []))}
Event listeners: {len(example.get('event_listeners', []))}
Routes: {len(example.get('routes', []))}
""")

print("\n✓ Example usage completed!")
print("\nTo use in production, use SemanticSearchService which handles:")
print("  - FAISS indexing for fast similarity search")
print("  - Hybrid search (BM25 + Semantic)")
print("  - Flow explanations")

