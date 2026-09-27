from zeroconf import ServiceBrowser, Zeroconf, ServiceListener


SERVICE_TYPE = "_labmonitor._tcp.local."


class LabServerListener(ServiceListener):

    def add_service(self, zeroconf, service_type, name):
        info = zeroconf.get_service_info(service_type, name)

        if info:
            addresses = [
                address for address in info.parsed_addresses()
                if ":" not in address
            ]

            print("\n===================================")
            print("Lab Monitoring Server FOUND!")
            print(f"Name: {name}")
            print(f"IP: {addresses}")
            print(f"Port: {info.port}")
            print("===================================\n")


zeroconf = Zeroconf()

print("Searching for Lab Monitoring Server...")
print("Press Ctrl+C to stop.\n")

listener = LabServerListener()

browser = ServiceBrowser(
    zeroconf,
    SERVICE_TYPE,
    listener
)

try:
    while True:
        pass

except KeyboardInterrupt:
    print("\nStopping discovery...")

finally:
    zeroconf.close()