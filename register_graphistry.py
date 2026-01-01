"""
Register Graphistry with API credentials
"""
import graphistry
import sys
import io

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print(f"Graphistry version: {graphistry.__version__}")

# Register with provided credentials
try:
    graphistry.register(
        api=3,
        protocol="https",
        server="hub.graphistry.com",
        personal_key_id="CSZZVP7E42",
        personal_key_secret="DB31ZN0424GOESPP"
    )
    print("\n[OK] Graphistry registered successfully!")
    print("You can now use Graphistry to visualize graphs.")
except Exception as e:
    print(f"\n[ERROR] Error registering Graphistry: {e}")
    print("Please check your credentials and internet connection.")

