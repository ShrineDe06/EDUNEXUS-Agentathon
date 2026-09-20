from backend.memory.chat_memory import ChatMemory


def test_chat_session_round_trip(tmp_path):
    memory = ChatMemory(str(tmp_path / "chat.db"))
    created = memory.create_session("student_1", "Linear algebra", "Learn vectors")

    memory.add_message(created["id"], "user", "What is a vector?")
    memory.add_message(created["id"], "tutor", "A vector has magnitude and direction.")

    loaded = memory.get_session(created["id"])
    assert loaded["title"] == "Linear algebra"
    assert [message["sender"] for message in loaded["messages"]] == ["user", "tutor"]
    assert memory.list_sessions("student_1")[0]["message_count"] == 2


def test_attachments_remain_linked_to_their_session(tmp_path):
    memory = ChatMemory(str(tmp_path / "chat.db"))
    created = memory.create_session("student_1", "Thermodynamics", "Review the first law")
    document = tmp_path / "lesson.pdf"
    document.write_bytes(b"local lesson content")

    attachment = memory.add_attachment(
        created["id"],
        display_name="lesson.pdf",
        stored_name="unique_lesson.pdf",
        file_path=str(document),
        content_type="application/pdf",
        size=document.stat().st_size,
    )

    reopened = memory.get_session(created["id"])
    assert reopened["attachments"][0]["id"] == attachment["id"]
    assert reopened["attachments"][0]["display_name"] == "lesson.pdf"
    assert memory.get_attachment(attachment["id"])["file_path"] == str(document)


def test_structured_responses_are_restored_with_chat_history(tmp_path):
    memory = ChatMemory(str(tmp_path / "chat.db"))
    created = memory.create_session("student_1", "Networks", "Learn packet routing")
    deck = {"title": "Routing", "cards": [{"title": "Hop", "points": ["One link"]}]}

    memory.add_message(
        created["id"], "tutor", "Interactive flashcards: Routing",
        content_type="flashcards", content_data=deck,
    )

    message = memory.get_session(created["id"])["messages"][0]
    assert message["content_type"] == "flashcards"
    assert message["content_data"] == deck
