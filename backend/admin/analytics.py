"""Read-only aggregation of isolated student databases for the admin dashboard."""

from datetime import datetime
from typing import Any, Dict, Iterable, List


def _score_percent(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(score * 100 if score <= 1 else score, 1)


def _latest_timestamp(values: Iterable[Any]) -> str:
    cleaned = [str(value) for value in values if value]
    return max(cleaned, default="")


def _date_part(value: str) -> str:
    if not value:
        return "Not recorded"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return value[:10]


def _time_part(value: str) -> str:
    if not value:
        return "Not recorded"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%I:%M %p")
    except ValueError:
        return value[11:16] or "Not recorded"


def _prior_knowledge(profile: Dict[str, Any]) -> str:
    explicit = str(profile.get("priorKnowledge", "")).strip()
    if explicit:
        return explicit
    level = str(profile.get("level", "")).lower()
    if level in {"university", "professional"}:
        return "Advanced"
    if level == "college":
        return "Intermediate"
    return "Beginner"


def build_student_snapshot(account: Dict[str, Any], services) -> Dict[str, Any]:
    student_id = account["id"]
    profile = account.get("profile") or {}
    learner = services.learner_memory.get_learner_summary(student_id)
    chats = services.chat_memory.list_sessions(student_id)
    revisions = services.revision_memory.list_sessions(student_id)
    tests = services.test_memory.list_sessions(student_id)
    schedules = services.schedule_memory.list_schedules(student_id)

    completed_tests = [item for item in tests if item.get("status") == "COMPLETED" and item.get("score") is not None]
    score_values = [_score_percent(item.get("score")) for item in completed_tests]
    average_score = round(sum(score_values) / len(score_values), 1) if score_values else 0.0
    passed_tests = sum(1 for item in completed_tests if item.get("passed"))
    pass_rate = round((passed_tests / len(completed_tests)) * 100, 1) if completed_tests else 0.0

    latest_test = tests[0] if tests else None
    latest_test_detail = services.test_memory.get_session(latest_test["id"]) if latest_test else None
    latest_chat = chats[0] if chats else None
    latest_revision = revisions[0] if revisions else None
    questions = (latest_test_detail or {}).get("questions") or []
    concepts = []
    for question in questions:
        concept = str(question.get("sub_concept") or question.get("concept") or "").strip()
        if concept and concept not in concepts:
            concepts.append(concept)

    attachment_names: List[str] = []
    for chat in chats[:5]:
        if not chat.get("attachment_count"):
            continue
        session = services.chat_memory.get_session(chat["id"]) or {}
        for attachment in session.get("attachments", []):
            name = attachment.get("display_name")
            if name and name not in attachment_names:
                attachment_names.append(name)

    latest_activity = _latest_timestamp([
        account.get("created_at"),
        *[item.get("updated_at") for item in chats],
        *[item.get("updated_at") for item in revisions],
        *[item.get("updated_at") for item in tests],
        *[item.get("created_at") for item in schedules],
    ])
    topics = learner.get("topics") or []
    activity_count = len(chats) + len(revisions) + len(tests)
    if completed_tests and average_score < 60:
        standing = "Needs attention"
    elif completed_tests and average_score >= 80:
        standing = "Excelling"
    elif activity_count:
        standing = "On track"
    else:
        standing = "Not started"

    latest_topic = (latest_test or {}).get("topic") or (latest_chat or {}).get("title") or (topics[0] if topics else "Not recorded")
    material = (latest_test or {}).get("document_name") or (", ".join(attachment_names[:3]) if attachment_names else "General learning workspace")
    course_year = " / ".join(filter(None, [profile.get("study"), profile.get("yearOfStudy")])) or "Not recorded"

    return {
        "id": student_id,
        "username": account.get("username", ""),
        "name": profile.get("name") or account.get("username", "Student"),
        "email": profile.get("email", ""),
        "level": profile.get("level", "Not recorded"),
        "course_year": course_year,
        "learning_goal": profile.get("learningGoal", ""),
        "joined_at": account.get("created_at", ""),
        "last_activity": latest_activity,
        "standing": standing,
        "progress": {
            "topics": learner.get("topics_count", len(topics)),
            "topic_names": topics,
            "chat_sessions": len(chats),
            "revision_sessions": len(revisions),
            "tests": len(tests),
            "completed_tests": len(completed_tests),
            "average_score": average_score,
            "pass_rate": pass_rate,
            "mastered": learner.get("mastered_subconcepts_count", 0),
            "weak": learner.get("weak_subconcepts_count", 0),
            "misconceptions": learner.get("active_misconceptions_count", 0),
            "scheduled": len(schedules),
        },
        "walkthrough": {
            "test_number": (latest_test or {}).get("test_number") or "—",
            "date": _date_part((latest_test or {}).get("created_at", "")),
            "start_time": _time_part((latest_test or {}).get("created_at", "")),
            "end_time": _time_part((latest_test or {}).get("updated_at", "")) if (latest_test or {}).get("status") == "COMPLETED" else "In progress" if latest_test else "Not recorded",
            "tester_name": profile.get("name") or account.get("username", "Student"),
            "tester_type": "Student",
            "course_year": course_year,
            "prior_knowledge": _prior_knowledge(profile),
            "learning_material": material,
            "topic_selected": latest_topic,
            "concept_being_tested": ", ".join(concepts[:3]) or latest_topic,
            "facilitator": "Top Teacher",
            "observer": "Not assigned",
            "technical_monitor": "Not assigned",
        },
        "recent_tests": tests[:5],
        "recent_revisions": revisions[:5],
    }


def build_admin_overview(accounts: List[Dict[str, Any]], service_factory) -> Dict[str, Any]:
    students = [build_student_snapshot(account, service_factory(account["id"])) for account in accounts]
    active = sum(1 for student in students if student["standing"] != "Not started")
    completed_scores = [student["progress"]["average_score"] for student in students if student["progress"]["completed_tests"]]
    return {
        "summary": {
            "total_students": len(students),
            "active_students": active,
            "average_score": round(sum(completed_scores) / len(completed_scores), 1) if completed_scores else 0,
            "needs_attention": sum(1 for student in students if student["standing"] == "Needs attention"),
            "tests_completed": sum(student["progress"]["completed_tests"] for student in students),
            "topics_explored": sum(student["progress"]["topics"] for student in students),
        },
        "students": students,
        "generated_at": datetime.now().astimezone().isoformat(),
    }
