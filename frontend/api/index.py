# frontend/api/index.py — Vercel Serverless Python Entrypoint
# Hosts the FastAPI backend directly on Vercel
import sys
import os

# Add project root directory to Python path
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.abspath(os.path.join(_HERE, "..", ".."))

for p in [_ROOT_DIR, "/var/task", _HERE]:
    if p and os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

# Import the main FastAPI app from the root api.index module
try:
    from api.index import app
except Exception as e:
    print(f"Error loading api.index: {e}")
    # Fallback: create minimal app
    from fastapi import FastAPI
    app = FastAPI()
    @app.get("/")
    @app.get("/api/health")
    def fallback_health():
        return {"status": "healthy", "mode": "fallback"}

# Export for Vercel Serverless Function
handler = app
