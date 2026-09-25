from fastapi import APIRouter, HTTPException
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
        hits = rag_service.retrieve(
            query=request.question,
            campus=request.campus,
            category=request.category,
            program=request.program,
            regulation=request.regulation
        )
        
        result = rag_service.generate_answer(request.question, hits)
        
        return ChatResponse(
            answer=result["answer"],
            sources=[SourceModel(**s) for s in result["sources"]]
        )
    except Exception as e:
        logger.error(f"Error during RAG generation: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while generating the response.")
