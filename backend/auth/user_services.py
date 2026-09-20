"""Request-scoped local persistence services for authenticated accounts."""

import threading
from contextvars import ContextVar
from pathlib import Path

from backend.memory.chat_memory import ChatMemory
from backend.memory.learner_memory import LearnerMemory
from backend.memory.progress_memory import ProgressMemory
from backend.memory.revision_memory import RevisionMemory
from backend.memory.schedule_memory import ScheduleMemory
from backend.memory.syllabus_memory import SyllabusMemory
from backend.memory.test_memory import TestMemory


current_account = ContextVar("edunexus_current_account", default=None)


class UserServices:
    def __init__(self, account_id: str, base_dir: str = "backend/data/users"):
        safe_id = account_id if account_id == "__legacy__" else "".join(c for c in account_id if c.isalnum() or c in "_-")
        if safe_id == "__legacy__":
            root = Path("backend/data")
        else:
            root = Path(base_dir) / safe_id
        root.mkdir(parents=True, exist_ok=True)
        self.root = root.resolve()
        self.db_path = str((self.root / "edunexus.db").resolve())
        self.upload_dir = str((self.root / "uploads").resolve())
        self.media_dir = str((self.root / "generated").resolve())
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.media_dir).mkdir(parents=True, exist_ok=True)
        self._instances = {}
        self._instance_lock = threading.Lock()

    def _get(self, name, factory):
        with self._instance_lock:
            if name not in self._instances:
                self._instances[name] = factory()
            return self._instances[name]

    @property
    def learner_memory(self): return self._get("learner", lambda: LearnerMemory(self.db_path))

    @property
    def chat_memory(self): return self._get("chat", lambda: ChatMemory(self.db_path))

    @property
    def syllabus_memory(self): return self._get("syllabus", lambda: SyllabusMemory(persist_dir=str((self.root / "syllabus").resolve())))

    @property
    def revision_memory(self): return self._get("revision", lambda: RevisionMemory(self.db_path))

    @property
    def test_memory(self): return self._get("test", lambda: TestMemory(self.db_path))

    @property
    def schedule_memory(self): return self._get("schedule", lambda: ScheduleMemory(self.db_path))

    @property
    def progress_memory(self): return self._get("progress", lambda: ProgressMemory(self.db_path))


_services = {}
_lock = threading.Lock()


def services_for(account_id: str) -> UserServices:
    with _lock:
        if account_id not in _services:
            _services[account_id] = UserServices(account_id)
        return _services[account_id]


def current_services() -> UserServices:
    account = current_account.get()
    return services_for(account["id"] if account else "__legacy__")


def current_account_id() -> str:
    account = current_account.get()
    return account["id"] if account else "student_1"


class ServiceProxy:
    def __init__(self, name: str):
        self.name = name

    def __getattr__(self, attribute):
        return getattr(getattr(current_services(), self.name), attribute)
