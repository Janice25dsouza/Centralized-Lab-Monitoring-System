import sys
import os
import time
import socket
import asyncio
import threading
import json
import queue
import subprocess
import tkinter as tk

import requests
import websockets
from zeroconf import ServiceBrowser, Zeroconf, ServiceListener


IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"


if IS_WINDOWS:
    try:
        import winreg
        import win32gui
    except ImportError:
        winreg = None
        win32gui = None
else:
    winreg = None
    win32gui = None


# ─────────────────────────────────────────
# PERSISTENT LOCK STATE
# ─────────────────────────────────────────

if IS_WINDOWS:
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    LOCK_FILE = os.path.join(appdata, "client_lock_state.txt")
else:
    LOCK_FILE = os.path.expanduser("~/.client_lock_state.txt")


def save_lock_state(state: bool):
    try:
        with open(LOCK_FILE, "w") as f:
            f.write("1" if state else "0")

    except Exception as e:
        print("[!] Failed to save lock state:", e)


def load_lock_state():
    try:
        with open(LOCK_FILE, "r") as f:
            return f.read().strip() == "1"

    except Exception:
        return False


# ─────────────────────────────────────────
# CONFIG & RULES
# ─────────────────────────────────────────

SERVER_HTTP = None
SERVER_WS = None

# Stable client ID based on computer hostname
client_id = socket.gethostname()


# ─────────────────────────────────────────
# SERVER DISCOVERY
# ─────────────────────────────────────────

SERVICE_TYPE = "_labmonitor._tcp.local."


class LabServerListener(ServiceListener):

    def __init__(self):
        self.server_ip = None
        self.server_port = None
        self.found_event = threading.Event()

    def add_service(self, zeroconf, service_type, name):

        info = zeroconf.get_service_info(
            service_type,
            name
        )

        if info:

            addresses = [
                address
                for address in info.parsed_addresses()
                if ":" not in address
            ]

            if addresses:

                self.server_ip = addresses[0]
                self.server_port = info.port

                self.found_event.set()

    def remove_service(self, zeroconf, service_type, name):
        pass

    def update_service(self, zeroconf, service_type, name):
        self.add_service(
            zeroconf,
            service_type,
            name
        )


def discover_server():

    print("[DISCOVERY] Searching for Lab Monitoring Server...")

    zeroconf = Zeroconf()

    listener = LabServerListener()

    browser = ServiceBrowser(
        zeroconf,
        SERVICE_TYPE,
        listener
    )

    try:

        while not listener.found_event.wait(timeout=1):

            print("[DISCOVERY] Still searching...")

        print("[DISCOVERY] Server found!")

        print(
            f"[DISCOVERY] IP: {listener.server_ip}"
        )

        print(
            f"[DISCOVERY] Port: {listener.server_port}"
        )

        return (
            listener.server_ip,
            listener.server_port
        )

    finally:

        zeroconf.close()


# ─────────────────────────────────────────
# OVERLAY GLOBALS
# ─────────────────────────────────────────

_overlay_root = None
_overlay_thread = None
_overlay_lock = threading.Lock()

lock_event = threading.Event()


if load_lock_state():
    lock_event.set()


# ─────────────────────────────────────────
# RULES
# ─────────────────────────────────────────

RULES_FILE = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "rules.json"
)

rules_lock = threading.Lock()

monitored_rules = {
    "allowed_apps": [],
    "allowed_keywords": []
}


# ─────────────────────────────────────────
# OUTBOUND QUEUE
# ─────────────────────────────────────────

outbound_queue = queue.Queue()


# ─────────────────────────────────────────
# RULE FUNCTIONS
# ─────────────────────────────────────────

