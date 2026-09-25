from pydantic import BaseModel, Field
from typing import Optional, List

class ChatRequest(BaseModel):
    question: str
    campus: Optional[str] = None
    program: Optional[str] = None
    regulation: Optional[str] = None
    category: Optional[str] = None

class SourceModel(BaseModel):
    title: str
    url: str
    chunk_id: str
    score: float

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceModel]
