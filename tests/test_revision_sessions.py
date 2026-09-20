import pytest
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from server import app, revision_memory

client = TestClient(app)

def test_revision_sessions_persistence():
    student_id = "test_student_rev_sessions"
    topic = "Binary Trees"

    # Clean previous test entries if any
    revision_memory.delete_sessions_for_topic(student_id, topic)

    # 1. Start revision session 1
    bundle_data = {
        "revision_lesson": "## Binary Trees Revision 1\n\nRoot, left and right subtrees.",
        "flashcards": {
            "title": "Binary Trees Quick Revision Deck",
            "cards": [
                {
                    "title": "Tree Invariant",
                    "summary": "Every node has at most 2 children.",
                    "prompt": "What is maximum degree of binary tree node?",
                    "accent": "cyan",
                    "points": ["Max degree is 2"],
                    "blocks": []
                }
            ]
        },
        "questions": [
            {
                "id": "rq1",
                "sub_concept": "Tree Invariant",
                "question": "What is the maximum number of children in a binary tree node?",
                "options": ["Option 1: 2", "Option 2: 3", "Option 3: Any"],
                "correct_answer": "Option 1: 2",
                "explanation": "Binary trees have at most 2 children."
            }
        ],
        "diagnosis": {
            "has_signals": True,
            "diagnosis_summary": "Learner struggled with node degree limits."
        }
    }

    s1 = revision_memory.save_session(student_id, topic, bundle_data)
    assert s1["title"] == "Revision 1 in Binary Trees"
    assert s1["revision_number"] == 1
    assert "id" in s1
    session_id_1 = s1["id"]

    # 2. Start revision session 2
    s2 = revision_memory.save_session(student_id, topic, bundle_data)
    assert s2["title"] == "Revision 2 in Binary Trees"
    assert s2["revision_number"] == 2
    session_id_2 = s2["id"]

    # 3. List sessions for this topic
    res = client.get(f"/api/revise/sessions/{student_id}/{topic}")
    assert res.status_code == 200
    sessions = res.json()
    assert len(sessions) >= 2
    assert sessions[0]["title"] == "Revision 2 in Binary Trees"
    assert sessions[1]["title"] == "Revision 1 in Binary Trees"

    # 4. Get specific session
    res = client.get(f"/api/revise/session/{session_id_1}")
    assert res.status_code == 200
    retrieved = res.json()
    assert retrieved["title"] == "Revision 1 in Binary Trees"
    assert "Tree Invariant" in retrieved["revision_lesson"] or len(retrieved["questions"]) == 1

    # 5. Verify revision quiz and update session
    verify_res = client.post(
        "/api/revise/verify",
        json={
            "student_id": student_id,
            "topic": topic,
            "session_id": session_id_1,
            "answers": {"rq1": "Option 1: 2"},
            "questions": bundle_data["questions"]
        }
    )
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["passed"] is True

    # 6. Check that session in DB has been updated with passed status
    res = client.get(f"/api/revise/session/{session_id_1}")
    assert res.status_code == 200
    updated_session = res.json()
    assert updated_session["passed"] is True
    assert updated_session["answers"] == {"rq1": "Option 1: 2"}

    # 7. Delete session 2
    del_res = client.delete(f"/api/revise/session/{session_id_2}")
    assert del_res.status_code == 200

    # Verify session 2 is gone
    res = client.get(f"/api/revise/sessions/{student_id}/{topic}")
    remaining_ids = [s["id"] for s in res.json()]
    assert session_id_2 not in remaining_ids
    assert session_id_1 in remaining_ids

    # Clean up test data
    revision_memory.delete_sessions_for_topic(student_id, topic)

if __name__ == "__main__":
    test_revision_sessions_persistence()
    print("ALL TESTS PASSED SUCCESSFULLY!")
