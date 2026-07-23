# frontend/api/index.py — Vercel Serverless Python Entrypoint
# Hosts the FastAPI backend directly on Vercel for 100% FREE!
import sys
import os

# Add project root directory to Python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi_app.main import app

# Export for Vercel Serverless Function
handler = app
