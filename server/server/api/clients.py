# client registration, heartbeat, and management

from fastapi import APIRouter
from pydantic import BaseModel
import time


router = APIRouter()

clients = {}


class Client(BaseModel):
    client_id: str
    hostname: str
    ip: str


class Heartbeat(BaseModel):
    client_id: str


# A client is considered offline if we haven't
# received a heartbeat for this many seconds.
CLIENT_TIMEOUT = 30


# ─────────────────────────────────────────
# REGISTER CLIENT
# ─────────────────────────────────────────

@router.post("/register")
def register_client(client: Client):

    clients[client.client_id] = {
        "client_id": client.client_id,
        "hostname": client.hostname,
        "ip": client.ip,
        "last_seen": time.time()
    }

    print(
        f"[REGISTER] Client registered: "
        f"{client.client_id} ({client.ip})"
    )

    return {
        "status": "registered"
    }


# ─────────────────────────────────────────
# HEARTBEAT
# ─────────────────────────────────────────

@router.post("/heartbeat")
def heartbeat(data: Heartbeat):

    client = clients.get(data.client_id)

    if client is None:

        return {
            "status": "error",
            "message": "Client is not registered."
        }

    client["last_seen"] = time.time()

    print(
        f"[HEARTBEAT] {data.client_id}"
    )

    return {
        "status": "ok"
    }


# ─────────────────────────────────────────
# GET CLIENTS
# ─────────────────────────────────────────

@router.get("/clients")
def get_clients():

    current_time = time.time()

    result = {}

    for client_id, client in clients.items():

        last_seen = client.get(
            "last_seen",
            0
        )

        online = (
            current_time - last_seen
        ) <= CLIENT_TIMEOUT

        result[client_id] = {
            "client_id": client["client_id"],
            "hostname": client["hostname"],
            "ip": client["ip"],
            "online": online,
            "last_seen": last_seen
        }

    return result