from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv
load_dotenv()
from .routes import chat
from .services.rag_service import get_rag_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="MRDU Knowledge Base RAG API")

import os
# CORS config
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/health")
def api_health_check():
    try:
        # Check Qdrant connectivity
        service = get_rag_service()
        # A simple check to see if client is alive
        service.qdrant_client.get_collection(service.qdrant_collection)
        return {"status": "ok", "qdrant": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "qdrant": "disconnected"}
