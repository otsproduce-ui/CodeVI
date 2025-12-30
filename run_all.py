"""
CodeVI - Run both backend and frontend servers
Starts FastAPI backend on port 8000 and HTTP server for frontend on port 8080
"""
import subprocess
import sys
import time
import os
from pathlib import Path

def start_backend():
    """Start Flask backend server with new structure (serves both API and frontend)"""
    backend_dir = Path(__file__).parent / "backend"
    print("🚀 Starting Flask server on http://localhost:8000...")
    print("   (Serving both API and frontend)")
    # Set PORT environment variable to 8000
    env = os.environ.copy()
    env["PORT"] = "8000"
    return subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )

def main():
    print("=" * 60)
    print("CodeVI - Starting Development Servers")
    print("=" * 60)
    print()
    
    # Kill any existing processes on port 8000
    try:
        import subprocess as sp
        result = sp.run(["netstat", "-ano"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if ":8000" in line and "LISTENING" in line:
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    try:
                        sp.run(["taskkill", "/PID", pid, "/F"], capture_output=True)
                        print(f"⚠️  Killed existing process on port 8000 (PID: {pid})")
                    except:
                        pass
    except:
        pass
    
    # Start backend (serves both API and frontend)
    backend_process = start_backend()
    time.sleep(3)  # Give backend time to start
    
    print()
    print("=" * 60)
    print("✅ Both servers are running!")
    print("=" * 60)
    print()
    print("📍 Application:  http://localhost:8000")
    print("📍 API:          http://localhost:8000/api/v1")
    print("📍 Health Check: http://localhost:8000/health")
    print()
    print("Press CTRL+C to stop both servers")
    print("=" * 60)
    print()
    
    try:
        # Monitor process
        while True:
            # Check if process is still alive
            if backend_process.poll() is not None:
                print("❌ Server process died!")
                print(backend_process.stderr.read())
                break
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down server...")
        backend_process.terminate()
        
        # Wait for process to terminate
        try:
            backend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("⚠️  Force killing process...")
            backend_process.kill()
        
        print("✅ Server stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()

