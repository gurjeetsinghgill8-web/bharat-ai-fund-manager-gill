# frontend/api/index.py — Vercel Serverless Python Entrypoint
# Hosts the FastAPI backend directly on Vercel for 100% FREE!
import sys
import os

# Add project root directory to Python path
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.abspath(os.path.join(_HERE, "..", ".."))

for p in [_ROOT_DIR, "/var/task", os.path.join(_ROOT_DIR, "fastapi_app"), _HERE]:
    if p and os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    from fastapi_app.main import app
except Exception as e1:
    print(f"Error loading fastapi_app.main: {e1}")
    try:
        from api.index import app
    except Exception as e2:
        print(f"Error loading api.index: {e2}")
        from fastapi import FastAPI
        app = FastAPI()
        @app.get("/")
        @app.get("/api/health")
        def fallback_health():
            return {"status": "healthy", "mode": "fallback"}

# Export for Vercel Serverless Function
handler = app
