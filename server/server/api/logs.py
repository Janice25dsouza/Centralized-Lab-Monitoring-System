# api/logs.py

from fastapi import APIRouter
from typing import Dict, List, Any
from pathlib import Path
import json
import uuid
import threading
import time

from api.sessions import find_active_session

router = APIRouter(prefix="/logs", tags=["logs"])


# ============================================================
# Persistent warning history
# ============================================================

HISTORY_FILE = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "warning_history.json"
)

HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

file_lock = threading.Lock()


def load_warning_history() -> List[Dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data.get("events", [])

        return []

    except (json.JSONDecodeError, OSError):
        print("[WARNING] Could not read warning_history.json")
        return []


def save_warning_history(events: List[Dict[str, Any]]):
    with file_lock:
        temp_file = HISTORY_FILE.with_suffix(".tmp")

        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(
                {"events": events},
                file,
                indent=4
            )

        temp_file.replace(HISTORY_FILE)


# ============================================================
# Active warnings
#
# These are the warnings currently shown on Dashboard/Lab Map.
# Clearing them does NOT delete historical records.
# ============================================================

warning_logs_by_client: Dict[str, List[Dict[str, Any]]] = {}

all_warning_logs: List[Dict[str, Any]] = []


# ============================================================
# Load history when server starts
# ============================================================

persistent_warning_history = load_warning_history()

print(
    f"[LOGS] Loaded "
    f"{len(persistent_warning_history)} historical warning(s)"
)


# ============================================================
# Record warning
# ============================================================

def record_log(client_id: str, log_data: dict):

    log_type = log_data.get("type")

    if log_type != "warning_log":
        return

    # --------------------------------------------------------
    # Server timestamp
    # --------------------------------------------------------

    recorded_at = time.time()

    # --------------------------------------------------------
    # Find currently active lab session
    # --------------------------------------------------------

    active_session = find_active_session()

    session_id = None
    session_lab_name = None

    if active_session:
        session_id = active_session.get("session_id")
        session_lab_name = active_session.get("lab_name")

    # --------------------------------------------------------
    # Create warning entry
    # --------------------------------------------------------

    log_entry = {
        "id": str(uuid.uuid4()),

        "client_id": client_id,

        "type": log_type,

        "window": log_data.get("window"),

        "matched_rule": log_data.get(
            "matched_rule",
            "Unallowed Application"
        ),

        # Original timestamp supplied by client
        "timestamp": log_data.get("timestamp"),

        # Reliable server-side timestamp
        "recorded_at": recorded_at,

        # Lab session information
        "session_id": session_id,

        "session_lab_name": session_lab_name
    }

    # ========================================================
    # Active warning memory
    # ========================================================

    if client_id not in warning_logs_by_client:
        warning_logs_by_client[client_id] = []

    warning_logs_by_client[client_id].append(log_entry)

    all_warning_logs.append(log_entry)

    # ========================================================
    # Persistent history
    # ========================================================

    history = load_warning_history()

    history.append(log_entry)

    try:

        save_warning_history(history)

        print(
            f"[LOG] Warning saved permanently: "
            f"{client_id} | "
            f"{log_entry['matched_rule']} | "
            f"session={session_id}"
        )

    except OSError as e:

        print(
            f"[ERROR] Failed to save warning history: {e}"
        )


# ============================================================
# Active warnings
# ============================================================

@router.get("/warnings")
def get_warning_logs():

    return warning_logs_by_client


@router.get("/warnings/{client_id}")
def get_client_warning_logs(client_id: str):

    return warning_logs_by_client.get(client_id, [])


# ============================================================
# Clear active warnings for one PC
#
# IMPORTANT:
# Historical warnings remain untouched.
# ============================================================

@router.delete("/warnings/{client_id}")
def clear_client_warning_logs(client_id: str):

    if client_id in warning_logs_by_client:
        warning_logs_by_client[client_id] = []

    return {
        "status": "ok",
        "cleared": client_id,
        "history_preserved": True
    }


# ============================================================
# Clear all active warnings
#
# IMPORTANT:
# Historical warnings remain untouched.
# ============================================================

@router.delete("/warnings")
def clear_all_warning_logs():

    warning_logs_by_client.clear()
    all_warning_logs.clear()

    return {
        "status": "ok",
        "message": "All active warning logs cleared",
        "history_preserved": True
    }


# ============================================================
# Historical warning history
# ============================================================

@router.get("/history")
def get_warning_history():

    return {
        "events": load_warning_history()
    }


# ============================================================
# Historical warnings for a specific session
# ============================================================

@router.get("/history/session/{session_id}")
def get_session_warning_history(session_id: str):

    history = load_warning_history()

    events = [
        event
        for event in history
        if event.get("session_id") == session_id
    ]

    return {
        "session_id": session_id,
        "events": events,
        "count": len(events)
    }