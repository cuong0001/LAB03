"""Read settings from .env"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Use the .env NEXT TO this file, even if the app was started from another folder.
load_dotenv(Path(__file__).with_name(".env"), override=False)

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "").strip()
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY", "").strip()

OLLAMA_URL = os.getenv("OLLAMA_URL", "").strip().rstrip("/")
# `or` (not a getenv default) so an EMPTY value in .env still falls back
EMBED_MODEL = os.getenv("EMBED_MODEL", "").strip() or "embeddinggemma"
CHAT_MODEL = os.getenv("CHAT_MODEL", "").strip() or "qwen3:4b"