import { useEffect, useState } from "react";

import api from "../services/api";

import "../styles/labsetup-palette.css";

export default function LabSetup() {
  const [labName, setLabName] = useState("");
  const [rows, setRows] = useState(0);
  const [columns, setColumns] = useState(0);
  const [pcs, setPcs] = useState([]);

  // Connected clients
  const [clients, setClients] = useState([]);

  // New PC registration fields
  const [pcName, setPcName] = useState("");
  const [clientId, setClientId] = useState("");
  const [pcRow, setPcRow] = useState(1);
  const [pcColumn, setPcColumn] = useState(1);

  async function loadConfig() {
    try {
      const response = await api.get("/lab-config");

      const data = response.data;

      setLabName(data.lab?.name || "");
      setRows(data.lab?.rows || 0);
      setColumns(data.lab?.columns || 0);
      setPcs(data.pcs || []);
    } catch (err) {
      console.error("Failed to load lab configuration:", err);
    }
  }

  async function loadClients() {
    try {
      const response = await api.get("/clients");

      const data = response.data;

      // /clients currently returns an object:
      // {
      //     "client_id": {
      //         "client_id": "...",
      //         "hostname": "...",
      //         "ip": "..."
      //     }
      // }

      setClients(Object.values(data));
    } catch (err) {
      console.error("Failed to load connected clients:", err);
    }
  }

  useEffect(() => {
    loadConfig();
    loadClients();
  }, []);

  async function registerPC() {
    if (!clientId) {
      alert("Please select a connected PC.");
      return;
    }

    if (!pcName.trim()) {
      alert("Please enter a PC name.");
      return;
    }

    try {
      const response = await api.post("/lab-config/pcs", {
        client_id: clientId,
        pc_name: pcName,
        row: pcRow,
        column: pcColumn,
      });

      if (response.data.status === "error") {
        alert(response.data.message);
        return;
      }

      alert("PC registered successfully!");

      // Clear form
      setPcName("");
      setClientId("");
      setPcRow(1);
      setPcColumn(1);

      // Refresh registered PCs
      await loadConfig();

      // Refresh connected clients
      await loadClients();
    } catch (err) {
      console.error("Failed to register PC:", err);

      alert("Failed to register PC.");
    }
  }

  async function saveLabConfiguration() {
    try {
      const response = await api.put("/lab-config", {
        name: labName,
        rows: rows,
        columns: columns,
      });

      if (response.data.status === "error") {
        alert(response.data.message);
        return;
      }

      alert("Lab configuration saved!");

      await loadConfig();
    } catch (err) {
      console.error("Failed to save lab configuration:", err);

      alert("Failed to save lab configuration.");
    }
  }

  async function deletePC(pc) {
    const confirmed = window.confirm(
      `Are you sure you want to remove ${pc.pc_name} from the lab?`,
    );

    if (!confirmed) {
      return;
    }

    try {
      const response = await api.delete(
        `/lab-config/pcs/${encodeURIComponent(pc.client_id)}`,
      );

      if (response.data.status === "error") {
        alert(response.data.message);
        return;
      }

      alert("PC removed from lab.");

      await loadConfig();
    } catch (err) {
      console.error("Failed to delete PC:", err);

      alert("Failed to remove PC.");
    }
  }

  return (
    <div className="dashboard-container labsetup-scope">
      <header className="dashboard-header">
        <div className="dashboard-title">
          <h1>Workspace Layout & Config</h1>
          <div className="dashboard-subtitle">
            Configure room seating dimensions, grid layout, and registered PCs
          </div>
        </div>
        <div className="status-indicator">
          <span className="status-dot" />
          {clients.length} PC connected
        </div>
      </header>

      <main className="setup-grid">
        {/* ========================================= */}
        {/* LAB CONFIGURATION */}
        {/* ========================================= */}

        <section className="metric-card lab-configuration">
          <div className="card-heading">
            <div>
              <span className="card-index">01</span>
              <h2>Lab Configuration</h2>
            </div>
            <p>Set the room name and seating grid.</p>
          </div>

          <div className="form-group lab-name-field">
            <label htmlFor="lab-name">Lab Name</label>
            <input
              id="lab-name"
              type="text"
              value={labName}
              onChange={(e) => setLabName(e.target.value)}
              placeholder="Computer Lab 1"
            />
          </div>

          <div className="form-row configuration-row">
            <div className="form-group compact-field">
              <label htmlFor="rows">Rows</label>
              <input
                id="rows"
                type="number"
                min="1"
                value={rows}
                onChange={(e) => setRows(Number(e.target.value))}
              />
            </div>
            <div className="form-group compact-field">
              <label htmlFor="columns">Columns</label>
              <input
                id="columns"
                type="number"
                min="1"
                value={columns}
                onChange={(e) => setColumns(Number(e.target.value))}
              />
            </div>
            <button className="btn btn-rules" onClick={saveLabConfiguration}>
              Save Lab Configuration
            </button>
          </div>
        </section>

        {/* ========================================= */}
        {/* REGISTER NEW PC */}
        {/* ========================================= */}

        <section className="metric-card register-card">
          <div className="card-heading">
            <div>
              <span className="card-index">02</span>
              <h2>Register New PC</h2>
            </div>
            <p>Assign a connected computer to a position.</p>
          </div>

          {/* Connected PC */}
          <div className="form-group">
            <label htmlFor="connected-pc">Connected PC</label>
            <select
              id="connected-pc"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
            >
              <option value="">Select a connected PC</option>
              {clients.map((client) => (
                <option key={client.client_id} value={client.client_id}>
                  {client.client_id} — {client.hostname} — {client.ip}
                </option>
              ))}
            </select>
          </div>

          {/* PC Name */}
          <div className="form-group">
            <label htmlFor="pc-name">PC Name</label>
            <input
              id="pc-name"
              type="text"
              value={pcName}
              onChange={(e) => setPcName(e.target.value)}
              placeholder="Lab PC 01"
            />
          </div>

          {/* Row + Column */}
          <div className="form-row location-row">
            <div className="form-group">
              <label htmlFor="pc-row">Row</label>
              <input
                id="pc-row"
                type="number"
                min="1"
                max={rows}
                value={pcRow}
                onChange={(e) => setPcRow(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label htmlFor="pc-column">Column</label>
              <input
                id="pc-column"
                type="number"
                min="1"
                max={columns}
                value={pcColumn}
                onChange={(e) => setPcColumn(Number(e.target.value))}
              />
            </div>
          </div>

          <button
            className="btn btn-rules register-button"
            onClick={registerPC}
            disabled={!clientId || !pcName.trim()}
          >
            Register PC
          </button>
        </section>

        {/* ========================================= */}
        {/* REGISTERED PCS */}
        {/* ========================================= */}

        <section className="metric-card registered-card">
          <div className="card-heading registered-heading">
            <div>
              <span className="card-index">03</span>
              <h2>Registered PCs</h2>
            </div>
            <span className="count-badge">{pcs.length} assigned</span>
          </div>

          {pcs.length === 0 ? (
            <div className="no-warnings">
              No PCs have been registered yet.
            </div>
          ) : (
            <div className="pc-list">
              <div className="pc-list-header">
                <span>Computer</span>
                <span>Position</span>
                <span>Action</span>
              </div>
              {pcs.map((pc) => (
                <div className="pc-row" key={pc.client_id}>
                  <div className="pc-identity">
                    <span className="pc-monogram">
                      {pc.pc_name.slice(-2)}
                    </span>
                    <div>
                      <strong>{pc.pc_name}</strong>
                      <span>Client ID: {pc.client_id}</span>
                    </div>
                  </div>
                  <div className="position">
                    Row {pc.row}, Column {pc.column}
                  </div>
                  <button
                    className="btn delete-button"
                    onClick={() => deletePC(pc)}
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