def load_rules():

    global monitored_rules

    if os.path.exists(RULES_FILE):

        try:

            with open(
                RULES_FILE,
                "r"
            ) as f:

                data = json.load(f)

            with rules_lock:

                monitored_rules[
                    "allowed_apps"
                ] = [
                    app.lower()
                    for app in data.get(
                        "allowed_apps",
                        []
                    )
                ]

                monitored_rules[
                    "allowed_keywords"
                ] = [
                    kw.lower()
                    for kw in data.get(
                        "allowed_keywords",
                        []
                    )
                ]

            print(
                "[RULES] Loaded whitelist rules from file:",
                monitored_rules
            )

        except Exception as e:

            print(
                "[!] Failed to load rules.json:",
                e
            )


def update_rules(data):

    with rules_lock:

        if "allowed_apps" in data:

            monitored_rules[
                "allowed_apps"
            ] = [
                app.lower()
                for app in data[
                    "allowed_apps"
                ]
            ]

        if "allowed_keywords" in data:

            monitored_rules[
                "allowed_keywords"
            ] = [
                kw.lower()
                for kw in data[
                    "allowed_keywords"
                ]
            ]

    print(
        "[RULES] Dynamic whitelist rules updated from server:",
        monitored_rules
    )


def check_window_against_rules(window_title):

    title_lower = (
        window_title
        .lower()
        .strip()
    )

    if not title_lower:
        return None

    with rules_lock:

        apps = list(
            monitored_rules.get(
                "allowed_apps",
                []
            )
        )

        keywords = list(
            monitored_rules.get(
                "allowed_keywords",
                []
            )
        )

    # Check allowed applications
    for app in apps:

        if app in title_lower:

            return None

    # Check allowed keywords
    for kw in keywords:

        if kw in title_lower:

            return None

    # Not allowed
    return "Unallowed Application/Site"


# ─────────────────────────────────────────
# WEBSOCKET OUTBOUND
# ─────────────────────────────────────────

def send_ws_payload(payload):

    outbound_queue.put(payload)


# ─────────────────────────────────────────
# GET LOCAL IP
# ─────────────────────────────────────────

def get_local_ip():

    s = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    try:

        s.connect(
            ("8.8.8.8", 80)
        )

        ip = s.getsockname()[0]

    finally:

        s.close()

    return ip


# ─────────────────────────────────────────
# CLIENT INFORMATION
# ─────────────────────────────────────────

def get_client_data():

    return {

        "client_id": client_id,

        "hostname": client_id,

        "ip": get_local_ip()

    }


# ─────────────────────────────────────────
# DISCOVER + REGISTER
# ─────────────────────────────────────────
#
# This function:
#
# 1. Discovers the server using Zeroconf
# 2. Builds the HTTP and WebSocket addresses
# 3. Registers this client with the server
#
# It is used both during startup and
# after a reconnect.
# ─────────────────────────────────────────

def discover_and_register():

    global SERVER_HTTP
    global SERVER_WS

    # Discover server
    server_ip, server_port = discover_server()

    # Build server addresses dynamically
    SERVER_HTTP = (
        f"http://{server_ip}:{server_port}/register"
    )

    SERVER_WS = (
        f"ws://{server_ip}:{server_port}/ws"
    )

    print(
        f"[DISCOVERY] HTTP: {SERVER_HTTP}"
    )

    print(
        f"[DISCOVERY] WebSocket: {SERVER_WS}"
    )

    # Register client
    res = requests.post(

        SERVER_HTTP,

        json=get_client_data(),

        timeout=5
    )

    # Raise an error if the server returned
    # a HTTP error status.
    res.raise_for_status()

    print(
        "[+] Registered:",
        res.json()
    )


# ─────────────────────────────────────────
# REGISTER
# ─────────────────────────────────────────
#
# Startup registration.
#
# Keeps retrying until the server is found
# and registration succeeds.
# ─────────────────────────────────────────

def register():

    while True:

        try:

            discover_and_register()

            return

        except Exception as e:

            print(
                "[!] Registration failed:",
                e
            )

            print(
                "[*] Retrying discovery in 5 seconds..."
            )

            time.sleep(5)


