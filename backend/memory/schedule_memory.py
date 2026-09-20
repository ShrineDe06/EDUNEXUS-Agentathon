import os
import sqlite3
import json
import uuid
import datetime
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ScheduleMemory:
    """
    Manages study and test schedules for students in local SQLite (backend/data/edunexus.db).
    Allows students to schedule revisions and tests on specific topics across days with multiple alert times.
    """

    def __init__(self, db_path: str = "backend/data/edunexus.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS study_schedules (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    mode TEXT NOT NULL, -- 'revise' or 'test'
                    date TEXT NOT NULL, -- YYYY-MM-DD
                    time_slots TEXT NOT NULL, -- JSON array of strings e.g. ["09:00", "15:30"]
                    email TEXT,
                    note TEXT,
                    status TEXT DEFAULT 'SCHEDULED', -- 'SCHEDULED', 'COMPLETED', 'CANCELLED'
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_schedules_student_topic
                ON study_schedules (student_id, topic, date)
                """
            )

    def _now(self) -> str:
        return datetime.datetime.utcnow().isoformat()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        data = dict(row)
        try:
            data["time_slots"] = json.loads(row["time_slots"]) if row["time_slots"] else []
        except Exception:
            data["time_slots"] = []
        return data

    def create_schedule(
        self,
        student_id: str,
        topic: str,
        mode: str,
        date: str,
        time_slots: List[str],
        email: Optional[str] = None,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new study/test schedule with multiple time slots."""
        now = self._now()
        schedule_id = str(uuid.uuid4())
        slots_json = json.dumps(time_slots if isinstance(time_slots, list) else [time_slots])

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO study_schedules (
                    id, student_id, topic, mode, date, time_slots, email, note, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'SCHEDULED', ?, ?)
                """,
                (
                    schedule_id,
                    student_id,
                    topic,
                    mode.lower(),
                    date,
                    slots_json,
                    email or "",
                    note or "",
                    now,
                    now
                )
            )
            row = conn.execute("SELECT * FROM study_schedules WHERE id = ?", (schedule_id,)).fetchone()
            return self._row_to_dict(row)

    def list_schedules(
        self,
        student_id: str,
        mode: Optional[str] = None,
        topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists schedules for a student ordered by date."""
        with self._connect() as conn:
            query = "SELECT * FROM study_schedules WHERE student_id = ?"
            params: List[Any] = [student_id]

            if mode:
                query += " AND LOWER(TRIM(mode)) = LOWER(TRIM(?))"
                params.append(mode)

            if topic:
                query += " AND LOWER(TRIM(topic)) = LOWER(TRIM(?))"
                params.append(topic)

            query += " ORDER BY date ASC, created_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single schedule by ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM study_schedules WHERE id = ?", (schedule_id,)).fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def delete_schedule(self, schedule_id: str) -> bool:
        """Deletes a schedule by ID."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM study_schedules WHERE id = ?", (schedule_id,))
            return cursor.rowcount > 0

    def update_status(self, schedule_id: str, status: str) -> Optional[Dict[str, Any]]:
        """Updates status of a schedule."""
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE study_schedules SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, schedule_id)
            )
            row = conn.execute("SELECT * FROM study_schedules WHERE id = ?", (schedule_id,)).fetchone()
            if not row:
                return None
            return self._row_to_dict(row)
