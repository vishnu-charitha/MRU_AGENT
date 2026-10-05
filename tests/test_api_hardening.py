import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.main import app
import json
from api.services.rag_service import get_rag_service

client = TestClient(app)

class MockHit:
    def __init__(self, score, title="Mock", content="Mock content", url="Mock URL", campus="main"):
        self.score = score
        self.payload = {
            "title": title,
            "content": content,
            "source_url": url,
            "campus": campus
        }

@pytest.fixture
def mock_rag_service():
    with patch("api.routes.chat.get_rag_service") as mock_get:
        mock_service = MagicMock()
        mock_get.return_value = mock_service
        yield mock_service

def test_successful_chat_response(mock_rag_service):
    # Setup mock
    mock_rag_service.retrieve.return_value = [MockHit(1.0)]
    
    def mock_stream(query, hits, history):
        yield json.dumps({"sources": [{"title": "MRDU Mock", "url": "Mock URL", "score": 1.0}]}) + "\n"
        yield json.dumps({"answer_chunk": "This "}) + "\n"
        yield json.dumps({"answer_chunk": "is a test."}) + "\n"
        
    mock_rag_service.generate_answer_stream.side_effect = mock_stream
    
    response = client.post("/api/chat", json={"question": "What is this?"})
    assert response.status_code == 200
    
    chunks = response.text.strip().split("\n")
    assert len(chunks) == 3
    assert "sources" in json.loads(chunks[0])
    assert json.loads(chunks[1])["answer_chunk"] == "This "
    assert json.loads(chunks[2])["answer_chunk"] == "is a test."

def test_unsupported_question(mock_rag_service):
    mock_rag_service.retrieve.return_value = [MockHit(-20.0)]
    
    def mock_stream(query, hits, history):
        yield json.dumps({"answer": "I couldn't find enough information in the MRDU knowledge base to answer that accurately.", "sources": []}) + "\n"
        
    mock_rag_service.generate_answer_stream.side_effect = mock_stream
    
    response = client.post("/api/chat", json={"question": "Alien landing pad?"})
    assert response.status_code == 200
    chunk = json.loads(response.text.strip())
    assert "I couldn't find enough information" in chunk["answer"]
    assert chunk["sources"] == []

def test_malformed_request():
    # Sending missing required field
    response = client.post("/api/chat", json={})
    assert response.status_code == 422 # FastAPI validation error

def test_retrieval_failure(mock_rag_service):
    mock_rag_service.retrieve.side_effect = Exception("Qdrant connection refused")
    
    response = client.post("/api/chat", json={"question": "What is B.Tech?"})
    assert response.status_code == 500
    assert response.json()["detail"] == "An error occurred while generating the response."

def test_llm_timeout_streaming_failure(mock_rag_service):
    mock_rag_service.retrieve.return_value = [MockHit(1.0)]
    
    def mock_stream(query, hits, history):
        # Initial sources yield
        yield json.dumps({"sources": [{"title": "MRDU Mock", "url": "Mock URL", "score": 1.0}]}) + "\n"
        # Then simulated timeout
        yield json.dumps({"error": "The AI service is currently unavailable. Please try again in a few moments."}) + "\n"
        
    mock_rag_service.generate_answer_stream.side_effect = mock_stream
    
    response = client.post("/api/chat", json={"question": "What is B.Tech?"})
    assert response.status_code == 200
    
    chunks = response.text.strip().split("\n")
    assert len(chunks) == 2
    assert "error" in json.loads(chunks[1])
    assert "unavailable" in json.loads(chunks[1])["error"]

def test_service_initialization_failure():
    with patch("api.routes.chat.get_rag_service") as mock_get:
        mock_get.side_effect = Exception("Failed to load SentenceTransformer")
        response = client.post("/api/chat", json={"question": "Test"})
        assert response.status_code == 503
        assert response.json()["detail"] == "RAG service is currently unavailable."

def test_inference_guardrail_exact_rejection(mock_rag_service):
    # Weak retrieval but clears the -15.0 threshold (e.g. -10.0)
    mock_rag_service.retrieve.return_value = [MockHit(-10.0)]
    
    def mock_stream(query, hits, history):
        yield json.dumps({"sources": [{"title": "MRDU Mock", "url": "Mock URL", "score": -10.0}]}) + "\n"
        full_answer = "I couldn't find enough information in the MRDU knowledge base to answer that accurately."
        yield json.dumps({"answer_chunk": full_answer}) + "\n"
        if full_answer.strip().startswith("I couldn't find enough information"):
            yield json.dumps({"clear_sources": True}) + "\n"
            
    mock_rag_service.generate_answer_stream.side_effect = mock_stream
    response = client.post("/api/chat", json={"question": "Alien?"})
    assert response.status_code == 200
    chunks = response.text.strip().split("\n")
    assert json.loads(chunks[-1]).get("clear_sources") is True

def test_inference_guardrail_false_positive():
    rag = get_rag_service()
    hits = [MockHit(5.0)]
    
    # We will test the actual generate_answer_stream output
    with patch.object(rag, "llm_client") as mock_llm:
        mock_response = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.choices = [MagicMock()]
        mock_chunk.choices[0].delta.content = "I couldn't find enough information about M.Tech, but B.Tech is 100k."
        mock_response.__iter__.return_value = [mock_chunk]
        mock_llm.chat.completions.create.return_value = mock_response
        
        chunks = list(rag.generate_answer_stream("Fees?", hits))
        # Ensure we don't clear sources
        assert not any("clear_sources" in chunk for chunk in chunks if chunk)

