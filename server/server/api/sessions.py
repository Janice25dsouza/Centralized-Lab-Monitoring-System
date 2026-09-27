# api/sessions.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import List, Dict, Any
import json
import time
import uuid
import threading


router = APIRouter(
    prefix="/sessions",
    tags=["lab sessions"]
)


# ============================================================
# Persistent session storage
# ============================================================

SESSION_FILE = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "lab_sessions.json"
)

SESSION_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

file_lock = threading.Lock()


# ============================================================
# Load sessions
# ============================================================

def load_sessions() -> List[Dict[str, Any]]:
    if not SESSION_FILE.exists():
        return []

    try:
        with open(
            SESSION_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):
            return data.get("sessions", [])

        return []

    except (json.JSONDecodeError, OSError):

        print(
            "[SESSIONS] Could not read lab_sessions.json"
        )

        return []


# ============================================================
# Save sessions
# ============================================================

def save_sessions(
    sessions: List[Dict[str, Any]]
):
    with file_lock:

        temp_file = SESSION_FILE.with_suffix(".tmp")

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {"sessions": sessions},
                file,
                indent=4
            )

        temp_file.replace(SESSION_FILE)


# ============================================================
# Find active session
# ============================================================

def find_active_session():
    """
    Find the currently active lab session.

    This function loads the current session list
    and returns the active session.
    """

    sessions = load_sessions()

    return next(
        (
            session
            for session in sessions
            if session.get("status") == "active"
        ),
        None
    )


# ============================================================
# Request model
# ============================================================

class StartSessionRequest(BaseModel):
    lab_name: str


# ============================================================
# Start session
# ============================================================

@router.post("/start")
def start_session(
    data: StartSessionRequest
):

    sessions = load_sessions()

    # IMPORTANT:
    # Search the SAME list that we are going to save.

    active_session = next(
        (
            session
            for session in sessions
            if session.get("status") == "active"
        ),
        None
    )

    if active_session:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "A lab session is already active.",
                "session": active_session
            }
        )

    now = time.time()

    session = {
        "session_id": str(uuid.uuid4()),
        "lab_name": data.lab_name,
        "start_time": now,
        "end_time": None,
        "status": "active"
    }

    sessions.append(session)

    save_sessions(sessions)

    print(
        f"[SESSION] Started: "
        f"{data.lab_name} "
        f"({session['session_id']})"
    )

    return session


# ============================================================
# End session
# ============================================================

@router.post("/end")
def end_session():

    # Load the sessions ONCE.
    sessions = load_sessions()

    # Find the active session INSIDE this same list.
    active_session = next(
        (
            session
            for session in sessions
            if session.get("status") == "active"
        ),
        None
    )

    if active_session is None:

        raise HTTPException(
            status_code=404,
            detail="No active lab session."
        )

    # Update the object that belongs to `sessions`.
    active_session["end_time"] = time.time()
    active_session["status"] = "completed"

    # Save the SAME list we modified.
    save_sessions(sessions)

    print(
        f"[SESSION] Ended: "
        f"{active_session['session_id']}"
    )

    return active_session


# ============================================================
# Get active session
# ============================================================

@router.get("/active")
def get_active_session():

    return find_active_session()


# ============================================================
# Get all sessions
# ============================================================

@router.get("")
def get_sessions():

    sessions = load_sessions()

    # Newest first
    sessions.reverse()

    return sessions


# ============================================================
# Get specific session
# ============================================================

@router.get("/{session_id}")
def get_session(
    session_id: str
):

    sessions = load_sessions()

    session = next(
        (
            session
            for session in sessions
            if session.get("session_id") == session_id
        ),
        None
    )

    if session is None:

        raise HTTPException(
            status_code=404,
            detail="Session not found."
        )

    return session