# ─────────────────────────────────────────
# TASK MANAGER CONTROL
# ─────────────────────────────────────────

def disable_task_manager():

    if IS_WINDOWS and winreg:

        try:

            key = winreg.CreateKey(

                winreg.HKEY_CURRENT_USER,

                r"Software\Microsoft\Windows"
                r"\CurrentVersion\Policies\System"

            )

            winreg.SetValueEx(

                key,

                "DisableTaskMgr",

                0,

                winreg.REG_DWORD,

                1

            )

            winreg.CloseKey(key)

            print(
                "[*] Task Manager disabled"
            )

        except Exception as e:

            print(
                "[!] Could not disable Task Manager:",
                e
            )


def enable_task_manager():

    if IS_WINDOWS and winreg:

        try:

            key = winreg.CreateKey(

                winreg.HKEY_CURRENT_USER,

                r"Software\Microsoft\Windows"
                r"\CurrentVersion\Policies\System"

            )

            winreg.SetValueEx(

                key,

                "DisableTaskMgr",

                0,

                winreg.REG_DWORD,

                0

            )

            winreg.CloseKey(key)

            print(
                "[*] Task Manager enabled"
            )

        except Exception as e:

            print(
                "[!] Could not enable Task Manager:",
                e
            )


# ─────────────────────────────────────────
# OVERLAY HELPERS
# ─────────────────────────────────────────

def _absorb(event=None):

    return "break"


def _force_focus(root):

    try:

        if root.winfo_exists():

            root.focus_force()

            root.lift()

            root.after(
                200,
                _force_focus,
                root
            )

    except Exception:

        pass


# ─────────────────────────────────────────
# OVERLAY UI
# ─────────────────────────────────────────

def _run_overlay():

    global _overlay_root

    root = tk.Tk()

    with _overlay_lock:

        _overlay_root = root

    root.attributes(
        "-fullscreen",
        True
    )

    root.attributes(
        "-topmost",
        True
    )

    root.configure(
        bg="#0a0a0a"
    )

    frame = tk.Frame(
        root,
        bg="#0a0a0a"
    )

    frame.place(
        relx=0.5,
        rely=0.5,
        anchor="center"
    )

    tk.Label(

        frame,

        text="🔒",

        font=(
            "Segoe UI Emoji",
            72
        ),

        bg="#0a0a0a",

        fg="white"

    ).pack(
        pady=(0, 20)
    )

    tk.Label(

        frame,

        text="Screen Locked",

        font=(
            "Segoe UI",
            38,
            "bold"
        ),

        bg="#0a0a0a",

        fg="white"

    ).pack()

    tk.Label(

        frame,

        text="Please wait for your teacher.",

        font=(
            "Segoe UI",
            16
        ),

        bg="#0a0a0a",

        fg="#888888"

    ).pack(
        pady=(8, 0)
    )

    root.bind_all(
        "<Key>",
        _absorb
    )

    root.bind_all(
        "<Button>",
        _absorb
    )

    for k in [

        "<Alt-F4>",
        "<Alt-Tab>",
        "<Escape>",
        "<Control-Escape>"

    ]:

        root.bind(
            k,
            _absorb
        )

    _force_focus(root)

    print(
        "[LOCK] Overlay started"
    )

    root.mainloop()

    print(
        "[LOCK] Overlay closed"
    )

    with _overlay_lock:

        _overlay_root = None


def show_overlay():

    global _overlay_thread

    with _overlay_lock:

        if _overlay_root is not None:

            print(
                "[LOCK] Overlay already running"
            )

            return

    disable_task_manager()

    print(
        "[LOCK] Starting overlay"
    )

    _overlay_thread = threading.Thread(

        target=_run_overlay,

        daemon=True

    )

    _overlay_thread.start()


