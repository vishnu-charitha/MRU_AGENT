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
        safe_history = str(request.history).encode('ascii', 'replace').decode('ascii')
        logger.info(f"DEBUG BACKEND: Received question: {request.question}")
        logger.info(f"DEBUG BACKEND: Received history: {safe_history}")
        
        standalone_query = rag_service.rewrite_query(request.question, request.history)
        logger.info(f"DEBUG BACKEND: Standalone query generated: {standalone_query}")
        
        hits = rag_service.retrieve(
            query=standalone_query,
            campus=request.campus,
            category=request.category,
            program=request.program,
            regulation=request.regulation,
            limit=5
        )

        return StreamingResponse(
            rag_service.generate_answer_stream(request.question, hits, history=request.history),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        logger.error(f"Error during RAG generation: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while generating the response.")
