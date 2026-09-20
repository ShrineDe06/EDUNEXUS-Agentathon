import datetime
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any, Dict, List, Optional


class TestMemory:
    """Local SQLite persistence for test sessions across studied concepts and uploaded documents."""

    def __init__(self, db_path: str = "backend/data/edunexus.db"):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS test_sessions (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    subsection TEXT NOT NULL, -- 'studied_concept' or 'uploaded_file'
                    document_name TEXT,
                    title TEXT NOT NULL,
                    test_number INTEGER NOT NULL,
                    question_count INTEGER NOT NULL,
                    questions TEXT NOT NULL,
                    answers TEXT,
                    timing TEXT, -- JSON dictionary of { question_id: seconds_spent }
                    total_time_seconds REAL,
                    score REAL,
                    marks INTEGER,
                    passed INTEGER,
                    status TEXT NOT NULL DEFAULT 'IN_PROGRESS', -- 'IN_PROGRESS' or 'COMPLETED'
                    review_mode TEXT, -- 'text' or 'flashcards'
                    review_content TEXT, -- JSON string of review text or deck
                    loop_round INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS ix_test_sessions_student_topic
                ON test_sessions(student_id, topic, test_number DESC);

                CREATE INDEX IF NOT EXISTS ix_test_sessions_created
                ON test_sessions(created_at DESC);
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _row_to_dict(self, row: sqlite3.Row, include_full_payload: bool = True) -> Dict[str, Any]:
        data = {
            "id": row["id"],
            "student_id": row["student_id"],
            "topic": row["topic"],
            "subsection": row["subsection"],
            "document_name": row["document_name"],
            "title": row["title"],
            "test_number": row["test_number"],
            "question_count": row["question_count"],
            "score": row["score"],
            "marks": row["marks"],
            "passed": bool(row["passed"]) if row["passed"] is not None else None,
            "status": row["status"],
            "total_time_seconds": row["total_time_seconds"],
            "review_mode": row["review_mode"],
            "loop_round": row["loop_round"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

        if include_full_payload:
            try:
                data["questions"] = json.loads(row["questions"]) if row["questions"] else []
            except Exception:
                data["questions"] = []
            try:
                data["answers"] = json.loads(row["answers"]) if row["answers"] else {}
            except Exception:
                data["answers"] = {}
            try:
                data["timing"] = json.loads(row["timing"]) if row["timing"] else {}
            except Exception:
                data["timing"] = {}
            try:
                data["review_content"] = json.loads(row["review_content"]) if row["review_content"] else None
            except Exception:
                data["review_content"] = row["review_content"]
        return data

    def create_session(
        self,
        student_id: str,
        topic: str,
        subsection: str,
        questions: List[Dict[str, Any]],
        document_name: Optional[str] = None,
        loop_round: int = 1
    ) -> Dict[str, Any]:
        """Creates and saves a new test session in local SQLite."""
        now = self._now()
        session_id = str(uuid.uuid4())
        question_count = len(questions)

        with self._connect() as connection:
            # Determine next test number for this topic/document
            row = connection.execute(
                """
                SELECT MAX(test_number) as max_n
                FROM test_sessions
                WHERE student_id = ? AND LOWER(TRIM(topic)) = LOWER(TRIM(?))
                """,
                (student_id, topic)
            ).fetchone()

            max_n = row["max_n"] if row and row["max_n"] is not None else 0
            test_number = max_n + 1

            if subsection == "uploaded_file" and document_name:
                title = f"Test {test_number} on {document_name}"
            else:
                title = f"Test {test_number} in {topic}"

            connection.execute(
                """
                INSERT INTO test_sessions (
                    id, student_id, topic, subsection, document_name,
                    title, test_number, question_count, questions,
                    answers, timing, total_time_seconds, score, marks,
                    passed, status, review_mode, review_content,
                    loop_round, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    student_id,
                    topic,
                    subsection,
                    document_name,
                    title,
                    test_number,
                    question_count,
                    json.dumps(questions),
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "IN_PROGRESS",
                    None,
                    None,
                    loop_round,
                    now,
                    now
                )
            )

            saved = connection.execute("SELECT * FROM test_sessions WHERE id = ?", (session_id,)).fetchone()
            return self._row_to_dict(saved, include_full_payload=True)

    def update_submission(
        self,
        session_id: str,
        answers: Dict[str, str],
        timing: Dict[str, float],
        score: float,
        marks: int,
        passed: bool,
        total_time_seconds: float
    ) -> Optional[Dict[str, Any]]:
        """Updates a test session with student answers, timing metrics, and final score."""
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE test_sessions
                SET answers = ?,
                    timing = ?,
                    total_time_seconds = ?,
                    score = ?,
                    marks = ?,
                    passed = ?,
                    status = 'COMPLETED',
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(answers),
                    json.dumps(timing),
                    total_time_seconds,
                    score,
                    marks,
                    1 if passed else 0,
                    now,
                    session_id
                )
            )

            row = connection.execute("SELECT * FROM test_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                return None
            return self._row_to_dict(row, include_full_payload=True)

    def update_review(
        self,
        session_id: str,
        review_mode: str,
        review_content: Any
    ) -> Optional[Dict[str, Any]]:
        """Stores the generated remediation review (text concept or flashcards) in the test session."""
        now = self._now()
        content_str = json.dumps(review_content) if not isinstance(review_content, str) else review_content
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE test_sessions
                SET review_mode = ?,
                    review_content = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    review_mode,
                    content_str,
                    now,
                    session_id
                )
            )
            row = connection.execute("SELECT * FROM test_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                return None
            return self._row_to_dict(row, include_full_payload=True)

    def list_sessions(
        self,
        student_id: str,
        topic: Optional[str] = None,
        subsection: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists test sessions for a student, optionally filtered by topic or subsection."""
        with self._connect() as connection:
            query = "SELECT * FROM test_sessions WHERE student_id = ?"
            params: List[Any] = [student_id]

            if topic:
                query += " AND LOWER(TRIM(topic)) = LOWER(TRIM(?))"
                params.append(topic)
            if subsection:
                query += " AND subsection = ?"
                params.append(subsection)

            query += " ORDER BY created_at DESC"
            rows = connection.execute(query, tuple(params)).fetchall()
            return [self._row_to_dict(r, include_full_payload=False) for r in rows]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves complete details of a test session by ID."""
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM test_sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                return None
            return self._row_to_dict(row, include_full_payload=True)

    def delete_session(self, session_id: str) -> bool:
        """Deletes a test session."""
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM test_sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0

    def delete_sessions_for_topic(self, student_id: str, topic: str) -> int:
        """Deletes all test sessions for a given topic."""
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM test_sessions WHERE student_id = ? AND LOWER(TRIM(topic)) = LOWER(TRIM(?))",
                (student_id, topic)
            )
            return cursor.rowcount
