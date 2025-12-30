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
    
    def __init__(self, root_path=None, vector_index_file="vector.index"):
        self.root_path = Path(root_path) if root_path else None
        self.vector_index_file = vector_index_file
        self.embedding_model = None
        self.faiss_index = None
        self.file_map = []
        self.client = None
        
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
    
    def build_vector_index(self, root_path=None):
        """Build FAISS vector index from codebase files"""
        if root_path:
            self.root_path = Path(root_path)
        
        if not self.root_path or not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {self.root_path}")
        
        if not self.embedding_model:
            raise RuntimeError("Embedding model not loaded")
        
        docs = []
        self.file_map = []
        
        # Scan Python and JavaScript/TypeScript files
        for ext in ["*.py", "*.js", "*.ts", "*.tsx", "*.jsx"]:
            for file_path in self.root_path.rglob(ext):
                try:
                    content = file_path.read_text(errors="ignore")
                    if content.strip():  # Only add non-empty files
                        docs.append(content)
                        self.file_map.append(str(file_path.relative_to(self.root_path)))
                except Exception as e:
                    print(f"Skipping {file_path}: {e}")
        
        if not docs:
            print("No files found to index")
            return
        
        print(f"Encoding {len(docs)} files...")
        embeddings = self.embedding_model.encode(docs, convert_to_numpy=True, show_progress_bar=True)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatL2(dimension)
        self.faiss_index.add(embeddings.astype('float32'))
        
        # Save index
        faiss.write_index(self.faiss_index, self.vector_index_file)
        # Save file map
        self.save_file_map()
        print(f"✅ Built vector index for {len(docs)} files. Index saved to {self.vector_index_file}")
    
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
                    self.file_map = pickle.load(f)
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
    
    def semantic_search(self, query, top_k=5):
        """Perform semantic search and return file paths"""
        if not self.faiss_index:
            if not self.load_index():
                raise RuntimeError("No vector index available. Build index first.")
        
        if not self.embedding_model:
            raise RuntimeError("Embedding model not loaded")
        
        # Encode query
        query_emb = self.embedding_model.encode([query], convert_to_numpy=True)
        
        # Search
        k = min(top_k, len(self.file_map))
        distances, indices = self.faiss_index.search(query_emb.astype('float32'), k)
        
        # Return file paths with scores
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.file_map):
                results.append({
                    "file_path": self.file_map[idx],
                    "score": float(distances[0][i])  # Lower is better (L2 distance)
                })
        
        return results
    
    def explain_results(self, query, file_snippets):
        """Use OpenAI to explain the relationship between query and results"""
        if not self.client:
            return "OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
        
        if not file_snippets:
            return "No code snippets provided for explanation."
        
        context = "\n\n---\n\n".join(file_snippets)
        prompt = f"""Question: {query}

Code Context:
{context}

Explain the relevant logic and reasoning behind where and how this happens in the code.
Be concise and specific. Focus on the connection between the question and the code snippets."""
        
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
            return f"Error generating explanation: {str(e)}"
    
    def is_indexed(self):
        """Check if vector index exists"""
        return self.faiss_index is not None or Path(self.vector_index_file).exists()
    
    def file_count(self):
        """Get number of indexed files"""
        return len(self.file_map) if self.file_map else 0

