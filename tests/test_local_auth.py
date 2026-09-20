from pathlib import Path

from backend.auth.store import AuthStore
from backend.auth.user_services import UserServices


def test_account_passwords_are_hashed_and_sessions_resolve(tmp_path):
    store = AuthStore(str(tmp_path / "accounts.db"))
    account = store.create_account("alice_student", "correct-horse", {"name": "Alice", "level": "College", "theme": "violet"})

    assert store.verify_credentials("alice_student", "wrong-password") is None
    assert store.verify_credentials("ALICE_STUDENT", "correct-horse")["id"] == account["id"]

    token = store.create_session(account["id"])
    assert store.account_for_token(token)["profile"]["name"] == "Alice"
    assert store.account_for_token(token)["profile"]["theme"] == "violet"
    updated = store.update_profile(account["id"], {"name": "Alice", "theme": "ember"})
    assert updated["profile"]["theme"] == "ember"
    store.delete_session(token)
    assert store.account_for_token(token) is None


def test_local_admin_is_bootstrapped_with_admin_role(tmp_path):
    store = AuthStore(str(tmp_path / "accounts.db"))

    admin = store.verify_credentials("admin", "admin")

    assert admin is not None
    assert admin["role"] == "admin"
    assert admin["profile"]["name"] == "Top Teacher"


def test_duplicate_usernames_are_rejected_case_insensitively(tmp_path):
    store = AuthStore(str(tmp_path / "accounts.db"))
    store.create_account("learner_one", "password-123", {"name": "One"})
    try:
        store.create_account("LEARNER_ONE", "password-456", {"name": "Two"})
        assert False, "duplicate username should fail"
    except ValueError as error:
        assert "already in use" in str(error)


def test_each_account_gets_an_isolated_sqlite_database(tmp_path):
    first = UserServices("account_a", str(tmp_path / "users"))
    second = UserServices("account_b", str(tmp_path / "users"))
    first.chat_memory.create_session("account_a", "Algorithms", "First user's lesson")
    second.chat_memory.create_session("account_b", "Biology", "Second user's lesson")

    assert Path(first.db_path).is_file()
    assert Path(second.db_path).is_file()
    assert first.db_path != second.db_path
    assert [session["title"] for session in first.chat_memory.list_sessions("account_a")] == ["Algorithms"]
    assert [session["title"] for session in second.chat_memory.list_sessions("account_b")] == ["Biology"]
    assert first.chat_memory.list_sessions("account_b") == []


def test_auth_api_scopes_learning_data_to_the_signed_in_account(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import backend.auth.user_services as user_services_module
    import server

    store = AuthStore(str(tmp_path / "accounts.db"))
    service_cache = {}

    def temporary_services(account_id):
        if account_id not in service_cache:
            service_cache[account_id] = UserServices(account_id, str(tmp_path / "users"))
        return service_cache[account_id]

    monkeypatch.setattr(server, "auth_store", store)
    monkeypatch.setattr(server, "services_for", temporary_services)
    monkeypatch.setattr(user_services_module, "services_for", temporary_services)

    with TestClient(server.app) as client:
        assert client.get("/api/learner/anything").status_code == 401

        first = client.post("/api/auth/register", json={
            "username": "first_user", "password": "password-123", "name": "First Student",
            "level": "College", "study": "Computer Science",
        })
        assert first.status_code == 201
        first_id = first.json()["account"]["id"]
        created = client.post("/api/learn/sessions", json={
            "student_id": "attempted-spoof", "title": "Private algorithms", "description": "Only the first user sees this",
        })
        assert created.status_code == 201
        session_id = created.json()["id"]
        assert created.json()["student_id"] == first_id
        client.post("/api/auth/logout")

        second = client.post("/api/auth/register", json={
            "username": "second_user", "password": "password-456", "name": "Second Student",
            "level": "School", "study": "Biology",
        })
        assert second.status_code == 201
        assert client.get("/api/learn/sessions/not-the-current-id").json()["sessions"] == []
        assert client.get(f"/api/learn/session/{session_id}").status_code == 404


def test_admin_overview_is_protected_and_contains_walkthrough_fields(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import backend.auth.user_services as user_services_module
    import server

    store = AuthStore(str(tmp_path / "accounts.db"))
    service_cache = {}

    def temporary_services(account_id):
        if account_id not in service_cache:
            service_cache[account_id] = UserServices(account_id, str(tmp_path / "users"))
        return service_cache[account_id]

    monkeypatch.setattr(server, "auth_store", store)
    monkeypatch.setattr(server, "services_for", temporary_services)
    monkeypatch.setattr(user_services_module, "services_for", temporary_services)

    with TestClient(server.app) as client:
        registered = client.post("/api/auth/register", json={
            "username": "dashboard_student", "password": "password-123", "name": "Dashboard Student",
            "level": "College", "study": "Computer Science", "year_of_study": "2nd Year",
        })
        assert registered.status_code == 201
        assert registered.json()["account"]["role"] == "student"
        assert client.get("/api/admin/overview").status_code == 403

        client.post("/api/auth/logout")
        login = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        assert login.status_code == 200
        assert login.json()["account"]["role"] == "admin"

        overview = client.get("/api/admin/overview")
        assert overview.status_code == 200
        payload = overview.json()
        assert payload["summary"]["total_students"] == 1
        student = payload["students"][0]
        assert student["username"] == "dashboard_student"
        assert student["walkthrough"]["tester_name"] == "Dashboard Student"
        assert student["walkthrough"]["tester_type"] == "Student"
        assert student["walkthrough"]["course_year"] == "Computer Science / 2nd Year"
        assert "technical_monitor" in student["walkthrough"]
