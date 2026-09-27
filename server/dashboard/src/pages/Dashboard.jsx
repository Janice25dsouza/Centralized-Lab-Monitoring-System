import { useEffect, useState } from "react";
import api from "../services/api";
import ClientCard from "../components/ClientCard";
import "../styles/dashboard-palette.css";

export default function Dashboard() {
    // ============================================================
    // Dashboard State
    // ============================================================

    const [clients, setClients] = useState([]);
    const [warningLogs, setWarningLogs] = useState({});

    // ============================================================
    // Session State
    // ============================================================

    const [activeSession, setActiveSession] = useState(null);
    const [sessionLoading, setSessionLoading] = useState(false);

    // ============================================================
    // Remote Control State
    // ============================================================

    const [controlLoading, setControlLoading] = useState(false);
    const [controlAction, setControlAction] = useState("");

    // ============================================================
    // Rules Modal State
    // ============================================================

    const [showRulesModal, setShowRulesModal] = useState(false);

    const [allowedAppsInput, setAllowedAppsInput] = useState(
        "python, vs code, visual studio code, code, pycharm, sublime, terminal, iterm, cmd.exe, powershell, desktop, finder, explorer, system settings, system preferences, calculator"
    );

    const [allowedKeywordsInput, setAllowedKeywordsInput] = useState(
        "gmail, python, code, terminal, project, major-project, calculator, notes, clienttt.py"
    );

    const [savingRules, setSavingRules] = useState(false);


    // ============================================================
    // Fetch Active Session
    // ============================================================

    async function fetchActiveSession() {
        try {
            const response = await api.get("/sessions/active");

            setActiveSession(response.data || null);

        } catch (err) {
            console.error(
                "Failed to fetch active session:",
                err
            );

            setActiveSession(null);
        }
    }


    // ============================================================
    // Fetch Dashboard Data
    // ============================================================

    async function fetchData() {
        try {
            const [clientsRes, warningsRes] =
                await Promise.all([
                    api.get("/clients"),
                    api.get("/logs/warnings")
                ]);

            setClients(
                Object.values(clientsRes.data || {})
            );

            setWarningLogs(
                warningsRes.data || {}
            );

        } catch (err) {
            console.error(
                "Dashboard fetch error:",
                err
            );
        }

        // Fetch session separately so that a session
        // request failure does not break the dashboard.
        await fetchActiveSession();
    }


    // ============================================================
    // Start Session
    // ============================================================

    async function handleStartSession() {
        if (activeSession) {
            alert(
                "A lab session is already active."
            );

            return;
        }

        setSessionLoading(true);

        try {
            // Get current lab configuration
            const configResponse =
                await api.get("/lab-config");

            const labName =
                configResponse.data?.lab?.name ||
                "Computer Lab";

            // Start session
            const response =
                await api.post(
                    "/sessions/start",
                    {
                        lab_name: labName
                    }
                );

            setActiveSession(
                response.data
            );

            alert(
                `Session started successfully.\n\nLab: ${labName}`
            );

        } catch (err) {
            console.error(
                "Failed to start session:",
                err
            );

            const detail =
                err.response?.data?.detail;

            let message =
                "Failed to start lab session.";

            if (typeof detail === "string") {
                message = detail;
            } else if (
                detail &&
                typeof detail.message === "string"
            ) {
                message = detail.message;
            }

            alert(`${message}`);

            await fetchActiveSession();

        } finally {
            setSessionLoading(false);
        }
    }


    // ============================================================
    // Stop Session
    // ============================================================

    async function handleStopSession() {
        if (!activeSession) {
            alert(
                "There is no active lab session."
            );

            return;
        }

        const confirmed =
            window.confirm(
                `Stop the current lab session?\n\n` +
                `Lab: ${activeSession.lab_name}\n\n` +
                `All warnings recorded during this session will remain available in Reports.`
            );

        if (!confirmed) {
            return;
        }

        setSessionLoading(true);

        try {
            const response =
                await api.post(
                    "/sessions/end"
                );

            setActiveSession(null);

            alert(
                `Lab session stopped successfully.\n\n` +
                `Session ID: ${response.data.session_id}`
            );

        } catch (err) {
            console.error(
                "Failed to stop session:",
                err
            );

            const detail =
                err.response?.data?.detail;

            const message =
                typeof detail === "string"
                    ? detail
                    : "Failed to stop lab session.";

            alert(`${message}`);

            await fetchActiveSession();

        } finally {
            setSessionLoading(false);
        }
    }


    // ============================================================
    // Lock All Connected PCs
    // ============================================================

    async function handleLockAll() {
        if (controlLoading) {
            return;
        }

        if (onlineClients.length === 0) {
            alert(
                "There are no connected PCs to lock."
            );

            return;
        }

        const confirmed =
            window.confirm(
                `Lock all ${onlineClients.length} connected PC(s)?`
            );

        if (!confirmed) {
            return;
        }

        setControlLoading(true);
        setControlAction("lock");

        try {
            const response =
                await api.post(
                    "/lock-all"
                );

            const count =
                response.data?.broadcast_count || 0;

            alert(
                `Lock command sent to ${count} connected PC(s).`
            );

        } catch (err) {
            console.error(
                "Failed to lock all PCs:",
                err
            );

            const message =
                err.response?.data?.detail ||
                "Failed to lock connected PCs.";

            alert(
                `${message}`
            );

        } finally {
            setControlLoading(false);
            setControlAction("");
        }
    }


    // ============================================================
    // Unlock All Connected PCs
    // ============================================================

    async function handleUnlockAll() {
        if (controlLoading) {
            return;
        }

        if (onlineClients.length === 0) {
            alert(
                "There are no connected PCs to unlock."
            );

            return;
        }

        const confirmed =
            window.confirm(
                `Unlock all ${onlineClients.length} connected PC(s)?`
            );

        if (!confirmed) {
            return;
        }

        setControlLoading(true);
        setControlAction("unlock");

        try {
            const response =
                await api.post(
                    "/unlock-all"
                );

            const count =
                response.data?.broadcast_count || 0;

            alert(
                `Unlock command sent to ${count} connected PC(s).`
            );

        } catch (err) {
            console.error(
                "Failed to unlock all PCs:",
                err
            );

            const message =
                err.response?.data?.detail ||
                "Failed to unlock connected PCs.";

            alert(
                `${message}`
            );

        } finally {
            setControlLoading(false);
            setControlAction("");
        }
    }


    // ============================================================
    // Shutdown All Connected PCs
    // ============================================================

    async function handleShutdownAll() {
        if (controlLoading) {
            return;
        }

        if (onlineClients.length === 0) {
            alert(
                "There are no connected PCs to shut down."
            );

            return;
        }

        // First confirmation
        const confirmed =
            window.confirm(
                `WARNING\n\n` +
                `You are about to SHUT DOWN all ${onlineClients.length} connected PC(s).\n\n` +
                `Do you want to continue?`
            );

        if (!confirmed) {
            return;
        }

        // Second confirmation for destructive action
        const finalConfirmation =
            window.confirm(
                "FINAL CONFIRMATION\n\n" +
                "This will send a shutdown command to ALL currently connected PCs.\n\n" +
                "Are you absolutely sure?"
            );

        if (!finalConfirmation) {
            return;
        }

        setControlLoading(true);
        setControlAction("shutdown");

        try {
            const response =
                await api.post(
                    "/shutdown-all"
                );

            const count =
                response.data?.broadcast_count || 0;

            alert(
                `Shutdown command sent to ${count} connected PC(s).`
            );

        } catch (err) {
            console.error(
                "Failed to shut down all PCs:",
                err
            );

            const message =
                err.response?.data?.detail ||
                "Failed to shut down connected PCs.";

            alert(
                `${message}`
            );

        } finally {
            setControlLoading(false);
            setControlAction("");
        }
    }


    // ============================================================
    // Clear All Warnings
    // ============================================================

    async function handleClearAll() {
        try {
            await api.delete(
                "/logs/warnings"
            );

            setWarningLogs({});

        } catch (err) {
            console.error(
                "Failed to clear all warnings:",
                err
            );
        }
    }


    // ============================================================
    // Clear Warnings For One Client
    // ============================================================

    async function handleClearClientWarnings(
        clientId
    ) {
        try {
            await api.delete(
                `/logs/warnings/${clientId}`
            );

            setWarningLogs(prev => ({
                ...prev,
                [clientId]: []
            }));

        } catch (err) {
            console.error(
                `Failed to clear warnings for ${clientId}:`,
                err
            );
        }
    }


    // ============================================================
    // Save And Broadcast Rules
    // ============================================================

    async function handleSaveAndBroadcastRules(
        e
    ) {
        e.preventDefault();

        setSavingRules(true);

        const allowed_apps =
            allowedAppsInput
                .split(",")
                .map(
                    s =>
                        s.trim().toLowerCase()
                )
                .filter(Boolean);

        const allowed_keywords =
            allowedKeywordsInput
                .split(",")
                .map(
                    s =>
                        s.trim().toLowerCase()
                )
                .filter(Boolean);

        try {
            const res =
                await api.post(
                    "/update-rules",
                    {
                        rules: {
                            allowed_apps,
                            allowed_keywords
                        }
                    }
                );

            alert(
                `Rules successfully broadcasted live to ${res.data.broadcast_count || 0
                } connected PC(s)!`
            );

            setShowRulesModal(false);

        } catch (err) {
            console.error(
                "Failed to broadcast rules:",
                err
            );

            alert(
                "Failed to send rule update to clients."
            );

        } finally {
            setSavingRules(false);
        }
    }


    // ============================================================
    // Initial Load + Automatic Polling
    // ============================================================

    useEffect(() => {
        fetchData();

        const interval =
            setInterval(
                fetchData,
                2000
            );

        return () =>
            clearInterval(interval);

    }, []);


    // ============================================================
    // Online Clients
    // ============================================================

    /*
     * The server keeps registered clients in
     * its clients dictionary.
     *
     * Therefore:
     *
     * clients =
     * all registered clients
     *
     * client.online =
     * whether the client is currently online
     *
     * The Dashboard displays only online clients.
     */

    const onlineClients =
        clients.filter(
            client =>
                client.online === true
        );


    // ============================================================
    // Dashboard Metrics
    // ============================================================

    const totalClients =
        onlineClients.length;

    const activeAlertsCount =
        Object.keys(
            warningLogs
        ).filter(
            id =>
                warningLogs[id] &&
                warningLogs[id].length > 0
        ).length;

    const totalWarnings =
        Object.values(
            warningLogs
        ).reduce(
            (acc, logs) =>
                acc +
                (logs
                    ? logs.length
                    : 0),
            0
        );


    // ============================================================
    // Render
    // ============================================================

    return (
        <div className="dashboard-container">

            {/* ==================================================
                Dashboard Header
            =================================================== */}

            <header className="dashboard-header">

                <div className="dashboard-title">

                    <h1>
                        Dashboard
                    </h1>

                    <div className="dashboard-subtitle">
                        Real-time whitelist monitoring and remote machine administration
                    </div>

                </div>


                <div className="header-buttons">

                    <button
                        className="btn btn-outline"
                        onClick={() =>
                            setShowRulesModal(true)
                        }
                    >
                        Manage Allowed Rules
                    </button>


                    {totalWarnings > 0 && (
                        <button
                            className="btn btn-danger"
                            onClick={
                                handleClearAll
                            }
                        >
                            Clear All Alerts
                        </button>
                    )}

                </div>

            </header>


            {/* ==================================================
                Session & Remote Control
            =================================================== */}

            <section className="session-panel">

                {/* Panel Header */}

                <div className="session-panel-header">

                    <div>

                        <h2 className="session-panel-title">
                            Session & Remote Control
                        </h2>

                        <div className="session-panel-sub">
                            Manage the current lab session and connected student PCs.
                        </div>

                    </div>


                    {/* Session Status */}

                    <div
                        className="session-status"
                        data-active={
                            activeSession ? "true" : "false"
                        }
                    >
                        <span
                            className={
                                activeSession
                                    ? "status-dot status-dot--online"
                                    : "status-dot"
                            }
                        />
                        {activeSession
                            ? `Session active — ${activeSession.lab_name}`
                            : "No active session"}
                    </div>

                </div>


                {/* ==================================================
                    Session Controls
                =================================================== */}

                <div className="session-controls">

                    <button
                        className="btn btn-outline"
                        onClick={
                            handleStartSession
                        }
                        disabled={
                            !!activeSession ||
                            sessionLoading
                        }
                    >
                        {sessionLoading &&
                            !controlAction
                            ? "Please wait..."
                            : "Start Session"}
                    </button>


                    <button
                        className="btn btn-danger"
                        onClick={
                            handleStopSession
                        }
                        disabled={
                            !activeSession ||
                            sessionLoading
                        }
                    >
                        {sessionLoading &&
                            !controlAction
                            ? "Please wait..."
                            : "Stop Session"}
                    </button>

                </div>


                {/* ==================================================
                    Remote PC Controls
                =================================================== */}

                <div className="remote-control-block">

                    <div className="remote-control-label">
                        Remote control
                        <span className="remote-control-count">
                            ({totalClients} connected)
                        </span>
                    </div>


                    <div className="remote-control-buttons">

                        {/* Lock All */}

                        <button
                            className="btn btn-outline"
                            onClick={
                                handleLockAll
                            }
                            disabled={
                                totalClients === 0 ||
                                controlLoading
                            }
                        >
                            {controlLoading &&
                                controlAction ===
                                "lock"
                                ? "Locking..."
                                : "Lock All PCs"}
                        </button>


                        {/* Unlock All */}

                        <button
                            className="btn btn-outline"
                            onClick={
                                handleUnlockAll
                            }
                            disabled={
                                totalClients === 0 ||
                                controlLoading
                            }
                        >
                            {controlLoading &&
                                controlAction ===
                                "unlock"
                                ? "Unlocking..."
                                : "Unlock All PCs"}
                        </button>


                        {/* Shutdown All */}

                        <button
                            className="btn btn-danger-solid"
                            onClick={
                                handleShutdownAll
                            }
                            disabled={
                                totalClients === 0 ||
                                controlLoading
                            }
                        >
                            {controlLoading &&
                                controlAction ===
                                "shutdown"
                                ? "Shutting down..."
                                : "Shutdown All PCs"}
                        </button>

                    </div>

                </div>

            </section>


            {/* ==================================================
                Metrics Bar
            =================================================== */}

            <div className="metrics-bar">

                {/* Connected PCs */}

                <div className="metric-card">

                    <div className="metric-label">
                        Connected PCs
                    </div>

                    <div className="metric-value">
                        {totalClients}
                    </div>

                </div>


                {/* Active Alert Machines */}

                <div className="metric-card">

                    <div className="metric-label">
                        Active Alert Machines
                    </div>

                    <div
                        className="metric-value"
                        data-state={
                            activeAlertsCount > 0
                                ? "warn"
                                : undefined
                        }
                    >
                        {activeAlertsCount}
                    </div>

                </div>


                {/* Total Warnings */}

                <div className="metric-card">

                    <div className="metric-label">
                        Total Unallowed Alerts
                    </div>

                    <div
                        className="metric-value"
                        data-state={
                            totalWarnings > 0
                                ? "warn"
                                : undefined
                        }
                    >
                        {totalWarnings}
                    </div>

                </div>

            </div>


            {/* ==================================================
                Client Cards
            =================================================== */}

            {totalClients === 0 ? (

                <div className="no-warnings">
                    No client PCs connected.

                </div>

            ) : (

                <div className="client-grid">

                    {onlineClients.map(
                        client => (

                            <ClientCard
                                key={
                                    client.client_id
                                }
                                client={
                                    client
                                }
                                warningLogs={
                                    warningLogs[
                                    client
                                        .client_id
                                    ] || []
                                }
                                onClearWarnings={
                                    handleClearClientWarnings
                                }
                            />

                        )
                    )}

                </div>

            )}


            {/* ==================================================
                Rules Modal
            =================================================== */}

            {showRulesModal && (

                <div
                    className="modal-backdrop"
                    onClick={() =>
                        setShowRulesModal(
                            false
                        )
                    }
                >

                    <div
                        className="modal-content"
                        onClick={e =>
                            e.stopPropagation()
                        }
                    >

                        {/* Modal Header */}

                        <div className="modal-header">

                            <h2>
                                Whitelist Rules Manager
                            </h2>

                            <button
                                className="btn btn-danger"
                                onClick={() =>
                                    setShowRulesModal(
                                        false
                                    )
                                }
                            >
                                Close
                            </button>

                        </div>


                        {/* Rules Form */}

                        <form
                            onSubmit={
                                handleSaveAndBroadcastRules
                            }
                        >

                            {/* Allowed Applications */}

                            <div className="form-group">

                                <label>
                                    Allowed applications
                                    (comma-separated)
                                </label>

                                <textarea
                                    value={
                                        allowedAppsInput
                                    }
                                    onChange={e =>
                                        setAllowedAppsInput(
                                            e.target.value
                                        )
                                    }
                                    placeholder="python, vs code, terminal, calculator..."
                                />

                                <div className="form-hint">
                                    Student PCs can use these
                                    applications without
                                    triggering alerts.
                                </div>

                            </div>


                            {/* Allowed Keywords */}

                            <div className="form-group">

                                <label>
                                    Allowed keywords / web sites
                                    (comma-separated)
                                </label>

                                <textarea
                                    value={
                                        allowedKeywordsInput
                                    }
                                    onChange={e =>
                                        setAllowedKeywordsInput(
                                            e.target.value
                                        )
                                    }
                                    placeholder="gmail, python, project, stack overflow..."
                                />

                                <div className="form-hint">
                                    Matches window titles/tabs
                                    (e.g. "gmail" allows Gmail
                                    in Chrome).
                                </div>

                            </div>


                            {/* Form Buttons */}

                            <div
                                style={{
                                    display: "flex",
                                    gap: "10px",
                                    marginTop: "4px"
                                }}
                            >

                                <button
                                    type="submit"
                                    className="btn btn-outline"
                                    disabled={
                                        savingRules
                                    }
                                >
                                    {savingRules
                                        ? "Broadcasting..."
                                        : "Save & Broadcast to All PCs"}
                                </button>


                                <button
                                    type="button"
                                    className="btn btn-danger"
                                    onClick={() =>
                                        setShowRulesModal(
                                            false
                                        )
                                    }
                                >
                                    Cancel
                                </button>

                            </div>

                        </form>

                    </div>

                </div>

            )}

        </div>
    );
}