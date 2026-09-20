import datetime
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any, Dict, List, Optional


class RevisionMemory:
    """Local SQLite persistence for revision sessions under specific topics."""

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
                CREATE TABLE IF NOT EXISTS revision_sessions (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    title TEXT NOT NULL,
                    revision_number INTEGER NOT NULL,
                    revision_lesson TEXT NOT NULL,
                    flashcards TEXT NOT NULL,
                    questions TEXT NOT NULL,
                    diagnosis TEXT,
                    verify_result TEXT,
                    answers TEXT,
                    score REAL,
                    passed INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS ix_revision_sessions_student_topic
                ON revision_sessions(student_id, topic, revision_number DESC);

                CREATE INDEX IF NOT EXISTS ix_revision_sessions_created
                ON revision_sessions(created_at DESC);
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
            "title": row["title"],
            "revision_number": row["revision_number"],
            "score": row["score"],
            "passed": bool(row["passed"]) if row["passed"] is not None else None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

        if include_full_payload:
            data["revision_lesson"] = row["revision_lesson"]
            try:
                data["flashcards"] = json.loads(row["flashcards"]) if row["flashcards"] else {}
            except Exception:
                data["flashcards"] = {}
            try:
                data["questions"] = json.loads(row["questions"]) if row["questions"] else []
            except Exception:
                data["questions"] = []
            try:
                data["diagnosis"] = json.loads(row["diagnosis"]) if row["diagnosis"] else None
            except Exception:
                data["diagnosis"] = None
            try:
                data["verify_result"] = json.loads(row["verify_result"]) if row["verify_result"] else None
            except Exception:
                data["verify_result"] = None
            try:
                data["answers"] = json.loads(row["answers"]) if row["answers"] else {}
            except Exception:
                data["answers"] = {}
        else:
            # Summary info for card / list display
            try:
                cards = json.loads(row["flashcards"]) if row["flashcards"] else {}
                data["flashcards_count"] = len(cards.get("cards", [])) if isinstance(cards, dict) else 0
            except Exception:
                data["flashcards_count"] = 0
            try:
                qs = json.loads(row["questions"]) if row["questions"] else []
                data["questions_count"] = len(qs) if isinstance(qs, list) else 0
            except Exception:
                data["questions_count"] = 0
            data["has_diagnosis"] = bool(row["diagnosis"])

        return data

    def save_session(
        self,
        student_id: str,
        topic: str,
        bundle: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Stores the generated revision text, flashcards, questions, and diagnosis
        under the specific topic locally as 'Revision n in <topic>' where n is 1, 2, 3...
        """
        now = self._now()
        session_id = str(uuid.uuid4())

        with self._connect() as connection:
            # Determine next n for this topic
            row = connection.execute(
                """
                SELECT MAX(revision_number) as max_n
                FROM revision_sessions
                WHERE student_id = ? AND LOWER(TRIM(topic)) = LOWER(TRIM(?))
                """,
                (student_id, topic)
            ).fetchone()

            max_n = row["max_n"] if row and row["max_n"] is not None else 0
            next_n = max_n + 1
            title = f"Revision {next_n} in {topic}"

            revision_lesson = bundle.get("revision_lesson", "")
            flashcards_json = json.dumps(bundle.get("flashcards") or {})
            questions_json = json.dumps(bundle.get("questions") or [])
            diagnosis_json = json.dumps(bundle.get("diagnosis")) if bundle.get("diagnosis") else None
            verify_result_json = json.dumps(bundle.get("verify_result")) if bundle.get("verify_result") else None
            answers_json = json.dumps(bundle.get("answers")) if bundle.get("answers") else None

            connection.execute(
                """
                INSERT INTO revision_sessions (
                    id, student_id, topic, title, revision_number,
                    revision_lesson, flashcards, questions, diagnosis,
                    verify_result, answers, score, passed,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    student_id,
                    topic,
                    title,
                    next_n,
                    revision_lesson,
                    flashcards_json,
                    questions_json,
                    diagnosis_json,
                    verify_result_json,
                    answers_json,
                    None,
                    None,
                    now,
                    now
                )
            )

            # Fetch the saved row
            saved_row = connection.execute(
                "SELECT * FROM revision_sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            return self._row_to_dict(saved_row, include_full_payload=True)

    def list_sessions(
        self,
        student_id: str,
        topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List revision sessions for a student, optionally filtered by topic."""
        with self._connect() as connection:
            if topic:
                rows = connection.execute(
                    """
                    SELECT * FROM revision_sessions
                    WHERE student_id = ? AND LOWER(TRIM(topic)) = LOWER(TRIM(?))
                    ORDER BY revision_number DESC, created_at DESC
                    """,
                    (student_id, topic)
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM revision_sessions
                    WHERE student_id = ?
                    ORDER BY created_at DESC
                    """,
                    (student_id,)
                ).fetchall()

            return [self._row_to_dict(r, include_full_payload=False) for r in rows]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific revision session."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM revision_sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_dict(row, include_full_payload=True)

    def update_session_verification(
        self,
        session_id: str,
        answers: Dict[str, str],
        verify_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a revision session with verification quiz answers and result."""
        now = self._now()
        passed = 1 if verify_result.get("passed") else 0
        score = verify_result.get("score")

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE revision_sessions
                SET answers = ?,
                    verify_result = ?,
                    passed = ?,
                    score = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    json.dumps(answers),
                    json.dumps(verify_result),
                    passed,
                    score,
                    now,
                    session_id
                )
            )

            row = connection.execute(
                "SELECT * FROM revision_sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            if not row:
                return None
            return self._row_to_dict(row, include_full_payload=True)

    def delete_session(self, session_id: str) -> bool:
        """Delete a revision session by id."""
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM revision_sessions WHERE id = ?",
                (session_id,)
            )
            return cursor.rowcount > 0

    def delete_sessions_for_topic(self, student_id: str, topic: str) -> int:
        """Delete all revision sessions for a topic."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM revision_sessions
                WHERE student_id = ? AND LOWER(TRIM(topic)) = LOWER(TRIM(?))
                """,
                (student_id, topic)
            )
            return cursor.rowcount
