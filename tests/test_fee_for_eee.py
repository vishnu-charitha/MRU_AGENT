import pytest
from api.models import Message
from api.services.rag_service import get_rag_service

def test_fee_for_eee_context():
    service = get_rag_service()
    history = [
        Message(role="user", content="What are the B.Tech specializations?"),
        Message(role="assistant", content="B.Tech includes CSE, AI/ML, Data Science, Cyber Security, IoT, IT, ECE, EEE, Civil, Mechanical, Mining, etc."),
        Message(role="user", content="fee structure of btech"),
        Message(role="assistant", content="The indicative B.Tech tuition fee is Rs. 1,15,000 per year.")
    ]
    query = "fee for eee"
    
    rewritten = service.rewrite_query(query, history)
    
    assert "b.tech" in rewritten.lower() or "btech" in rewritten.lower(), f"Rewritten query missed B.Tech context: {rewritten}"
    assert "eee" in rewritten.lower(), f"Rewritten query missed EEE context: {rewritten}"
    assert "fee" in rewritten.lower(), f"Rewritten query missed fee intent: {rewritten}"
    
    # Check that 'fee for mba' doesn't inherit B.Tech/EEE
    mba_query = "fee for MBA"
    rewritten_mba = service.rewrite_query(mba_query, history)
    assert "eee" not in rewritten_mba.lower(), f"MBA query improperly inherited EEE: {rewritten_mba}"
    
    # Retrieve
    hits = service.retrieve(rewritten)
    assert len(hits) > 0, "No chunks retrieved for B.Tech EEE fee"
    
    answer_dict = service.generate_answer(query, hits, history)
    answer = answer_dict["answer"].lower()
    
    assert "1,15,000" in answer or "115000" in answer, "Answer missed indicative fee"
    assert "eee" in answer, "Answer missed EEE context"
    assert "not find" in answer or "could not find" in answer or "couldn't find" in answer or "general" in answer or "specific" in answer, "Answer must clarify lack of EEE specific fee"
