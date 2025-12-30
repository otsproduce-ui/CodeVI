from sentence_transformers import SentenceTransformer

# נשתמש במודל הרשמי מה-Hugging Face
print("🚀 Loading model... this may take a minute the first time")

model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

sentences = [
    "This is an example sentence",
    "Each sentence is converted into a semantic vector"
]

embeddings = model.encode(sentences)

print("✅ Model loaded successfully!")
print("Embedding size:", embeddings.shape)
print("Example embedding for sentence 1:\n", embeddings[0])
