from pydantic import BaseModel, Field
from typing import Optional, List

class Message(BaseModel):
    role: str
    content: str
    followUpQuestions: Optional[List[str]] = None

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


class StudentRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=1, max_length=255)
    mobile_number: str = Field(..., min_length=1, max_length=30)
    interested_course: str = Field(..., max_length=50)
    consent: bool = Field(...)


class StudentRegisterResponse(BaseModel):
    success: bool
    student_id: str
    token: str
    message: str


class SessionValidateResponse(BaseModel):
    valid: bool
    student_id: str
