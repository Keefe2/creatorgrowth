"""Vercel serverless entrypoint.

Vercel's Python runtime detects the module-level ASGI `app` natively —
no uvicorn, no wrapper needed. The backend is mounted under /api so the
same-origin frontend can call /api/* and the rewrite in vercel.json
forwards it here with the original path intact.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import FastAPI

from app.main import app as backend_app

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", backend_app)
