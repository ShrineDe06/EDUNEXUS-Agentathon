from backend.memory.rag_scope import is_explicit_document_request, select_relevant_document_chunks


METADATA = [
    {
        "document": "compiler-session.pdf",
        "text": "A compiler performs lexical analysis, syntax analysis, optimization, and code generation.",
    },
    {
        "document": "another-chat.pdf",
        "text": "Large language models use transformer attention and predict the next token.",
    },
]


def test_unrelated_question_does_not_force_session_document_context():
    chunks = select_relevant_document_chunks(
        metadata=METADATA,
        scores=[0.78, 0.72],
        indices=[1, 0],
        allowed_documents=["compiler-session.pdf"],
        query="Explain how LLM works",
    )
    assert chunks == []


def test_relevant_question_uses_only_the_current_sessions_document():
    chunks = select_relevant_document_chunks(
        metadata=METADATA,
        scores=[0.84, 0.80],
        indices=[1, 0],
        allowed_documents=["compiler-session.pdf"],
        query="What happens during syntax analysis in a compiler?",
    )
    assert chunks == [METADATA[0]["text"]]


def test_explicit_document_request_can_use_the_attachment():
    chunks = select_relevant_document_chunks(
        metadata=METADATA,
        scores=[0.35],
        indices=[0],
        allowed_documents=["compiler-session.pdf"],
        query="Summarize this PDF",
        explicit_document_request=True,
        threshold=0.28,
    )
    assert chunks == [METADATA[0]["text"]]


def test_document_reference_detection_does_not_match_general_source_questions():
    assert is_explicit_document_request("Summarize the PDF") is True
    assert is_explicit_document_request("What does my document say about optimization?") is True
    assert is_explicit_document_request("Explain open source LLMs") is False
