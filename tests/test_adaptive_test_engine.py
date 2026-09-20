import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from server import app, test_memory

client = TestClient(app)

def test_adaptive_test_engine():
    student_id = "test_student_adaptive_test"
    topic = "Hash Maps"

    # Clean previous test entries
    test_memory.delete_sessions_for_topic(student_id, topic)

    # 1. Start test with 6 questions
    start_res = client.post(
        "/api/test/start",
        json={
            "student_id": student_id,
            "topic": topic,
            "subsection": "studied_concept",
            "question_count": 6,
            "loop_round": 1
        }
    )
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert "session_id" in start_data
    assert "attempt_id" in start_data
    assert len(start_data["questions"]) >= 5
    assert start_data["topic"] == topic
    session_id = start_data["session_id"]
    attempt_id = start_data["attempt_id"]
    questions = start_data["questions"]

    # 2. Submit test with per-question timing
    timing_map = {q["id"]: (10.0 + idx * 5.0) for idx, q in enumerate(questions)}
    # Let's answer the first question correctly and remaining with Option 4
    answers = {}
    for idx, q in enumerate(questions):
        answers[q["id"]] = q["correct_answer"] if idx == 0 else "Option 4: Non-deterministic shift"

    submit_res = client.post(
        "/api/test/submit",
        json={
            "student_id": student_id,
            "topic": topic,
            "attempt_id": attempt_id,
            "session_id": session_id,
            "answers": answers,
            "questions": questions,
            "timing": timing_map
        }
    )
    assert submit_res.status_code == 200
    sub_data = submit_res.json()
    assert "score" in sub_data
    assert "marks" in sub_data
    assert "total_time_seconds" in sub_data
    assert sub_data["marks"] == 1
    assert len(sub_data["failed_results"]) == len(questions) - 1
    assert "average_time_per_question" in sub_data

    # 3. Test Remediation Review: Text Concept
    failed_items = sub_data["failed_results"]
    text_review_res = client.post(
        "/api/test/review",
        json={
            "student_id": student_id,
            "topic": topic,
            "session_id": session_id,
            "review_mode": "text",
            "failed_results": failed_items,
            "timings": timing_map
        }
    )
    assert text_review_res.status_code == 200
    text_data = text_review_res.json()
    assert text_data["review_mode"] == "text"
    assert isinstance(text_data["content"], str)

    # 4. Test Remediation Review: Flashcards
    card_review_res = client.post(
        "/api/test/review",
        json={
            "student_id": student_id,
            "topic": topic,
            "session_id": session_id,
            "review_mode": "flashcards",
            "failed_results": failed_items,
            "timings": timing_map
        }
    )
    assert card_review_res.status_code == 200
    card_data = card_review_res.json()
    assert card_data["review_mode"] == "flashcards"
    assert "cards" in card_data["content"]

    # 5. List saved test sessions
    list_res = client.get(f"/api/test/sessions/{student_id}?topic={topic}")
    assert list_res.status_code == 200
    saved_list = list_res.json()
    assert len(saved_list) >= 1
    assert saved_list[0]["id"] == session_id
    assert saved_list[0]["marks"] == 1
    assert saved_list[0]["status"] == "COMPLETED"

    # 6. Retrieve single session
    detail_res = client.get(f"/api/test/session/{session_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["id"] == session_id
    assert detail_data["review_mode"] == "flashcards"

    # 7. Clean up
    del_res = client.delete(f"/api/test/session/{session_id}")
    assert del_res.status_code == 200

    test_memory.delete_sessions_for_topic(student_id, topic)

if __name__ == "__main__":
    test_adaptive_test_engine()
    print("ALL ADAPTIVE TEST ENGINE TESTS PASSED SUCCESSFULLY!")
