"""Local username/password accounts and cookie-backed sessions."""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional


USERNAME_PATTERN = re.compile(r"^[a-z0-9_][a-z0-9_.-]{2,31}$")


class AuthStore:
    def __init__(self, db_path: str = "backend/data/accounts.db"):
        self.db_path = str(Path(db_path).resolve())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    role TEXT NOT NULL DEFAULT 'student',
                    password_salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    profile_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS ix_auth_sessions_account ON auth_sessions(account_id);
                """
            )
            account_columns = {row[1] for row in connection.execute("PRAGMA table_info(accounts)").fetchall()}
            if "role" not in account_columns:
                connection.execute("ALTER TABLE accounts ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")
        self._ensure_local_admin()

    def _ensure_local_admin(self) -> None:
        """Create the requested local teacher account once without changing it later."""
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT id, role FROM accounts WHERE username = ? COLLATE NOCASE", ("admin",)
            ).fetchone()
            if existing:
                if existing["role"] != "admin":
                    connection.execute(
                        "UPDATE accounts SET role = 'admin', updated_at = ? WHERE id = ?",
                        (self._now().isoformat(), existing["id"]),
                    )
                return
            account_id = uuid.uuid4().hex
            salt = os.urandom(16)
            now = self._now().isoformat()
            profile = self._sanitize_profile({
                "name": "Top Teacher",
                "level": "Administration",
                "study": "Student Progress & Evaluation",
                "theme": "nexus",
            })
            connection.execute(
                """INSERT INTO accounts
                   (id, username, role, password_salt, password_hash, profile_json, created_at, updated_at)
                   VALUES (?, ?, 'admin', ?, ?, ?, ?, ?)""",
                (account_id, "admin", salt, self._password_hash("admin", salt), json.dumps(profile), now, now),
            )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _password_hash(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _public_account(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"] if "role" in row.keys() else "student",
            "profile": json.loads(row["profile_json"] or "{}"),
            "created_at": row["created_at"],
        }

    def create_account(self, username: str, password: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        normalized = username.strip().lower()
        if not USERNAME_PATTERN.fullmatch(normalized):
            raise ValueError("Username must be 3-32 characters using letters, numbers, dots, dashes, or underscores.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not str(profile.get("name", "")).strip():
            raise ValueError("Full name is required.")
        account_id = uuid.uuid4().hex
        salt = os.urandom(16)
        now = self._now().isoformat()
        safe_profile = self._sanitize_profile(profile)
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO accounts (id, username, role, password_salt, password_hash, profile_json, created_at, updated_at) VALUES (?, ?, 'student', ?, ?, ?, ?, ?)",
                    (account_id, normalized, salt, self._password_hash(password, salt), json.dumps(safe_profile), now, now),
                )
                row = connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        except sqlite3.IntegrityError as exc:
            raise ValueError("That username is already in use.") from exc
        return self._public_account(row)

    def verify_credentials(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM accounts WHERE username = ? COLLATE NOCASE", (username.strip(),)).fetchone()
        if not row:
            return None
        candidate = self._password_hash(password, row["password_salt"])
        return self._public_account(row) if hmac.compare_digest(candidate, row["password_hash"]) else None

    def create_session(self, account_id: str, days: int = 30) -> str:
        token = secrets.token_urlsafe(40)
        now = self._now()
        with self._connect() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now.isoformat(),))
            connection.execute(
                "INSERT INTO auth_sessions (token_hash, account_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (self._token_hash(token), account_id, now.isoformat(), (now + timedelta(days=days)).isoformat()),
            )
        return token

    def account_for_token(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """SELECT a.* FROM auth_sessions s JOIN accounts a ON a.id = s.account_id
                   WHERE s.token_hash = ? AND s.expires_at > ?""",
                (self._token_hash(token), self._now().isoformat()),
            ).fetchone()
        return self._public_account(row) if row else None

    def delete_session(self, token: str) -> None:
        if token:
            with self._connect() as connection:
                connection.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (self._token_hash(token),))

    def update_profile(self, account_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        safe_profile = self._sanitize_profile(profile)
        if not safe_profile["name"]:
            raise ValueError("Full name is required.")
        with self._connect() as connection:
            connection.execute(
                "UPDATE accounts SET profile_json = ?, updated_at = ? WHERE id = ?",
                (json.dumps(safe_profile), self._now().isoformat(), account_id),
            )
            row = connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if not row:
            raise ValueError("Account not found.")
        return self._public_account(row)

    def list_accounts(self, role: Optional[str] = None) -> list[Dict[str, Any]]:
        with self._connect() as connection:
            if role:
                rows = connection.execute(
                    "SELECT * FROM accounts WHERE role = ? ORDER BY created_at DESC", (role,)
                ).fetchall()
            else:
                rows = connection.execute("SELECT * FROM accounts ORDER BY created_at DESC").fetchall()
        return [self._public_account(row) for row in rows]

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return self._public_account(row) if row else None

    @staticmethod
    def _sanitize_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
        theme = str(profile.get("theme", "nexus")).strip().lower()
        if theme not in {"nexus", "ocean", "violet", "ember"}:
            theme = "nexus"
        return {
            "name": str(profile.get("name", "")).strip()[:100],
            "email": str(profile.get("email", "")).strip()[:160],
            "level": str(profile.get("level", "College")).strip()[:60],
            "study": str(profile.get("study", "")).strip()[:120],
            "yearOfStudy": str(profile.get("yearOfStudy", "")).strip()[:60],
            "learningGoal": str(profile.get("learningGoal", "")).strip()[:500],
            "theme": theme,
            "pomodoro": profile.get("pomodoro") if isinstance(profile.get("pomodoro"), dict) else {"enabled": True, "studyTime": 25, "breakTime": 5},
            "hydration": profile.get("hydration") if isinstance(profile.get("hydration"), dict) else {"enabled": True, "interval": 45},
        }
