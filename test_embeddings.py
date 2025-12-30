# SSL Bypass - MUST be before any imports
import os, ssl
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
ssl._create_default_https_context = ssl._create_unverified_context

from sentence_transformers import SentenceTransformer
import os

model_path = r"C:\Users\omert\New folder\backend\models\all-MiniLM-L6-v2"

try:
    # טעינה מהנתיב המקומי בלבד
    model = SentenceTransformer(model_path, local_files_only=True)
    print("✓ Model loaded successfully from local path!")
except Exception as e:
    print(f"✗ Failed to load: {e}")
    raise

# בדיקה קצרה שהוא באמת עובד
sentences = [
    "This is an example sentence",
    "Each sentence is converted into a semantic vector"
]

embeddings = model.encode(sentences)

print("\nModel loaded successfully and embeddings generated!")
print("Embedding size:", embeddings.shape)
print("\nExample embedding for sentence 1:\n", embeddings[0])
