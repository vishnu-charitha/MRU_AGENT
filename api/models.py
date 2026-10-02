from pydantic import BaseModel, Field
from typing import Optional, List

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    campus: Optional[str] = None
    program: Optional[str] = None
    regulation: Optional[str] = None
    category: Optional[str] = None
    history: Optional[List[Message]] = []

class SourceModel(BaseModel):
    title: str
    url: str
    chunk_id: str
    score: float

class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceModel]
