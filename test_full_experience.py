import os
import pytest
from fastapi.testclient import TestClient
from server import app, learner_memory

client = TestClient(app)

def test_01_health_and_root():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    root_res = client.get("/")
    assert root_res.status_code == 200

def test_02_learner_profile():
    res = client.get("/api/learner/test_user_99")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == "test_user_99"
    assert "mastered_subconcepts_count" in data

def test_03_learn_chat_mode_a():
    payload = {
        "student_id": "test_user_99",
        "topic": "Python Slicing",
        "message": "How does Python slicing work?",
        "document_name": None
    }
    res = client.post("/api/learn/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert data["response"] is not None
    assert data["visualization"] is not None
    assert data["visualization"]["type"] == "array_indexing"

def test_04_save_learning_event():
    payload = {
        "student_id": "test_user_99",
        "topic": "Python Slicing",
        "sub_concept": "Indexing Boundaries",
        "source_type": "freeform",
        "mode": "learn",
        "status": "EXPOSED"
    }
    res = client.post("/api/learn/save_event", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["topic"] == "Python Slicing"
    assert data["status"] == "EXPOSED"

def test_05_check_understanding():
    payload = {
        "student_id": "test_user_99",
        "topic": "Python Slicing"
    }
    res = client.post("/api/learn/check_understanding", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "questions" in data
    assert len(data["questions"]) >= 2

def test_06_revise_topics_and_start():
    # Save a revision event first
    learner_memory.save_learning_event("test_user_99", "Python Slicing", status="NEEDS_REVISION")
    
    res = client.get("/api/revise/topics/test_user_99")
    assert res.status_code == 200
    topics = res.json()
    assert len(topics) >= 1

    start_res = client.post("/api/revise/start", json={"student_id": "test_user_99", "topic": "Python Slicing"})
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "revision_lesson" in start_data
    assert "questions" in start_data

def test_07_revise_verify_pass():
    questions = [
        {
            "id": "q1",
            "sub_concept": "Indexing",
            "question": "Sample q1",
            "options": ["Correct", "Wrong"],
            "correct_answer": "Option 1: Correct"
        },
        {
            "id": "q2",
            "sub_concept": "Boundaries",
            "question": "Sample q2",
            "options": ["Correct", "Wrong"],
            "correct_answer": "Option 1: Correct"
        }
    ]
    payload = {
        "student_id": "test_user_99",
        "topic": "Python Slicing",
        "answers": {"q1": "Option 1: Correct", "q2": "Option 1: Correct"},
        "questions": questions
    }
    res = client.post("/api/revise/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is True
    assert data["status"] == "MASTERED"

def test_08_test_start_and_submit():
    start_res = client.post("/api/test/start", json={"student_id": "test_user_99", "topic": "Python Lists"})
    assert start_res.status_code == 200
    test_data = start_res.json()
    assert "attempt_id" in test_data
    assert len(test_data["questions"]) == 5

    # Submit answers
    answers = {q.get("id") or q.get("question_id", f"q_{idx+1}"): q["options"][0] for idx, q in enumerate(test_data["questions"])}

    submit_payload = {
        "student_id": "test_user_99",
        "topic": "Python Lists",
        "attempt_id": test_data["attempt_id"],
        "answers": answers,
        "questions": test_data["questions"]
    }
    sub_res = client.post("/api/test/submit", json=submit_payload)
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert "score" in sub_data
    assert "thinking_process" in sub_data

if __name__ == "__main__":
    pytest.main(["-v", "test_full_experience.py"])
