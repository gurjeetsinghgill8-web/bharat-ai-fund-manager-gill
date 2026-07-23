# api/index.py — Root Vercel Serverless Entrypoint for FastAPI
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from fastapi_app.main import app
except ImportError:
    from api.fastapi_app.main import app

handler = app
