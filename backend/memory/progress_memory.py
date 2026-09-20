import os
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ProgressMemory:
    def __init__(self, db_path: str = "backend/data/edunexus.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS progress_reports (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    report_data TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_progress_reports_student 
                ON progress_reports (student_id, created_at DESC)
            """)
            conn.commit()

    def save_report(self, student_id: str, report_data: Dict[str, Any]) -> Dict[str, Any]:
        report_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        # Inject metadata
        report_data["id"] = report_id
        report_data["student_id"] = student_id
        report_data["created_at"] = created_at

        serialized = json.dumps(report_data)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO progress_reports (id, student_id, created_at, report_data)
                VALUES (?, ?, ?, ?)
            """, (report_id, student_id, created_at, serialized))
            conn.commit()

        logger.info("Saved progress report %s for student %s", report_id, student_id)
        return report_data

    def get_latest_report(self, student_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT report_data FROM progress_reports
                WHERE student_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (student_id,))
            row = cursor.fetchone()
            if not row:
                return None
            try:
                return json.loads(row[0])
            except Exception as e:
                logger.error("Failed to parse progress report JSON: %s", e)
                return None

    def list_reports(self, student_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT report_data FROM progress_reports
                WHERE student_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (student_id, limit))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                try:
                    results.append(json.loads(r[0]))
                except Exception:
                    continue
            return results