def hide_overlay():

    with _overlay_lock:

        root = _overlay_root

    if root is None:

        print(
            "[LOCK] No overlay to hide"
        )

        return

    print(
        "[LOCK] Unlock requested"
    )

    try:

        root.after(
            0,
            root.destroy
        )

    except Exception as e:

        print(
            "[LOCK] Destroy failed:",
            e
        )

    enable_task_manager()


# ─────────────────────────────────────────
# LOCK ENFORCER
# ─────────────────────────────────────────

def lock_enforcer():

    while True:

        time.sleep(1)

        with _overlay_lock:

            overlay_active = (
                _overlay_root is not None
            )

        if (
            lock_event.is_set()
            and not overlay_active
        ):

            time.sleep(0.5)

            print(
                "[LOCK] Overlay missing. Restoring..."
            )

            show_overlay()


# ─────────────────────────────────────────
# ACTIVE WINDOW MONITOR
# ─────────────────────────────────────────

def get_active_app():

    if IS_WINDOWS and win32gui:

        try:

            window = (
                win32gui.GetForegroundWindow()
            )

            return (
                win32gui.GetWindowText(window)
            )

        except Exception:

            return ""

    elif IS_MAC:

        try:

            window_script = '''

            tell application "System Events"

                set frontApp to first process
                whose frontmost is true

                set appName to name of frontApp

                try

                    tell frontApp

                        if (count of windows) > 0 then

                            set winName to name
                            of window 1

                            if winName is not "" then

                                return appName
                                & " - "
                                & winName

                            end if

                        end if

                    end tell

                end try

                return appName

            end tell

            '''

            result = subprocess.run(

                [
                    "osascript",
                    "-e",
                    window_script
                ],

                capture_output=True,

                text=True,

                timeout=2
            )

            return result.stdout.strip()

        except Exception:

            return ""

    return ""


def active_window_monitor():

    last_window = ""

    while True:

        time.sleep(0.5)

        current_window = (
            get_active_app()
        )

        if (
            current_window
            and current_window != last_window
        ):

            print(
                f"[ACTIVE WINDOW] {current_window}"
            )

            last_window = current_window

            # Check against whitelist
            unallowed_reason = (
                check_window_against_rules(
                    current_window
                )
            )

            if unallowed_reason:

                print(
                    "[WARNING LOG] "
                    "Unallowed application/site "
                    f"detected: '{current_window}'"
                )

                warning_payload = {

                    "type": "warning_log",

                    "client_id": client_id,

                    "window": current_window,

                    "matched_rule": unallowed_reason,

                    "timestamp": time.time()

                }

                send_ws_payload(
                    warning_payload
                )


# ─────────────────────────────────────────
# SHUTDOWN
# ─────────────────────────────────────────

def shutdown_system():

    enable_task_manager()

    if IS_WINDOWS:

        os.system(
            "shutdown /s /f /t 3"
        )

    elif IS_MAC:

        os.system(
            "osascript -e "
            "'tell application "
            "\"System Events\" "
            "to shut down'"
        )


# ─────────────────────────────────────────
# COMMAND HANDLER
# ─────────────────────────────────────────

def handle_command(raw_message):

    raw_message = raw_message.strip()

    print(
        "[>] Command received:",
        raw_message
    )

    # Try JSON first
    if (
        raw_message.startswith("{")
        and raw_message.endswith("}")
    ):

        try:

            data = json.loads(
                raw_message
            )

            cmd_type = (
                data
                .get("command", "")
                .lower()
            )

            if cmd_type == "update_rules":

                rules_data = data.get(
                    "rules",
                    data.get(
                        "data",
                        {}
                    )
                )

                update_rules(
                    rules_data
                )

                return

            if cmd_type == "lock":

                raw_message = "lock"

            elif cmd_type == "unlock":

                raw_message = "unlock"

            elif cmd_type == "shutdown":

                raw_message = "shutdown"

        except Exception as e:

            print(
                "[!] JSON command parse error:",
                e
            )

    command = raw_message.lower()

    if command == "lock":

        print(
            "[LOCK] Lock command received"
        )

        lock_event.set()

        save_lock_state(True)

        show_overlay()

    elif command == "unlock":

        print(
            "[LOCK] Unlock command received"
        )

        lock_event.clear()

        save_lock_state(False)

        hide_overlay()

    elif command == "shutdown":

        shutdown_system()

