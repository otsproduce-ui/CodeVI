"""
Search Service - Manages indexing, persistence and searching
"""
from pathlib import Path
import pickle
import sys
import os

# Add parent directory to path for search_engine import
backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

# Import search_engine from parent directory
from search_engine import SearchEngine


class SearchService:
    """Service managing indexing, persistence and searching."""

    def __init__(self, root_path: str, index_file: str):
        self.root_path = Path(root_path)
        self.index_file = index_file
        self.engine = None

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

    def index_codebase(self):
        """Index a new codebase"""
        self.engine = SearchEngine(self.root_path)
        self.engine.index_codebase()
        self.save_index()

    def save_index(self):
        """Save BM25 index to disk"""
        if self.engine:
            try:
                with open(self.index_file, "wb") as f:
                    pickle.dump(self.engine, f)
                print(f"[OK] Index saved to {self.index_file}")
            except Exception as e:
                print(f"[WARN] Error saving index: {e}")

    def search(self, query, max_results=10):
        """Perform a search on indexed codebase"""
        if not self.engine:
            raise RuntimeError("Engine not initialized. Please scan first.")
        return self.engine.search(query, max_results)

    def get_graph(self):
        """Return relationship graph"""
        if not self.engine:
            raise RuntimeError("Engine not initialized. Please scan first.")
        return self.engine.extract_graph()

    def file_count(self):
        """Return number of indexed files"""
        return self.engine.get_file_count() if self.engine else 0

    def is_indexed(self):
        """Check if codebase is indexed"""
        return self.engine and self.engine.is_indexed()

