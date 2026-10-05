import pytest
from unittest.mock import MagicMock
from api.services.rag_service import RAGService
from api.models import Message

@pytest.fixture
def rag_service():
    service = RAGService()
    service.llm_client = MagicMock()
    return service

def test_intent_inheritance_fee_structure(rag_service):
    history = [
        Message(role="user", content="fee structure"),
        Message(role="assistant", content="B.Tech is approximately \u20b91,15,000 per year...")
    ]
    query = "btech eee"
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="What is the fee structure for B.Tech EEE at MRDU?"))
    ]
    rag_service.llm_client.chat.completions.create.return_value = mock_response

    rewritten = rag_service.rewrite_query(query, history)
    
    assert "fee" in rewritten.lower()
    assert "structure" in rewritten.lower()
    assert "b.tech" in rewritten.lower()
    assert "eee" in rewritten.lower()

def test_intent_inheritance_eligibility(rag_service):
    history = [
        Message(role="user", content="What are the eligibility criteria for B.Tech?"),
        Message(role="assistant", content="Eligibility answer...")
    ]
    query = "btech eee"
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="What are the eligibility criteria for B.Tech EEE at MRDU?"))
    ]
    rag_service.llm_client.chat.completions.create.return_value = mock_response

    rewritten = rag_service.rewrite_query(query, history)
    
    assert "eligibility" in rewritten.lower()
    assert "b.tech eee" in rewritten.lower()

def test_intent_override_new_intent(rag_service):
    history = [
        Message(role="user", content="What is the fee structure?"),
        Message(role="assistant", content="Fee answer...")
    ]
    query = "What is the eligibility for B.Tech EEE?"
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="What is the eligibility for B.Tech EEE?"))
    ]
    rag_service.llm_client.chat.completions.create.return_value = mock_response

    rewritten = rag_service.rewrite_query(query, history)
    
    assert "eligibility" in rewritten.lower()
    assert "fee" not in rewritten.lower()

def test_standalone_specific_question_keeps_its_intent(rag_service):
    history = [
        Message(role="user", content="fee structure"),
        Message(role="assistant", content="B.Tech fee answer..."),
    ]
    query = "How many seats are there in B.Tech EEE?"
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=query))]
    rag_service.llm_client.chat.completions.create.return_value = mock_response

    rewritten = rag_service.rewrite_query(query, history)

    assert rewritten == query

def test_intent_inheritance_career(rag_service):
    history = [
        Message(role="user", content="What are the career opportunities after B.Tech EEE?"),
        Message(role="assistant", content="Career answer...")
    ]
    query = "cse"
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="What are the career opportunities after B.Tech CSE at MRDU?"))
    ]
    rag_service.llm_client.chat.completions.create.return_value = mock_response

    rewritten = rag_service.rewrite_query(query, history)
    
    assert "career" in rewritten.lower()
    assert "cse" in rewritten.lower()

def test_intent_standalone_no_history(rag_service):
    history = []
    query = "btech eee"
    
    rewritten = rag_service.rewrite_query(query, history)
    
    # Without context, keep the fragment rather than inventing an intent.
    assert rewritten == "btech eee"

def test_rewriter_receives_latest_user_intent_and_assistant_answer(rag_service):
    history = [
        Message(role="user", content="What courses does MRDU offer?"),
        Message(role="assistant", content="MRDU offers several programs."),
        Message(role="user", content="fee structure"),
        Message(role="assistant", content="B.Tech is approximately \u20b91,15,000 per year."),
    ]
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="What is the fee structure for B.Tech EEE at MRDU?"))
    ]
    rag_service.llm_client.chat.completions.create.return_value = mock_response

    rewritten = rag_service.rewrite_query("btech eee", history)

    assert "fee structure" in rewritten.lower()
    messages = rag_service.llm_client.chat.completions.create.call_args.kwargs["messages"]
    assert "MOST RECENT preceding user question" in messages[0]["content"]
    assert messages[-3]["content"] == "fee structure"
    assert "\u20b91,15,000" in messages[-2]["content"]
    assert messages[-1]["content"] == "New query: btech eee"