# ─────────────────────────────────────────
# HEARTBEAT
# ─────────────────────────────────────────

HEARTBEAT_INTERVAL = 10


def send_heartbeat():

    while True:

        time.sleep(HEARTBEAT_INTERVAL)

        try:

            if SERVER_HTTP is None:
                continue

            heartbeat_url = (
                SERVER_HTTP.rsplit(
                    "/register",
                    1
                )[0]
                + "/heartbeat"
            )

            response = requests.post(

                heartbeat_url,

                json={
                    "client_id": client_id
                },

                timeout=5
            )

            if response.ok:

                print(
                    "[HEARTBEAT] Server acknowledged heartbeat"
                )

            else:

                print(
                    "[HEARTBEAT] Server rejected heartbeat:",
                    response.text
                )

        except Exception as e:

            print(
                "[HEARTBEAT] Failed:",
                e
            )

# ─────────────────────────────────────────
# WEBSOCKET LISTENER & SENDER
# ─────────────────────────────────────────

async def listen():

    global SERVER_HTTP
    global SERVER_WS

    while True:

        try:

            # If we don't have a server address,
            # discover and register.
            if SERVER_WS is None:

                await asyncio.to_thread(
                    discover_and_register
                )

            uri = (
                f"{SERVER_WS}/{client_id}"
            )

            print(
                f"[*] Connecting to {uri}"
            )

            async with websockets.connect(
                uri
            ) as ws:

                print(
                    "[+] Connected to server"
                )

                # ─────────────────────────
                # RECEIVE LOOP
                # ─────────────────────────

                async def receive_loop():

                    while True:

                        msg = await ws.recv()

                        handle_command(
                            msg
                        )

                # ─────────────────────────
                # SEND LOOP
                # ─────────────────────────

                async def send_loop():

                    while True:

                        while not outbound_queue.empty():

                            item = (
                                outbound_queue
                                .get_nowait()
                            )

                            payload_str = (

                                json.dumps(item)

                                if isinstance(
                                    item,
                                    dict
                                )

                                else str(item)

                            )

                            await ws.send(
                                payload_str
                            )

                        await asyncio.sleep(
                            0.2
                        )

                await asyncio.gather(

                    receive_loop(),

                    send_loop()

                )

        except Exception as e:

            print(
                "[!] WebSocket error:",
                e
            )

            # Clear the old server addresses.
            #
            # This forces the next iteration
            # to rediscover the server.
            SERVER_HTTP = None
            SERVER_WS = None

            print(
                "[*] Server connection lost."
            )

            print(
                "[*] Rediscovering server "
                "and registering again "
                "in 5 seconds..."
            )

            await asyncio.sleep(5)

            try:

                await asyncio.to_thread(
                    discover_and_register
                )

                print(
                    "[+] Re-registration successful."
                )

            except Exception as register_error:

                print(
                    "[!] Re-registration failed:",
                    register_error
                )

                print(
                    "[*] Will retry discovery "
                    "on the next loop."
                )


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":

    # Load local rules
    load_rules()

    # Initial discovery + registration
    register()

    # Start heartbeat
    threading.Thread(
        target=send_heartbeat,
        daemon=True
    ).start()

    # Start lock monitoring
    threading.Thread(
        target=lock_enforcer,
        daemon=True
    ).start()

    # Start active-window monitoring
    threading.Thread(
        target=active_window_monitor,
        daemon=True
    ).start()

    # Restore locked state
    if lock_event.is_set():

        print(
            "[*] Restoring locked state after startup"
        )

        show_overlay()

    # Start WebSocket connection
    asyncio.run(
        listen()
    )