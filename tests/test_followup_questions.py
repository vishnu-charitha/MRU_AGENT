import pytest
import json
from unittest.mock import MagicMock, patch
from api.services.rag_service import get_rag_service

@pytest.fixture
def rag_service():
    service = get_rag_service()
    service.llm_client = MagicMock()
    return service

def test_generate_followup_questions_valid(rag_service):
    # Mock LLM to return valid JSON with 3 suggestions
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "followups": [
                "What is the eligibility for B.Tech?",
                "What is the fee structure?",
                "Tell me more about the campus."
            ]
        })))
    ]
    rag_service.llm_client.chat.completions.create.return_value = mock_response

    history = [
        MagicMock(role="user", content="Hi"),
        MagicMock(role="assistant", content="Hello, I am the MRDU assistant.")
    ]
    original_query = "What is the duration of B.Tech?"
    full_answer = "B.Tech is a 4-year, 8-semester programme."

    followups = rag_service.generate_followup_questions(original_query, full_answer, history)

    # Max 2 suggestions returned
    assert len(followups) == 2
    assert followups[0] == "What is the eligibility for B.Tech?"
    assert followups[1] == "What is the fee structure?"

def test_generate_followup_questions_duplicate_filtering(rag_service):
    # Mock LLM returns questions that were already asked
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "followups": [
                "What is the eligibility for B.Tech?", # already asked in history
                "What is the fee structure?"
            ]
        })))
    ]
    rag_service.llm_client.chat.completions.create.return_value = mock_response

    history = [
        MagicMock(role="user", content="What is the eligibility for B.Tech?"),
        MagicMock(role="assistant", content="It requires 10+2 with 60% marks.")
    ]
    original_query = "What is the duration of B.Tech?"
    full_answer = "B.Tech is a 4-year, 8-semester programme."

    followups = rag_service.generate_followup_questions(original_query, full_answer, history)

    # Only 1 unique returned
    assert len(followups) == 1
    assert followups[0] == "What is the fee structure?"

def test_generate_followup_questions_malformed_string(rag_service):
    # Mock LLM returns a string instead of a list for 'followups'
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "followups": "What is the fee structure?"
        })))
    ]
    rag_service.llm_client.chat.completions.create.return_value = mock_response

    followups = rag_service.generate_followup_questions("Q", "A", [])
    assert followups == []

def test_generate_followup_questions_empty_or_malformed(rag_service):
    # Mock LLM returns malformed JSON
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="This is not json"))
    ]
    rag_service.llm_client.chat.completions.create.return_value = mock_response

    followups = rag_service.generate_followup_questions("Q", "A", [])
    assert followups == []

def test_generate_followup_questions_failure_handled(rag_service):
    # Mock LLM raises Exception
    rag_service.llm_client.chat.completions.create.side_effect = Exception("API Error")

    followups = rag_service.generate_followup_questions("Q", "A", [])
    assert followups == []
