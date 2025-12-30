# SSL Bypass - MUST be before any imports
import os, ssl
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['HF_HUB_DISABLE_SSL'] = '1'
ssl._create_default_https_context = ssl._create_unverified_context

# Disable SSL verification for requests and urllib3
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from sentence_transformers import SentenceTransformer

# הגדרת הנתיב המדויק שלך
model_path = r"C:\Users\omert\New folder\backend\models\all-MiniLM-L6-v2"

print("Downloading and fixing model structure...")
# הורדה מהענן (זמנית) כדי להבטיח שלמות
model = SentenceTransformer('all-MiniLM-L6-v2')

# שמירה מחדש לתוך התיקייה הקיימת - זה ידרוס קבצים פגומים ויוסיף חסרים
model.save(model_path)

print(f"✓ Model structure fixed in: {model_path}")

