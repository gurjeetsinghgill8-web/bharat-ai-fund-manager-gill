# api/index.py — Vercel Serverless Entrypoint
import sys
import os

API_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(API_DIR)

for path in [API_DIR, ROOT_DIR, "/var/task/api", "/var/task"]:
    if path and path not in sys.path:
        sys.path.insert(0, path)

try:
    from fastapi_app.main import app
except Exception:
    try:
        from main import app
    except Exception:
        from api.fastapi_app.main import app

handler = app
