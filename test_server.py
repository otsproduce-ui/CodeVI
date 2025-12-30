"""
Quick test script to verify Flask server is working
"""
import requests
import time
import sys

def test_server():
    print("Waiting for server to start...")
    time.sleep(2)
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Server is running!")
            print(f"Status: {response.status_code}")
            print(f"Response: {data}")
            return True
        else:
            print(f"✗ Server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Server is not running.")
        print("  Start it with: python run_all.py")
        print("  Or manually: cd backend && python main.py")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)

