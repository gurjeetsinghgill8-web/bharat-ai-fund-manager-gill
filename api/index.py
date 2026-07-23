# api/index.py — Root Vercel Serverless Entrypoint for FastAPI
import sys
import os

# Add root folder to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastapi_app.main import app

handler = app
