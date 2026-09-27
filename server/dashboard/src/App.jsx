import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import LabSetup from "./pages/LabSetup";
import LabMap from "./pages/LabMap";
import Reports from "./pages/Reports";

import "./styles/navbar.css";

function App() {
    return (
        <BrowserRouter>
            <nav className="app-navigation">
                <div className="nav-brand">
                    <span className="nav-brand-text">LabWatch</span>
                </div>

                <div className="nav-links">
                    <NavLink to="/" end>
                        Dashboard
                    </NavLink>

                    <NavLink to="/lab-setup">
                        Lab Setup
                    </NavLink>

                    <NavLink to="/lab-map">
                        Lab Map
                    </NavLink>

                    <NavLink to="/reports">
                        Reports
                    </NavLink>
                </div>
            </nav>

            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/lab-setup" element={<LabSetup />} />
                <Route path="/lab-map" element={<LabMap />} />
                <Route path="/reports" element={<Reports />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;