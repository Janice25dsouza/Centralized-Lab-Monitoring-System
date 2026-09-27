
# api/commands.py

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional

from api.logs import record_log


router = APIRouter()


# Store active WebSocket connections
active_connections: dict[str, WebSocket] = {}


# ─────────────────────────────────────────
# Request bodies
# ─────────────────────────────────────────

class CommandRequest(BaseModel):
    client_id: str
    command: str  # "lock" | "unlock" | "shutdown"


class UpdateRulesRequest(BaseModel):
    client_id: Optional[str] = None
    rules: dict  # {"restricted_apps": [...], "restricted_keywords": [...]}


# ─────────────────────────────────────────
# WebSocket — clients connect here
# ─────────────────────────────────────────

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str
):
    await websocket.accept()

    active_connections[client_id] = websocket

    print(f"[+] {client_id} connected")

    try:
        while True:
            data = await websocket.receive_text()

            print(f"[{client_id}] {data}")

            if data.startswith("{") and data.endswith("}"):
                try:
                    log_data = json.loads(data)

                    record_log(
                        client_id,
                        log_data
                    )

                except Exception as e:
                    print(
                        f"[!] Log parse error from "
                        f"{client_id}: {e}"
                    )

    except WebSocketDisconnect:

        print(
            f"[-] {client_id} disconnected"
        )

        active_connections.pop(
            client_id,
            None
        )


# ─────────────────────────────────────────
# Helper — push a command to one client
# ─────────────────────────────────────────

async def _send(
    client_id: str,
    command: str
) -> dict:

    ws = active_connections.get(
        client_id
    )

    # Client is not connected
    if ws is None:
        return {
            "status": "error",
            "detail": f"{client_id} is not connected"
        }

    try:

        # Send command to client
        await ws.send_text(
            command
        )

        return {
            "status": "ok",
            "command": command,
            "client_id": client_id
        }

    except Exception as e:

        print(
            f"[!] Failed to send "
            f"'{command}' to {client_id}: {e}"
        )

        # Remove stale/dead WebSocket
        active_connections.pop(
            client_id,
            None
        )

        return {
            "status": "error",
            "command": command,
            "client_id": client_id,
            "detail": str(e)
        }


# ─────────────────────────────────────────
# POST /send-command
# Generic command endpoint
# ─────────────────────────────────────────

@router.post("/send-command")
async def send_command(
    req: CommandRequest
):

    allowed = {
        "lock",
        "unlock",
        "shutdown"
    }

    if req.command not in allowed:
        return {
            "status": "error",
            "detail": (
                f"Unknown command "
                f"'{req.command}'. "
                f"Allowed: {allowed}"
            ),
        }

    return await _send(
        req.client_id,
        req.command
    )


# ─────────────────────────────────────────
# POST /update-rules
# Push dynamic rules to client(s)
# ─────────────────────────────────────────

@router.post("/update-rules")
async def update_rules_endpoint(
    req: UpdateRulesRequest
):

    payload = {
        "command": "update_rules",
        "rules": req.rules
    }

    payload_str = json.dumps(
        payload
    )

    # Send to one specific client
    if req.client_id:

        ws = active_connections.get(
            req.client_id
        )

        if not ws:
            return {
                "status": "error",
                "detail": (
                    f"{req.client_id} "
                    f"is not connected"
                )
            }

        await ws.send_text(
            payload_str
        )

        return {
            "status": "ok",
            "target": req.client_id
        }

    else:

        # Broadcast to all connected clients
        count = 0

        for cid, ws in list(
            active_connections.items()
        ):

            try:

                await ws.send_text(
                    payload_str
                )

                count += 1

            except Exception as e:

                print(
                    f"[!] Failed to send rules "
                    f"to {cid}: {e}"
                )

        return {
            "status": "ok",
            "broadcast_count": count
        }


# ─────────────────────────────────────────
# Convenience endpoints
# ─────────────────────────────────────────

@router.post("/lock/{client_id}")
async def lock_client(
    client_id: str
):
    """Freeze keyboard and mouse input on the target PC."""

    return await _send(
        client_id,
        "lock"
    )


@router.post("/unlock/{client_id}")
async def unlock_client(
    client_id: str
):
    """Restore keyboard and mouse input on the target PC."""

    return await _send(
        client_id,
        "unlock"
    )


@router.post("/shutdown/{client_id}")
async def shutdown_client(
    client_id: str
):
    """Shut down the target PC."""

    return await _send(
        client_id,
        "shutdown"
    )


# ─────────────────────────────────────────
# GET /connected
# List currently online clients
# ─────────────────────────────────────────

@router.get("/connected")
def get_connected_clients():

    return {
        "connected": list(
            active_connections.keys()
        )
    }


# ─────────────────────────────────────────
# POST /lock-all
# Lock all currently connected PCs
# ─────────────────────────────────────────

@router.post("/lock-all")
async def lock_all_clients():

    """Lock all currently connected PCs."""

    results = []

    for client_id in list(
        active_connections.keys()
    ):

        result = await _send(
            client_id,
            "lock"
        )

        results.append(
            result
        )

    successful = sum(
        1
        for result in results
        if result.get("status") == "ok"
    )

    return {
        "status": "ok",
        "command": "lock",
        "broadcast_count": successful,
        "results": results
    }


# ─────────────────────────────────────────
# POST /shutdown-all
# Shut down all currently connected PCs
# ─────────────────────────────────────────

@router.post("/shutdown-all")
async def shutdown_all_clients():

    """Shut down all currently connected PCs."""

    results = []

    for client_id in list(
        active_connections.keys()
    ):

        result = await _send(
            client_id,
            "shutdown"
        )

        results.append(
            result
        )

    successful = sum(
        1
        for result in results
        if result.get("status") == "ok"
    )

    return {
        "status": "ok",
        "command": "shutdown",
        "broadcast_count": successful,
        "results": results
    }


# ─────────────────────────────────────────
# POST /unlock-all
# Unlock all connected PCs
# ─────────────────────────────────────────

@router.post("/unlock-all")
async def unlock_all_clients():

    """Unlock all currently connected PCs."""

    results = []

    for client_id in list(
        active_connections.keys()
    ):

        result = await _send(
            client_id,
            "unlock"
        )

        results.append(
            result
        )

    successful = sum(
        1
        for result in results
        if result.get("status") == "ok"
    )

    return {
        "status": "ok",
        "command": "unlock",
        "broadcast_count": successful,
        "results": results
    }
