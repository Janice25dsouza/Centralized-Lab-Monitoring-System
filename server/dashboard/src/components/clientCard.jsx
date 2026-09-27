import api from "../services/api";
import "./ClientCard.css";

export default function ClientCard({ client, warningLogs = [], onClearWarnings }) {

    async function sendCommand(command) {

        try {

            await api.post(`/${command}/${client.client_id}`);

        } catch (err) {

            console.error("Failed to send command:", err);

            alert(`Failed to send ${command} command.`);

        }

    }

    async function handleClear() {

        try {

            await api.delete(`/logs/warnings/${client.client_id}`);

            if (onClearWarnings) {

                onClearWarnings(client.client_id);

            }

        } catch (err) {

            console.error("Failed to clear warnings:", err);

        }

    }

    function formatTime(timestamp) {

        if (!timestamp) return "";

        const date = new Date(timestamp * 1000);

        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    }

    const hasWarnings = warningLogs.length > 0;

    return (

        <div className={`client-card ${hasWarnings ? 'has-warnings' : ''}`}>

            <div className="card-header">

                <div className="client-info">

                    <h3>{client.hostname || client.client_id}</h3>

                    <div className="client-ip">{client.ip}</div>

                </div>

                <div className={`status-badge ${hasWarnings ? 'status-alert' : 'status-online'}`}>

                    <span className="status-dot" aria-hidden="true"></span>

                    {hasWarnings ? `${warningLogs.length} Alert${warningLogs.length > 1 ? 's' : ''}` : 'Connected'}

                </div>

            </div>

            <div className="actions-group">

                <button className="btn btn-lock" onClick={() => sendCommand("lock")}>

                    Lock

                </button>

                <button className="btn btn-unlock" onClick={() => sendCommand("unlock")}>

                    Unlock

                </button>

                <button className="btn btn-shutdown" onClick={() => sendCommand("shutdown")}>

                    Shutdown

                </button>

            </div>

            <div className="warnings-section">

                <div className="warnings-header">

                    <span className="warnings-title">Unallowed Application Logs</span>

                    {hasWarnings && (

                        <button className="btn btn-clear" onClick={handleClear}>

                            Clear

                        </button>

                    )}

                </div>

                {hasWarnings ? (

                    <div className="warnings-list">

                        {warningLogs.slice().reverse().map((log, index) => (

                            <div key={index} className="warning-item">

                                <div className="warning-title">{log.window}</div>

                                <div className="warning-time">

                                    {log.matched_rule || "Unallowed Application"} &middot; {formatTime(log.timestamp)}

                                </div>

                            </div>

                        ))}

                    </div>

                ) : (

                    <div className="no-warnings">

                        No unallowed application alerts

                    </div>

                )}

            </div>

        </div>

    );

}