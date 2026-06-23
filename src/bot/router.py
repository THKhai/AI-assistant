from src.core import db
from src.core.query import ask, invalidate_index
from src.core.ingest import ingest_directory
from src.modules.planner import PlannerSession, get_week_status


_active_sessions: dict[int, PlannerSession] = {}


def start_planner_session(user_id: int, session_type: str) -> str:
    session_id = db.new_session_id()
    session = PlannerSession(session_type, session_id)
    _active_sessions[user_id] = session
    return session.start()


def handle_message(user_id: int, text: str) -> str:
    if user_id in _active_sessions:
        session = _active_sessions[user_id]
        response = session.reply(text)
        return response
    return (
        "I'm not in an active session. Use a command to start:\n"
        "/daily — morning planning\n"
        "/evening — evening check-in\n"
        "/weekly — weekly planning\n"
        "/monthly — monthly planning\n"
        "/status — this week's progress\n"
        "/ask <question> — search your knowledge base"
    )


def end_session(user_id: int):
    _active_sessions.pop(user_id, None)


def handle_ask(question: str, user_id: int) -> str:
    session = _active_sessions.get(user_id)
    history = session.history if session else []
    result = ask(question, history)
    answer = result["answer"]
    if result["sources"]:
        answer += "\n\n_Sources: " + ", ".join(result["sources"]) + "_"
    return answer


def handle_ingest() -> str:
    results = ingest_directory()
    invalidate_index()
    lines = [f"*Ingest complete*", f"Indexed: {results['indexed']}  Skipped: {results['skipped']}"]
    if results["errors"]:
        lines.append("Errors:\n" + "\n".join(results["errors"]))
    return "\n".join(lines)


def handle_status() -> str:
    return get_week_status()
