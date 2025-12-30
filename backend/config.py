"""
CodeVI Backend Configuration
"""
import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INDEX_PATH = os.path.join(BASE_DIR, "index.pkl")
    VECTOR_INDEX_PATH = os.path.join(BASE_DIR, "vector.index")
    ALLOWED_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")

