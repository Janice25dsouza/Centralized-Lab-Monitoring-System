import socket

from zeroconf import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf


SERVICE_TYPE = "_labmonitor._tcp.local."
SERVICE_NAME = "Lab Monitoring Server._labmonitor._tcp.local."
PORT = 8000

zeroconf = None
service_info = None


def get_local_ip():
    """
    Find the IP address of this server on the local network.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # This does not actually send data.
        # It allows the OS to determine the active network interface.
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
    finally:
        sock.close()

    return ip


async def start_discovery():
    global zeroconf, service_info

    ip = get_local_ip()

    service_info = ServiceInfo(
        SERVICE_TYPE,
        SERVICE_NAME,
        addresses=[socket.inet_aton(ip)],
        port=PORT,
        properties={
            "server": "lab-monitoring-server",
            "version": "1.0",
        },
    )

    zeroconf = AsyncZeroconf()

    await zeroconf.async_register_service(service_info)

    print("-----------------------------------")
    print("Lab Monitoring Server discovered!")
    print(f"Server IP: {ip}")
    print(f"Server Port: {PORT}")
    print(f"Service: {SERVICE_TYPE}")
    print("-----------------------------------")


async def stop_discovery():
    global zeroconf

    if zeroconf:
        await zeroconf.async_close()
        zeroconf = None

        print("Lab Monitoring Server discovery stopped.")