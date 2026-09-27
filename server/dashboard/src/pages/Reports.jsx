import { useEffect, useState } from "react";
import api from "../services/api";
import "../styles/reports-palette.css";

function formatDate(timestamp) {
  if (!timestamp) return "N/A";
  return new Date(timestamp * 1000).toLocaleString();
}

function formatDuration(start, end) {
  if (!start || !end) return "N/A";

  const seconds = Math.max(0, Math.floor(end - start));

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m ${remainingSeconds}s`;
  }

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }

  return `${remainingSeconds}s`;
}

export default function Reports() {
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [report, setReport] = useState(null);

  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [error, setError] = useState("");

  // ========================================================
  // Load completed sessions
  // ========================================================
  async function fetchSessions() {
    try {
      setLoadingSessions(true);
      setError("");

      const response = await api.get("/sessions");

      const completedSessions = response.data.filter(
        (session) => session.status === "completed"
      );

      setSessions(completedSessions);

      // Automatically select newest completed session
      if (completedSessions.length > 0 && !selectedSessionId) {
        setSelectedSessionId(completedSessions[0].session_id);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to load lab sessions.");
    } finally {
      setLoadingSessions(false);
    }
  }

  // ========================================================
  // Load report
  // ========================================================
  async function fetchReport(sessionId) {
    if (!sessionId) {
      setReport(null);
      return;
    }

    try {
      setLoadingReport(true);
      setError("");

      const response = await api.get(`/reports/session/${sessionId}`);

      setReport(response.data);
    } catch (err) {
      console.error(err);
      setReport(null);
      setError(
        err.response?.data?.detail?.message || "Failed to load report."
      );
    } finally {
      setLoadingReport(false);
    }
  }

  // ========================================================
  // Initial load
  // ========================================================
  useEffect(() => {
    fetchSessions();
  }, []);

  // ========================================================
  // Load selected report
  // ========================================================
  useEffect(() => {
    if (selectedSessionId) {
      fetchReport(selectedSessionId);
    }
  }, [selectedSessionId]);

  // ========================================================
  // Download CSV
  // ========================================================
  async function downloadCSV() {
    if (!selectedSessionId) return;

    try {
      const response = await api.get(
        `/reports/session/${selectedSessionId}/csv`,
        { responseType: "blob" }
      );

      const blob = new Blob([response.data], { type: "text/csv" });

      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = `lab_report_${selectedSessionId}.csv`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      setError("Failed to download CSV report.");
    }
  }

  // ========================================================
  // Download PDF
  // ========================================================
  async function downloadPDF() {
    if (!selectedSessionId) return;

    try {
      const response = await api.get(
        `/reports/session/${selectedSessionId}/pdf`,
        { responseType: "blob" }
      );

      const blob = new Blob([response.data], { type: "application/pdf" });

      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = `lab_report_${selectedSessionId}.pdf`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      setError("Failed to download PDF report.");
    }
  }

  // ========================================================
  // No sessions
  // ========================================================
  if (!loadingSessions && sessions.length === 0) {
    return (
      <div className="reports-container">
        <div className="reports-header">
          <div>
            <h1 className="reports-title">Reports</h1>
            <p className="reports-subtitle">
              View and export completed lab sessions.
            </p>
          </div>
        </div>

        <div className="rep-empty">
          <h3>No completed sessions</h3>
          <p>
            Reports will appear here after a lab session has been completed.
          </p>
        </div>
      </div>
    );
  }

  // ========================================================
  // Main UI
  // ========================================================
  return (
    <div className="reports-container">
      {/* ============================================== 
          Header
      ============================================== */}
      <div className="reports-header">
        <div>
          <h1 className="reports-title">Session Audit Reports</h1>
          <p className="reports-subtitle">
            Review completed laboratory sessions, compliance logs, and export audit data.
          </p>
        </div>
      </div>

      {/* ============================================== 
          Error
      ============================================== */}
      {error && <div className="rep-alert">{error}</div>}

      {/* ============================================== 
          Session selector
      ============================================== */}
      <div className="rep-card">
        <div className="rep-form-group">
          <label htmlFor="rep-session-select">
            Select Completed Lab Session
          </label>

          <select
            id="rep-session-select"
            className="rep-select"
            value={selectedSessionId}
            onChange={(event) => setSelectedSessionId(event.target.value)}
          >
            <option value="">Select a session</option>

            {sessions.map((session) => (
              <option key={session.session_id} value={session.session_id}>
                {session.lab_name} — {formatDate(session.start_time)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ============================================== 
          Loading
      ============================================== */}
      {loadingReport && <div className="rep-empty">Loading report...</div>}

      {/* ============================================== 
          Report
      ============================================== */}
      {report && !loadingReport && (
        <>
          {/* =====================================
              Session information
          ===================================== */}
          <div className="rep-card">
            <h2 className="rep-card-title">{report.session.lab_name}</h2>

            <div className="rep-session-meta">
              <div className="rep-meta-item">
                <span className="rep-meta-label">Session ID</span>
                <span className="rep-meta-value">
                  {report.session.session_id}
                </span>
              </div>

              <div className="rep-meta-item">
                <span className="rep-meta-label">Started</span>
                <span className="rep-meta-value">
                  {formatDate(report.session.start_time)}
                </span>
              </div>

              <div className="rep-meta-item">
                <span className="rep-meta-label">Ended</span>
                <span className="rep-meta-value">
                  {formatDate(report.session.end_time)}
                </span>
              </div>

              <div className="rep-meta-item">
                <span className="rep-meta-label">Duration</span>
                <span className="rep-meta-value">
                  {formatDuration(
                    report.session.start_time,
                    report.session.end_time
                  )}
                </span>
              </div>

              <div className="rep-meta-item">
                <span className="rep-meta-label">Status</span>
                <span className="rep-meta-value">
                  <strong>{report.session.status}</strong>
                </span>
              </div>
            </div>
          </div>

          {/* =====================================
              Summary cards
          ===================================== */}
          <div className="rep-summary-grid">
            <div className="rep-stat">
              <div className="rep-stat-label">Total Violations</div>
              <div
                className="rep-stat-value"
                data-state={
                  report.summary.total_violations > 0 ? "warn" : undefined
                }
              >
                {report.summary.total_violations}
              </div>
            </div>

            <div className="rep-stat">
              <div className="rep-stat-label">Affected PCs</div>
              <div
                className="rep-stat-value"
                data-state={
                  report.summary.affected_pcs > 0 ? "warn" : undefined
                }
              >
                {report.summary.affected_pcs}
              </div>
            </div>

            <div className="rep-stat">
              <div className="rep-stat-label">Rules Triggered</div>
              <div className="rep-stat-value">
                {Object.keys(report.violations_by_rule).length}
              </div>
            </div>
          </div>

          {/* =====================================
              Export buttons
          ===================================== */}
          <div className="rep-actions">
            <button className="rep-btn rep-btn-outline" onClick={downloadPDF}>
              📄 Download PDF
            </button>

            <button className="rep-btn rep-btn-outline" onClick={downloadCSV}>
              📊 Download CSV
            </button>
          </div>

          {/* =====================================
              Violations per PC
          ===================================== */}
          <div className="rep-card">
            <h2 className="rep-card-title">Violations Per PC</h2>

            {Object.keys(report.violations_per_pc).length === 0 ? (
              <p className="rep-none">No violations recorded.</p>
            ) : (
              <div className="rep-table-wrap">
                <table className="rep-table">
                  <thead>
                    <tr>
                      <th>PC</th>
                      <th>Violations</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(report.violations_per_pc).map(
                      ([pc, count]) => (
                        <tr key={pc}>
                          <td>{pc}</td>
                          <td>{count}</td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* =====================================
              Violations by rule
          ===================================== */}
          <div className="rep-card">
            <h2 className="rep-card-title">Violations By Rule</h2>

            {Object.keys(report.violations_by_rule).length === 0 ? (
              <p className="rep-none">No violations recorded.</p>
            ) : (
              <div className="rep-table-wrap">
                <table className="rep-table">
                  <thead>
                    <tr>
                      <th>Matched Rule</th>
                      <th>Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(report.violations_by_rule).map(
                      ([rule, count]) => (
                        <tr key={rule}>
                          <td>{rule}</td>
                          <td>{count}</td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* =====================================
              Timeline
          ===================================== */}
          <div className="rep-card">
            <h2 className="rep-card-title">Violation Timeline</h2>

            {report.timeline.length === 0 ? (
              <p className="rep-none">
                No violations were recorded during this session.
              </p>
            ) : (
              <div className="rep-table-wrap">
                <table className="rep-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>PC</th>
                      <th>Window / Application</th>
                      <th>Matched Rule</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.timeline.map((event) => (
                      <tr key={event.id}>
                        <td>
                          {formatDate(event.recorded_at || event.timestamp)}
                        </td>
                        <td>{event.client_id}</td>
                        <td>{event.window}</td>
                        <td>{event.matched_rule}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}