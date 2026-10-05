from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import logging
from ..models import ChatRequest, ChatResponse, SourceModel
from ..services.rag_service import get_rag_service

router = APIRouter()
logger = logging.getLogger("api")

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # We lazy-load the service so startup doesn't block immediately on imports if it fails
        rag_service = get_rag_service()
    except Exception as e:
        logger.error(f"Service initialization error: {e}")
        raise HTTPException(status_code=503, detail="RAG service is currently unavailable.")

    try:
        # Safely log history and question to avoid UnicodeEncodeError on Windows consoles
        safe_history = str(request.history).encode('ascii', 'replace').decode('ascii')
        safe_question = request.question.encode('ascii', 'replace').decode('ascii')
        logger.info(f"DEBUG BACKEND: Received question: {safe_question}")
        logger.info(f"DEBUG BACKEND: Received history: {safe_history}")
    except Exception as e:
        logger.exception("Failed during request logging")
        # Do NOT raise HTTPException(500) merely because logging failed
        
    try:
        standalone_query = rag_service.rewrite_query(request.question, request.history)
        safe_standalone = standalone_query.encode('ascii', 'replace').decode('ascii')
        logger.info(f"DEBUG BACKEND: Standalone query generated: {safe_standalone}")
    except Exception as e:
        logger.exception("Query rewriting failure")
        raise HTTPException(status_code=500, detail="An error occurred while generating the response.")
        
    try:
        hits = rag_service.retrieve(
            query=standalone_query,
            campus=request.campus,
            category=request.category,
            program=request.program,
            regulation=request.regulation,
            limit=5
        )
    except Exception as e:
        logger.exception("Retrieval failure")
        raise HTTPException(status_code=500, detail="An error occurred while generating the response.")

    try:
        return StreamingResponse(
            rag_service.generate_answer_stream(request.question, hits, history=request.history),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        logger.exception("Answer streaming initialization failure")
        raise HTTPException(status_code=500, detail="An error occurred while generating the response.")
