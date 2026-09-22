import uuid

# In-memory only — resets when the server restarts. Fine for a learning app;
# a real deployment would back this with Postgres or Redis instead.
_sessions: dict[str, list[dict]] = {}


def create_session() -> str:
    session_id = uuid.uuid4().hex
    _sessions[session_id] = []
    return session_id


def get_history(session_id: str) -> list[dict]:
    return _sessions.get(session_id, [])


def append_turn(session_id: str, role: str, content: str):
    _sessions.setdefault(session_id, []).append({
        "role": role,
        "content": content,
    })
