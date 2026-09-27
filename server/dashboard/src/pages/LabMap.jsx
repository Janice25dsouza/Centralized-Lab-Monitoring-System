import { useEffect, useState } from "react";
import api from "../services/api";
import "../styles/LabMap.css";

function LabMap() {
    const [config, setConfig] = useState(null);
    const [clients, setClients] = useState({});
    const [warnings, setWarnings] = useState({});

    const loadData = async () => {
        try {
            const [
                configResponse,
                clientsResponse,
                warningsResponse
            ] = await Promise.all([
                api.get("/lab-config"),
                api.get("/clients"),
                api.get("/logs/warnings")
            ]);

            setConfig(configResponse.data);
            setClients(clientsResponse.data);
            setWarnings(warningsResponse.data);
        } catch (error) {
            console.error(
                "Failed to load lab map data:",
                error
            );
        }
    };

    useEffect(() => {
        loadData();

        const interval = setInterval(() => {
            loadData();
        }, 5000);

        return () => clearInterval(interval);
    }, []);

    if (!config) {
        return (
            <div className="dashboard-container">
                Loading lab map...
            </div>
        );
    }

    const getPCAtPosition = (row, column) => {
        return config.pcs.find(
            (pc) =>
                pc.row === row &&
                pc.column === column
        );
    };

    const hasViolation = (clientId) => {
    const clientWarnings =
        warnings[clientId] || [];

    return clientWarnings.length > 0;
    };

    return (
        <div className="dashboard-container">

            <header className="dashboard-header">
                <div className="dashboard-title">
                    <h1>Workstation Floor Map</h1>
                    <div className="dashboard-subtitle">
                        Interactive visual grid status of student computer positions
                    </div>
                </div>
            </header>

            {/* Status legend */}
            <div
                style={{
                    display: "flex",
                    gap: "25px",
                    marginTop: "20px",
                    marginBottom: "20px",
                    flexWrap: "wrap"
                }}
            >
                <span>🟢 Online</span>
                <span>⚪ Offline</span>
                <span>🔴 Recent Violation</span>
            </div>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns:
                        `repeat(${config.lab.columns}, 1fr)`,
                    gap: "15px",
                    marginTop: "30px"
                }}
            >
                {Array.from(
                    {
                        length:
                            config.lab.rows *
                            config.lab.columns
                    },
                    (_, index) => {

                        const row =
                            Math.floor(
                                index /
                                config.lab.columns
                            ) + 1;

                        const column =
                            (index %
                                config.lab.columns) + 1;

                        const pc =
                            getPCAtPosition(
                                row,
                                column
                            );

                        // Empty position
                        if (!pc) {
                            return (
                                <div
                                    key={`${row}-${column}`}
                                    style={{
                                        minHeight: "100px",
                                        borderRadius: "10px",
                                        border:
                                            "1px solid #333",
                                        display: "flex",
                                        alignItems:
                                            "center",
                                        justifyContent:
                                            "center",
                                        color: "#777"
                                    }}
                                >
                                    Empty
                                </div>
                            );
                        }

                        const client =
                            clients[pc.client_id];

                        const isOnline =
                            client?.online === true;

                        const violation =
                            isOnline &&
                            hasViolation(
                                pc.client_id
                            );

                        let background;
                        let border;
                        let status;
                        let icon;

                        if (violation) {
                            background = "#5a1515";
                            border =
                                "2px solid #ef4444";
                            status = "Violation";
                            icon = "🔴";
                        } else if (isOnline) {
                            background = "#164d2a";
                            border =
                                "2px solid #22c55e";
                            status = "Online";
                            icon = "🟢";
                        } else {
                            background = "#444";
                            border =
                                "2px solid #777";
                            status = "Offline";
                            icon = "⚪";
                        }

                        return (
                            <div
                                key={`${row}-${column}`}
                                style={{
                                    minHeight: "100px",
                                    borderRadius: "10px",
                                    padding: "15px",
                                    background,
                                    border,
                                    display: "flex",
                                    flexDirection:
                                        "column",
                                    alignItems:
                                        "center",
                                    justifyContent:
                                        "center"
                                }}
                            >
                                <div
                                    style={{
                                        fontSize: "30px"
                                    }}
                                >
                                    {icon}
                                </div>

                                <strong>
                                    {pc.pc_name}
                                </strong>

                                <small>
                                    {status}
                                </small>

                                {violation && (
                                    <small
                                        style={{
                                            marginTop:
                                                "5px",
                                            color:
                                                "#ffb4b4"
                                        }}
                                    >
                                        Recent warning
                                    </small>
                                )}
                            </div>
                        );
                    }
                )}
            </div>
        </div>
    );
}

export default LabMap;