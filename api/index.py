# api/index.py — Root Vercel Serverless Entrypoint for FastAPI
import sys
import os

# Ensure Vercel /var/task working directory and parent directories are on Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR  = os.path.dirname(CURRENT_DIR)
VAR_TASK    = "/var/task"

for p in [VAR_TASK, PARENT_DIR, CURRENT_DIR, os.getcwd()]:
    if p and os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from fastapi_app.main import app

handler = app
